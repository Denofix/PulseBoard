import httpx

from app.api import create_app


async def test_crud_evidence_and_bounded_history(api):
    client, db = api
    assert (await client.get("/api/health")).status_code == 200
    response = await client.post("/api/services", json={"name": "API", "url": "http://demo-service/ok"})
    assert response.status_code == 201 and response.json()["status"] == "UNKNOWN"
    service_id = response.json()["id"]
    assert (
        await client.post("/api/services", json={"name": "Other", "url": "http://demo-service/ok"})
    ).status_code == 409
    assert (await client.get(f"/api/services/{service_id}/checks?limit=201")).status_code == 422
    assert (await client.get(f"/api/services/{service_id}/checks")).json()["items"] == []
    assert (await client.get("/api/checks/999")).status_code == 404
    assert (await client.get("/api/services/999/checks")).status_code == 404
    dashboard = (await client.get("/api/dashboard")).json()
    assert dashboard["total_services"] == 1 and dashboard["unknown_services"] == 1
    assert dashboard["availability_percent"] is None
    assert (await client.delete(f"/api/services/{service_id}")).status_code == 204
    assert (await client.delete(f"/api/services/{service_id}")).status_code == 404


async def test_read_only_is_enforced_on_backend(settings):
    settings.read_only, settings.seed_demo = True, True
    app = create_app(settings, enable_monitor=False)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            services = (await client.get("/api/services")).json()
            assert len(services) == 3
            assert (await client.get("/api/config")).json()["read_only"]
            assert (
                await client.post("/api/services", json={"name": "Forbidden", "url": "http://localhost"})
            ).status_code == 403
            assert (await client.delete(f"/api/services/{services[0]['id']}")).status_code == 403
    # Startup seeding is idempotent, including in read-only mode.
    async with app.router.lifespan_context(app):
        assert len(await app.state.database.services()) == 3


async def test_cors_exact_origin(settings):
    settings.cors_origins = ["https://pulse.example.com"]
    app = create_app(settings, enable_monitor=False)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            allowed = await client.get("/api/config", headers={"Origin": "https://pulse.example.com"})
            denied = await client.get("/api/config", headers={"Origin": "https://other.example.com"})
            assert allowed.headers["access-control-allow-origin"] == "https://pulse.example.com"
            assert "access-control-allow-origin" not in denied.headers
