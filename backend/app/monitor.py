import asyncio
import logging

import httpx

from .checker import check_url
from .database import Database
from .models import parse_time, utc_now
from .settings import Settings

logger = logging.getLogger(__name__)


class Monitor:
    def __init__(self, database: Database, client: httpx.AsyncClient, settings: Settings):
        self.database, self.client, self.settings = database, client, settings
        self.semaphore = asyncio.Semaphore(settings.concurrency)
        self.inflight: set[int] = set()
        self.tasks: set[asyncio.Task] = set()
        self.loop_task: asyncio.Task | None = None

    def start(self) -> None:
        if self.loop_task is not None:
            raise RuntimeError("The monitor is already started")
        self.loop_task = asyncio.create_task(self.run(), name="pulseboard-monitor")

    @property
    def running(self) -> bool:
        return self.loop_task is not None and not self.loop_task.done()

    async def stop(self) -> None:
        if self.loop_task:
            self.loop_task.cancel()
            await asyncio.gather(self.loop_task, return_exceptions=True)
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)

    async def run(self) -> None:
        while True:
            try:
                services = await self.database.targets()
                for service in services:
                    latest = service["last_checked_at"]
                    due = (
                        latest is None
                        or (utc_now() - parse_time(latest)).total_seconds() >= self.settings.interval_seconds
                    )
                    if due and service["id"] not in self.inflight:
                        self.inflight.add(service["id"])
                        task = asyncio.create_task(self.run_service(service), name=f"check-{service['id']}")
                        self.tasks.add(task)
                        task.add_done_callback(self.tasks.discard)
            except Exception:
                logger.exception("Scheduler iteration failed; the next iteration will retry")
            await asyncio.sleep(min(1, self.settings.interval_seconds / 2))

    async def run_service(self, service: dict) -> None:
        try:
            async with self.semaphore:
                if not await self.database.exists(service["id"]):
                    return
                observation = await check_url(self.client, service["url"], self.settings.timeout_seconds)
                await self.database.record_check(service["id"], observation)
        except Exception:
            logger.exception("Check failed for service id %s; other services continue", service["id"])
        finally:
            self.inflight.discard(service["id"])
