import asyncio

import httpx

from app.monitor import Monitor


async def test_parallelism_no_overlap_isolation_and_shutdown(db, settings):
    settings.concurrency = 2
    ids = [await db.create_service(str(i), f"http://demo-service/{i}") for i in range(6)]
    active, max_active = set(), 0
    done = asyncio.Event()
    calls = []

    async def handler(request):
        nonlocal max_active
        key = request.url.path
        assert key not in active, "Concurrent requests to the same service"
        active.add(key)
        max_active = max(max_active, len(active))
        try:
            await asyncio.sleep(0.01)
            calls.append(key)
            if len(calls) >= len(ids):
                done.set()
            if key == "/0":
                raise httpx.ConnectError("simulated failure")
            return httpx.Response(200)
        finally:
            active.remove(key)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        monitor = Monitor(db, client, settings)
        monitor.start()
        try:
            await asyncio.wait_for(done.wait(), 2)
            await asyncio.sleep(0.03)
            assert monitor.running
        finally:
            await monitor.stop()
        assert not monitor.running and not monitor.inflight
    assert max_active == 2
    assert len(calls) == len(ids)
    services = await db.services()
    assert all(service["check_count"] == 1 for service in services)
    assert sum(service["status"] == "UP" for service in services) == 5
    assert len((await db.incidents(10))["items"]) == 1


async def test_slow_check_cannot_be_scheduled_twice(db, settings):
    settings.interval_seconds = 1
    await db.create_service("Slow", "http://demo-service/slow")
    started, release = asyncio.Event(), asyncio.Event()
    calls = 0

    async def handler(request):
        nonlocal calls
        calls += 1
        started.set()
        await release.wait()
        return httpx.Response(200)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        monitor = Monitor(db, client, settings)
        monitor.start()
        try:
            await asyncio.wait_for(started.wait(), 1)
            # Cross another scheduler tick while the first observation has not completed.
            await asyncio.sleep(0.6)
            assert calls == 1
        finally:
            release.set()
            await monitor.stop()
