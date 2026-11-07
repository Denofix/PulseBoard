import asyncio
from pathlib import Path
from uuid import uuid4

import aiosqlite

from .checker import Observation
from .incidents import apply_observation
from .models import parse_time, timestamp, utc_now
from .settings import Settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    check_count INTEGER NOT NULL DEFAULT 0,
    success_count INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_id INTEGER NOT NULL REFERENCES services(id) ON DELETE CASCADE,
    run_id TEXT NOT NULL,
    checked_at TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('UP', 'DOWN')),
    http_status INTEGER,
    response_time_ms REAL,
    error_type TEXT,
    error_message TEXT,
    gap_before_seconds REAL NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS checks_service_id ON checks(service_id, id DESC);
CREATE TABLE IF NOT EXISTS incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_id INTEGER NOT NULL REFERENCES services(id) ON DELETE CASCADE,
    opened_at TEXT NOT NULL,
    closed_at TEXT,
    opening_check_id INTEGER NOT NULL REFERENCES checks(id),
    closing_check_id INTEGER REFERENCES checks(id),
    reason TEXT NOT NULL,
    last_observed_at TEXT NOT NULL,
    observation_gap_seconds REAL NOT NULL DEFAULT 0
);
CREATE UNIQUE INDEX IF NOT EXISTS one_open_incident ON incidents(service_id) WHERE closed_at IS NULL;
CREATE INDEX IF NOT EXISTS incidents_service_id ON incidents(service_id, id DESC);
PRAGMA user_version = 1;
"""


class ServiceLimitError(Exception):
    pass


class Database:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.lock = asyncio.Lock()
        self.connection: aiosqlite.Connection
        self.run_id = uuid4().hex

    async def open(self) -> None:
        Path(self.settings.database_path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = await aiosqlite.connect(str(self.settings.database_path))
        self.connection.row_factory = aiosqlite.Row
        await self.connection.execute("PRAGMA foreign_keys = ON")
        await self.connection.execute("PRAGMA journal_mode = WAL")
        await self.connection.execute("PRAGMA busy_timeout = 5000")
        await self.connection.executescript(SCHEMA)
        await self.connection.commit()

    async def close(self) -> None:
        await self.connection.close()

    async def create_service(self, name: str, url: str) -> int:
        async with self.lock:
            try:
                count = await (await self.connection.execute("SELECT COUNT(*) FROM services")).fetchone()
                if count[0] >= self.settings.max_services:
                    raise ServiceLimitError
                cursor = await self.connection.execute(
                    "INSERT INTO services(name, url, created_at) VALUES (?, ?, ?)", (name, url, timestamp())
                )
                await self.connection.commit()
                return int(cursor.lastrowid)
            except BaseException:
                await self.connection.rollback()
                raise

    async def seed(self) -> None:
        base = str(self.settings.demo_base_url).rstrip("/")
        existing = {service["url"] for service in await self.services()}
        for name, endpoint in [("Demo API", "/ok"), ("Demo failure", "/error"), ("Demo timeout", "/slow")]:
            if base + endpoint not in existing:
                await self.create_service(name, base + endpoint)

    async def delete_service(self, service_id: int) -> bool:
        async with self.lock:
            try:
                # Delete incidents first: they reference the evidence checks being cascade-deleted.
                await self.connection.execute("DELETE FROM incidents WHERE service_id = ?", (service_id,))
                cursor = await self.connection.execute("DELETE FROM services WHERE id = ?", (service_id,))
                await self.connection.commit()
                return cursor.rowcount > 0
            except BaseException:
                await self.connection.rollback()
                raise

    async def services(self, service_id: int | None = None) -> list[dict]:
        async with self.lock:
            where, params = ("WHERE id = ?", (service_id,)) if service_id is not None else ("", ())
            rows = await (
                await self.connection.execute(f"SELECT * FROM services {where} ORDER BY id DESC", params)
            ).fetchall()
            # Indexed LIMIT queries avoid scanning the full, unbounded history on every refresh.
            grouped: dict[int, list[dict]] = {}
            for row in rows:
                checks = await (
                    await self.connection.execute(
                        "SELECT * FROM checks WHERE service_id = ? ORDER BY id DESC LIMIT 30", (row["id"],)
                    )
                ).fetchall()
                grouped[row["id"]] = [dict(check) for check in reversed(checks)]
        result = []
        for row in rows:
            service = dict(row)
            recent = grouped.get(service["id"], [])
            latest = recent[-1] if recent else None
            service.update(
                status=latest["status"] if latest else "UNKNOWN",
                latest_check=latest,
                recent_checks=recent,
                availability_percent=round(service["success_count"] * 100 / service["check_count"], 2)
                if service["check_count"]
                else None,
                stale=latest is not None
                and (utc_now() - parse_time(latest["checked_at"])).total_seconds()
                > self.settings.gap_threshold_seconds,
            )
            result.append(service)
        return result

    async def targets(self) -> list[dict]:
        async with self.lock:
            rows = await (
                await self.connection.execute(
                    """SELECT s.id, s.url, (SELECT checked_at FROM checks WHERE service_id = s.id
                   ORDER BY id DESC LIMIT 1) AS last_checked_at FROM services s ORDER BY s.id"""
                )
            ).fetchall()
        return [dict(row) for row in rows]

    async def exists(self, service_id: int) -> bool:
        async with self.lock:
            row = await (
                await self.connection.execute("SELECT 1 FROM services WHERE id = ?", (service_id,))
            ).fetchone()
        return row is not None

    async def record_check(self, service_id: int, observation: Observation) -> int | None:
        async with self.lock:
            try:
                await self.connection.execute("BEGIN IMMEDIATE")
                service = await (
                    await self.connection.execute("SELECT id FROM services WHERE id = ?", (service_id,))
                ).fetchone()
                if service is None:
                    await self.connection.rollback()
                    return None
                previous = await (
                    await self.connection.execute(
                        "SELECT checked_at, run_id FROM checks WHERE service_id = ? ORDER BY id DESC LIMIT 1",
                        (service_id,),
                    )
                ).fetchone()
                gap = 0.0
                if previous:
                    delta = (parse_time(observation.checked_at) - parse_time(previous[0])).total_seconds()
                    if previous["run_id"] != self.run_id:
                        # Across process sessions, conservatively mark the whole intervening span unknown.
                        gap = max(0, delta)
                    elif delta > self.settings.gap_threshold_seconds:
                        gap = max(0, delta - self.settings.interval_seconds)
                cursor = await self.connection.execute(
                    """INSERT INTO checks(service_id, run_id, checked_at, status, http_status, response_time_ms,
                       error_type, error_message, gap_before_seconds) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        service_id,
                        self.run_id,
                        observation.checked_at,
                        observation.status,
                        observation.http_status,
                        observation.response_time_ms,
                        observation.error_type,
                        observation.error_message,
                        gap,
                    ),
                )
                check_id = int(cursor.lastrowid)
                await self.connection.execute(
                    """UPDATE services SET check_count = check_count + 1,
                       success_count = success_count + ? WHERE id = ?""",
                    (int(observation.status == "UP"), service_id),
                )
                await apply_observation(self.connection, service_id, check_id, observation, gap)
                await self.connection.commit()
                return check_id
            except BaseException:
                await self.connection.rollback()
                raise

    async def check(self, check_id: int) -> dict | None:
        async with self.lock:
            row = await (
                await self.connection.execute("SELECT * FROM checks WHERE id = ?", (check_id,))
            ).fetchone()
        return dict(row) if row else None

    async def checks(self, service_id: int, limit: int, before: int | None = None) -> dict:
        async with self.lock:
            rows = await (
                await self.connection.execute(
                    "SELECT * FROM checks WHERE service_id = ? AND id < ? ORDER BY id DESC LIMIT ?",
                    (service_id, before if before is not None else 9223372036854775807, limit + 1),
                )
            ).fetchall()
        return {
            "items": [dict(row) for row in rows[:limit]],
            "next_cursor": rows[limit - 1]["id"] if len(rows) > limit else None,
        }

    async def incidents(self, limit: int, before: int | None = None, service_id: int | None = None) -> dict:
        clauses = ["i.id < ?"]
        params: list = [before if before is not None else 9223372036854775807]
        if service_id is not None:
            clauses.append("i.service_id = ?")
            params.append(service_id)
        async with self.lock:
            rows = await (
                await self.connection.execute(
                    f"""SELECT i.*, s.name AS service_name FROM incidents i
                    JOIN services s ON s.id = i.service_id
                    WHERE {" AND ".join(clauses)} ORDER BY i.id DESC LIMIT ?""",
                    (*params, limit + 1),
                )
            ).fetchall()
        items = []
        for row in rows[:limit]:
            item = dict(row)
            elapsed = (parse_time(item["last_observed_at"]) - parse_time(item["opened_at"])).total_seconds()
            item.update(
                elapsed_seconds=max(0, elapsed),
                observed_duration_seconds=max(0, elapsed - item["observation_gap_seconds"]),
            )
            items.append(item)
        return {"items": items, "next_cursor": rows[limit - 1]["id"] if len(rows) > limit else None}

    async def dashboard(self) -> dict:
        # The lock in services() yields one coherent service/check snapshot.
        services = await self.services()
        async with self.lock:
            count = await (
                await self.connection.execute("SELECT COUNT(*) FROM incidents WHERE closed_at IS NULL")
            ).fetchone()
        total = sum(service["check_count"] for service in services)
        successes = sum(service["success_count"] for service in services)
        return {
            "total_services": len(services),
            "up_services": sum(service["status"] == "UP" for service in services),
            "down_services": sum(service["status"] == "DOWN" for service in services),
            "unknown_services": sum(service["status"] == "UNKNOWN" for service in services),
            "stale_services": sum(service["stale"] for service in services),
            "open_incidents": count[0],
            "check_count": total,
            "availability_percent": round(successes * 100 / total, 2) if total else None,
            "generated_at": timestamp(),
        }
