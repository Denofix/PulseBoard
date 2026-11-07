import pytest
from pydantic import ValidationError

from app.models import ServiceCreate
from app.settings import Settings


@pytest.mark.parametrize(
    "url",
    [
        "http://demo-service:8081/ok",
        "http://192.168.1.4/health",
        "https://example.com/path?key=value",
        "http://localhost:8000",
        "http://[::1]:8000/",
        "http://service_with_underscore:80/",
    ],
)
def test_accepts_local_http_urls(url):
    assert str(ServiceCreate(name=" API ", url=url).url).startswith("http")


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "example.com",
        "",
        "https://user:secret@example.com",
        "http://user@example.com",
        "http://:secret@localhost/",
        "http://example.com/#fragment",
        "http://localhost:0/",
        "http://localhost:99999/",
    ],
)
def test_rejects_unsafe_or_invalid_url_shapes(url):
    with pytest.raises(ValidationError):
        ServiceCreate(name="API", url=url)


@pytest.mark.parametrize("name", ["", "   ", "a" * 101, "API\x00"])
def test_invalid_name(name):
    with pytest.raises(ValidationError):
        ServiceCreate(name=name, url="http://demo-service")


@pytest.mark.parametrize(
    "values",
    [
        {"interval_seconds": 0},
        {"concurrency": 0},
        {"concurrency": 6},
        {"timeout_seconds": 0},
        {"timeout_seconds": 1, "network_timeout_seconds": 2},
        {"interval_seconds": float("nan")},
        {"cors_origins": ["*"]},
        {"cors_origins": ["https://example.com/path"]},
        {"cors_origins": ["https://example.com/"]},
        {"cors_origins": ["https://*.example.com"]},
    ],
)
def test_invalid_settings(values):
    with pytest.raises(ValidationError):
        Settings(**values, _env_file=None)


def test_settings_from_environment(monkeypatch):
    monkeypatch.setenv("PULSE_INTERVAL_SECONDS", "20")
    monkeypatch.setenv("PULSE_READ_ONLY", "true")
    monkeypatch.setenv("PULSE_CORS_ORIGINS", '["https://pulse.example.com"]')
    settings = Settings(_env_file=None)
    assert settings.interval_seconds == 20
    assert settings.read_only
    assert settings.cors_origins == ["https://pulse.example.com"]
