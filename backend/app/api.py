import sqlite3
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from .database import Database, ServiceLimitError
from .models import Check, CheckPage, Dashboard, IncidentPage, PublicConfig, Service, ServiceCreate
from .monitor import Monitor
from .settings import Settings


def create_app(settings: Settings | None = None, *, enable_monitor: bool = True) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        database = Database(settings)
        await database.open()
        try:
            if settings.seed_demo:
                await database.seed()
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(settings.network_timeout_seconds),
                limits=httpx.Limits(
                    max_connections=settings.concurrency, max_keepalive_connections=settings.concurrency
                ),
                follow_redirects=False,
                trust_env=False,
                headers={"User-Agent": "PulseBoard/0.1"},
            ) as client:
                monitor = Monitor(database, client, settings)
                app.state.database, app.state.monitor = database, monitor
                if enable_monitor:
                    monitor.start()
                try:
                    yield
                finally:
                    await monitor.stop()
        finally:
            await database.close()

    app = FastAPI(
        title="PulseBoard",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type"],
    )

    def database(request: Request) -> Database:
        return request.app.state.database

    def writable() -> None:
        if settings.read_only:
            raise HTTPException(403, "This public demo is read-only")

    async def require_service(service_id: int, db: Database) -> dict:
        services = await db.services(service_id)
        if not services:
            raise HTTPException(404, "Service not found")
        return services[0]

    @app.get("/api/health")
    async def health(request: Request, db: Database = Depends(database)):
        # Exercise the DB as well as the event loop; healthchecks must detect a stopped scheduler.
        await db.check(0)
        running = request.app.state.monitor.running
        if enable_monitor and not running:
            raise HTTPException(503, "Monitoring loop is not running")
        return {"status": "ok", "monitor_running": running}

    @app.get("/api/config", response_model=PublicConfig)
    async def config():
        return {
            "read_only": settings.read_only,
            "interval_seconds": settings.interval_seconds,
            "timeout_seconds": settings.timeout_seconds,
            "concurrency": settings.concurrency,
            "gap_threshold_seconds": settings.gap_threshold_seconds,
            "max_services": settings.max_services,
        }

    @app.get("/api/dashboard", response_model=Dashboard)
    async def dashboard(db: Database = Depends(database)):
        return await db.dashboard()

    @app.get("/api/services", response_model=list[Service])
    async def services(db: Database = Depends(database)):
        return await db.services()

    @app.post("/api/services", response_model=Service, status_code=201, dependencies=[Depends(writable)])
    async def add_service(body: ServiceCreate, db: Database = Depends(database)):
        try:
            service_id = await db.create_service(body.name, str(body.url))
        except sqlite3.IntegrityError:
            raise HTTPException(409, "This URL is already being monitored") from None
        except ServiceLimitError:
            raise HTTPException(
                409, f"The limit of {settings.max_services} services has been reached"
            ) from None
        return await require_service(service_id, db)

    @app.get("/api/services/{service_id}", response_model=Service)
    async def service(service_id: int, db: Database = Depends(database)):
        return await require_service(service_id, db)

    @app.delete("/api/services/{service_id}", status_code=204, dependencies=[Depends(writable)])
    async def delete_service(service_id: int, db: Database = Depends(database)):
        if not await db.delete_service(service_id):
            raise HTTPException(404, "Service not found")
        return Response(status_code=204)

    @app.get("/api/services/{service_id}/checks", response_model=CheckPage)
    async def checks(
        service_id: int,
        limit: int = Query(50, ge=1, le=200),
        before: int | None = Query(None, ge=1),
        db: Database = Depends(database),
    ):
        await require_service(service_id, db)
        return await db.checks(service_id, limit, before)

    @app.get("/api/checks/{check_id}", response_model=Check)
    async def check(check_id: int, db: Database = Depends(database)):
        item = await db.check(check_id)
        if item is None:
            raise HTTPException(404, "Check not found")
        return item

    @app.get("/api/incidents", response_model=IncidentPage)
    async def incidents(
        limit: int = Query(50, ge=1, le=200),
        before: int | None = Query(None, ge=1),
        db: Database = Depends(database),
    ):
        return await db.incidents(limit, before)

    @app.get("/api/services/{service_id}/incidents", response_model=IncidentPage)
    async def service_incidents(
        service_id: int,
        limit: int = Query(50, ge=1, le=200),
        before: int | None = Query(None, ge=1),
        db: Database = Depends(database),
    ):
        await require_service(service_id, db)
        return await db.incidents(limit, before, service_id)

    return app
