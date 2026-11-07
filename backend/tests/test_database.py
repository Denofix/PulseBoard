from datetime import timedelta

import pytest

import app.database as database_module
from app.checker import Observation
from app.database import Database
from app.models import timestamp, utc_now


def observation(status, when=None):
    return Observation(
        timestamp(when),
        status,
        200 if status == "UP" else 500,
        2.5,
        None if status == "UP" else "HTTP_STATUS",
        None if status == "UP" else "HTTP 500",
    )


async def test_unknown_then_incident_lifecycle(db):
    service_id = await db.create_service("API", "http://demo-service/ok")
    initial = (await db.services(service_id))[0]
    assert initial["status"] == "UNKNOWN"
    assert initial["latest_check"] is None and initial["availability_percent"] is None
    start = utc_now()
    await db.record_check(service_id, observation("UP", start))
    first_bad = await db.record_check(service_id, observation("DOWN", start + timedelta(seconds=15)))
    await db.record_check(service_id, observation("DOWN", start + timedelta(seconds=30)))
    opened = (await db.incidents(10))["items"]
    assert len(opened) == 1 and opened[0]["closed_at"] is None
    assert opened[0]["opening_check_id"] == first_bad
    assert opened[0]["observed_duration_seconds"] == 15
    recovered = await db.record_check(service_id, observation("UP", start + timedelta(seconds=45)))
    closed = (await db.incidents(10))["items"][0]
    assert closed["closing_check_id"] == recovered
    assert closed["closed_at"] is not None and closed["observed_duration_seconds"] == 30
    await db.record_check(service_id, observation("DOWN", start + timedelta(seconds=60)))
    incidents = (await db.incidents(10))["items"]
    assert len(incidents) == 2 and incidents[0]["closed_at"] is None
    service = (await db.services(service_id))[0]
    assert service["check_count"] == 5 and service["availability_percent"] == 40


async def test_first_failure_opens_and_restart_preserves_open_incident(settings):
    database = Database(settings)
    await database.open()
    service_id = await database.create_service("API", "http://demo-service")
    await database.record_check(service_id, observation("DOWN"))
    await database.close()
    database = Database(settings)
    await database.open()
    try:
        assert (await database.services(service_id))[0]["status"] == "DOWN"
        assert len((await database.checks(service_id, 10))["items"]) == 1
        assert len((await database.incidents(10))["items"]) == 1
        await database.record_check(service_id, observation("DOWN"))
        assert len((await database.incidents(10))["items"]) == 1
        await database.record_check(service_id, observation("UP"))
        assert (await database.incidents(10))["items"][0]["closed_at"] is not None
    finally:
        await database.close()


async def test_observation_gap_is_not_downtime(db):
    service_id = await db.create_service("API", "http://demo-service")
    start = utc_now() - timedelta(minutes=10)
    await db.record_check(service_id, observation("DOWN", start))
    await db.record_check(service_id, observation("UP", start + timedelta(seconds=300)))
    incident = (await db.incidents(10))["items"][0]
    assert incident["elapsed_seconds"] == 300
    assert incident["observation_gap_seconds"] == 285
    assert incident["observed_duration_seconds"] == 15
    checks = (await db.checks(service_id, 10))["items"]
    assert checks[0]["gap_before_seconds"] == 285
    assert (await db.services(service_id))[0]["stale"]


async def test_atomic_rollback_if_incident_write_fails(db, monkeypatch):
    service_id = await db.create_service("API", "http://demo-service")

    async def fail(*args):
        raise RuntimeError("simulated storage failure")

    monkeypatch.setattr(database_module, "apply_observation", fail)
    with pytest.raises(RuntimeError):
        await db.record_check(service_id, observation("DOWN"))
    assert (await db.checks(service_id, 10))["items"] == []
    assert (await db.services(service_id))[0]["check_count"] == 0
    assert (await db.incidents(10))["items"] == []


async def test_pagination_and_cascade_delete(db):
    service_id = await db.create_service("API", "http://demo-service")
    for state in ["DOWN", "UP", "DOWN", "UP"]:
        await db.record_check(service_id, observation(state))
    first = await db.checks(service_id, 2)
    second = await db.checks(service_id, 2, first["next_cursor"])
    assert len(first["items"]) == len(second["items"]) == 2
    assert second["next_cursor"] is None
    assert not ({row["id"] for row in first["items"]} & {row["id"] for row in second["items"]})
    incident_page = await db.incidents(1)
    assert len((await db.incidents(1, incident_page["next_cursor"]))["items"]) == 1
    assert await db.delete_service(service_id)
    assert (await db.incidents(10))["items"] == []
    assert (await db.checks(service_id, 10))["items"] == []
    assert await db.record_check(service_id, observation("DOWN")) is None


async def test_short_restart_is_still_an_observation_gap(settings):
    start = utc_now()
    first = Database(settings)
    await first.open()
    service_id = await first.create_service("API", "http://demo-service")
    await first.record_check(service_id, observation("DOWN", start))
    await first.close()
    second = Database(settings)
    await second.open()
    try:
        await second.record_check(service_id, observation("UP", start + timedelta(seconds=2)))
        check = (await second.checks(service_id, 1))["items"][0]
        assert check["gap_before_seconds"] == 2
        incident = (await second.incidents(1))["items"][0]
        assert incident["observation_gap_seconds"] == 2
        assert incident["observed_duration_seconds"] == 0
    finally:
        await second.close()
