import asyncio
import socket
import ssl

import httpx
import pytest

from app.checker import check_url


@pytest.mark.parametrize(
    ("code", "status"), [(200, "UP"), (204, "UP"), (299, "UP"), (301, "DOWN"), (500, "DOWN")]
)
async def test_http_status_and_no_redirect(code, status):
    seen = []

    def handler(request):
        seen.append(request.url)
        return httpx.Response(code, headers={"Location": "http://demo-service/other"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        observation = await check_url(client, "http://demo-service/ok", 1)
    assert observation.status == status
    assert observation.http_status == code
    assert observation.response_time_ms is not None and observation.response_time_ms >= 0
    assert len(seen) == 1
    assert observation.error_type == ("HTTP_STATUS" if status == "DOWN" else None)


@pytest.mark.parametrize("kind", ["network", "total"])
async def test_both_timeout_limits(kind):
    async def handler(request):
        if kind == "network":
            raise httpx.ReadTimeout("test", request=request)
        await asyncio.sleep(0.2)
        return httpx.Response(200)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        observation = await check_url(client, "http://demo-service/slow", 0.01)
    assert observation.status == "DOWN"
    assert observation.error_type == "TIMEOUT"
    assert observation.http_status is None
    assert observation.response_time_ms is None


@pytest.mark.parametrize(
    ("cause", "expected"),
    [
        (ConnectionRefusedError(), "CONNECTION"),
        (socket.gaierror(), "DNS"),
        (ssl.SSLCertVerificationError(), "TLS"),
    ],
)
async def test_connection_errors(cause, expected):
    def handler(request):
        raise httpx.ConnectError("connection failed", request=request) from cause

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        observation = await check_url(client, "https://demo-service", 1)
    assert observation.error_type == expected
    assert observation.http_status is None and observation.response_time_ms is None


async def test_response_body_is_not_consumed():
    class NeverRead(httpx.AsyncByteStream):
        async def __aiter__(self):
            raise AssertionError("Monitoring must stop at response headers")
            yield b""  # pragma: no cover

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, stream=NeverRead()))
    ) as client:
        assert (await check_url(client, "http://demo-service", 1)).status == "UP"
