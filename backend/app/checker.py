import asyncio
import socket
import ssl
from dataclasses import dataclass
from time import perf_counter

import httpx

from .models import timestamp


@dataclass(frozen=True)
class Observation:
    checked_at: str
    status: str
    http_status: int | None = None
    response_time_ms: float | None = None
    error_type: str | None = None
    error_message: str | None = None


def connection_error_kind(error: BaseException) -> tuple[str, str]:
    cause: BaseException | None = error
    seen: set[int] = set()
    while cause is not None and id(cause) not in seen:
        seen.add(id(cause))
        if isinstance(cause, socket.gaierror):
            return "DNS", "The hostname could not be resolved"
        if isinstance(cause, (ssl.SSLError, ssl.CertificateError)):
            return "TLS", "The secure connection or certificate could not be verified"
        cause = cause.__cause__ or cause.__context__
    # Some HTTP transports preserve the TLS cause only in their exception text.
    if "CERTIFICATE_VERIFY_FAILED" in str(error) or "SSL:" in str(error):
        return "TLS", "The secure connection or certificate could not be verified"
    return "CONNECTION", "Could not connect to the service"


async def check_url(client: httpx.AsyncClient, url: str, timeout_seconds: float) -> Observation:
    start = perf_counter()
    try:
        async with asyncio.timeout(timeout_seconds):
            # Stop at response headers: do not buffer an unbounded or streaming response body.
            async with client.stream("GET", url, follow_redirects=False) as response:
                latency = round((perf_counter() - start) * 1000, 3)
                status = response.status_code
                return Observation(
                    checked_at=timestamp(),
                    status="UP" if 200 <= status <= 299 else "DOWN",
                    http_status=status,
                    response_time_ms=latency,
                    error_type=None if 200 <= status <= 299 else "HTTP_STATUS",
                    error_message=None if 200 <= status <= 299 else f"Unexpected HTTP status {status}",
                )
    except (TimeoutError, httpx.TimeoutException):
        kind, message = "TIMEOUT", "The request exceeded a network or total time limit"
    except httpx.ConnectError as error:
        kind, message = connection_error_kind(error)
    except httpx.RemoteProtocolError:
        kind, message = "PROTOCOL", "The service returned an invalid HTTP response"
    except httpx.RequestError:
        kind, message = "NETWORK", "The HTTP request failed"
    except Exception:
        kind, message = "INTERNAL", "The check could not be completed"
    return Observation(timestamp(), "DOWN", error_type=kind, error_message=message)
