"""Incident transitions; called inside the same transaction as the observation insert."""

import aiosqlite

from .checker import Observation


async def apply_observation(
    connection: aiosqlite.Connection,
    service_id: int,
    check_id: int,
    observation: Observation,
    gap_seconds: float,
) -> None:
    async with connection.execute(
        "SELECT id FROM incidents WHERE service_id = ? AND closed_at IS NULL", (service_id,)
    ) as cursor:
        opened = await cursor.fetchone()
    if opened:
        await connection.execute(
            """UPDATE incidents SET last_observed_at = ?,
               observation_gap_seconds = observation_gap_seconds + ?,
               closed_at = ?, closing_check_id = ? WHERE id = ?""",
            (
                observation.checked_at,
                gap_seconds,
                observation.checked_at if observation.status == "UP" else None,
                check_id if observation.status == "UP" else None,
                opened["id"],
            ),
        )
    elif observation.status == "DOWN":
        await connection.execute(
            """INSERT INTO incidents
               (service_id, opened_at, opening_check_id, reason, last_observed_at)
               VALUES (?, ?, ?, ?, ?)""",
            (
                service_id,
                observation.checked_at,
                check_id,
                observation.error_message or "The service is unavailable",
                observation.checked_at,
            ),
        )
