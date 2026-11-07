from pathlib import Path

from pydantic import Field, HttpUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PULSE_", env_file=".env", extra="ignore")
    database_path: Path = Path("data/pulseboard.sqlite3")
    interval_seconds: float = Field(default=15, ge=1, le=3600, allow_inf_nan=False)
    timeout_seconds: float = Field(default=5, ge=0.01, le=60, allow_inf_nan=False)
    network_timeout_seconds: float = Field(default=3, ge=0.01, le=60, allow_inf_nan=False)
    concurrency: int = Field(default=5, ge=1, le=5)
    max_services: int = Field(default=100, ge=1, le=1000)
    read_only: bool = False
    seed_demo: bool = False
    demo_base_url: HttpUrl = HttpUrl("http://demo-service:8081")
    cors_origins: list[str] = Field(default_factory=list)

    @field_validator("cors_origins")
    @classmethod
    def exact_origins(cls, values: list[str]) -> list[str]:
        for value in values:
            url = HttpUrl(value)
            if url.username or url.password or url.path not in (None, "/") or url.query or url.fragment:
                raise ValueError("CORS origins must be exact HTTP(S) origins without paths or credentials")
            if value.endswith("/") or "*" in value:
                raise ValueError("CORS origins must not contain wildcards or a trailing slash")
        return values

    @model_validator(mode="after")
    def valid_timeouts(self) -> "Settings":
        if self.network_timeout_seconds > self.timeout_seconds:
            raise ValueError("Network timeout must not exceed the total check timeout")
        if self.demo_base_url.username or self.demo_base_url.password:
            raise ValueError("Demo base URL must not contain credentials")
        return self

    @property
    def gap_threshold_seconds(self) -> float:
        # A completion-to-completion interval includes the next request's duration and scheduler jitter.
        return self.interval_seconds + self.timeout_seconds + max(2, self.interval_seconds * 0.2)
