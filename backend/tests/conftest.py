import httpx
import pytest
import pytest_asyncio

from app.api import create_app
from app.database import Database
from app.settings import Settings


@pytest.fixture
def settings(tmp_path):
    return Settings(database_path=tmp_path / "test.sqlite3", _env_file=None)


@pytest_asyncio.fixture
async def db(settings):
    database = Database(settings)
    await database.open()
    yield database
    await database.close()


@pytest_asyncio.fixture
async def api(settings):
    app = create_app(settings, enable_monitor=False)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client, app.state.database
