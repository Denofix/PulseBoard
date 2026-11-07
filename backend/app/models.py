from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


def timestamp(value: datetime | None = None) -> str:
    return (value or utc_now()).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class Status(StrEnum):
    UNKNOWN = "UNKNOWN"
    UP = "UP"
    DOWN = "DOWN"


class ServiceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    url: HttpUrl = Field(max_length=2048)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value or any(ord(char) < 32 for char in value):
            raise ValueError("Enter a nonempty service name without control characters")
        return value

    @field_validator("url")
    @classmethod
    def clean_url(cls, value: HttpUrl) -> HttpUrl:
        if value.username is not None or value.password is not None:
            raise ValueError("URLs must not contain a username or password")
        if value.fragment is not None:
            raise ValueError("Remove the URL fragment; it is not sent in an HTTP request")
        if value.port == 0:
            raise ValueError("Port must be between 1 and 65535")
        return value


class Check(BaseModel):
    id: int
    service_id: int
    checked_at: str
    status: Literal["UP", "DOWN"]
    http_status: int | None
    response_time_ms: float | None
    error_type: str | None
    error_message: str | None
    gap_before_seconds: float


class Service(BaseModel):
    id: int
    name: str
    url: str
    created_at: str
    status: Status
    latest_check: Check | None
    recent_checks: list[Check]
    check_count: int
    success_count: int
    availability_percent: float | None
    stale: bool


class Incident(BaseModel):
    id: int
    service_id: int
    service_name: str
    opened_at: str
    closed_at: str | None
    opening_check_id: int
    closing_check_id: int | None
    reason: str
    last_observed_at: str
    observation_gap_seconds: float
    observed_duration_seconds: float
    elapsed_seconds: float


class CheckPage(BaseModel):
    items: list[Check]
    next_cursor: int | None


class IncidentPage(BaseModel):
    items: list[Incident]
    next_cursor: int | None


class PublicConfig(BaseModel):
    read_only: bool
    interval_seconds: float
    timeout_seconds: float
    concurrency: int
    gap_threshold_seconds: float
    max_services: int


class Dashboard(BaseModel):
    total_services: int
    up_services: int
    down_services: int
    unknown_services: int
    stale_services: int
    open_incidents: int
    check_count: int
    availability_percent: float | None
    generated_at: str
