"""Verify a seeded read-only demo before sharing it; uses only the Python standard library."""

import argparse
import json
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def api_base(value):
    parsed = urlsplit(value)
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path.rstrip("/") != "/api"
    ):
        raise ValueError("Use an HTTP(S) API URL ending in /api, without credentials or query parameters")
    return value.rstrip("/")


def exact_origin(value):
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path
        or parsed.query
        or parsed.fragment
        or "*" in value
    ):
        raise ValueError("Use the exact HTTPS frontend origin without a trailing slash")
    return value


def request(base, path, method="GET", body=None, origin=None, preflight=False):
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if origin:
        headers["Origin"] = origin
    if preflight:
        headers["Access-Control-Request-Method"] = "GET"
    req = Request(
        base + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers=headers,
    )
    try:
        response = urlopen(req, timeout=8)
    except HTTPError as error:
        response = error
    with response:
        raw = response.read()
        try:
            payload = json.loads(raw)
        except ValueError:
            payload = None
        return response.status, response.headers, payload


def verify(base, origin=None):
    base = api_base(base)
    if origin is not None:
        origin = exact_origin(origin)

    status, _, config = request(base, "/config")
    require(status == 200 and isinstance(config, dict), "Public config must return JSON with HTTP 200")
    # Do not send any write probes to an owner-mode API.
    require(config.get("read_only") is True, "Refusing write probes: backend read_only must be true")
    print("PASS backend reports read-only mode", flush=True)

    status, _, health = request(base, "/health")
    require(
        status == 200 and health == {"status": "ok", "monitor_running": True},
        "Backend health or monitoring loop is not ready",
    )
    print("PASS backend is healthy and monitoring is running", flush=True)

    status, _, services = request(base, "/services")
    require(status == 200 and isinstance(services, list), "Services must return a JSON list")
    require(
        len(services) == 3
        and {urlsplit(service["url"]).path for service in services} == {"/ok", "/error", "/slow"},
        "Expected the separate demo database with exactly the three seeded endpoints",
    )
    print("PASS three real demo services are configured", flush=True)

    status, _, _ = request(
        base, "/services", "POST", {"name": "Forbidden probe", "url": "http://demo-service:8081/probe"}
    )
    require(status == 403, f"POST must return 403; got {status}")
    # Zero is never an existing service ID, even if write protection regresses.
    status, _, _ = request(base, "/services/0", "DELETE")
    require(status == 403, f"DELETE must return 403 before looking up a service; got {status}")
    print("PASS backend rejects adding and deleting services with HTTP 403", flush=True)

    if origin is not None:
        status, headers, _ = request(base, "/config", origin=origin)
        require(
            status == 200 and headers.get("Access-Control-Allow-Origin") == origin,
            "CORS does not allow the exact frontend origin",
        )
        status, headers, _ = request(base, "/config", "OPTIONS", origin=origin, preflight=True)
        require(
            status == 200 and headers.get("Access-Control-Allow-Origin") == origin,
            "CORS preflight does not allow the exact frontend origin",
        )
        foreign = "https://untrusted-pulseboard.invalid"
        require(origin != foreign, "Use the actual frontend origin, not the negative-test origin")
        for method in ("GET", "OPTIONS"):
            _, headers, _ = request(
                base, "/config", method, origin=foreign, preflight=method == "OPTIONS"
            )
            require(
                headers.get("Access-Control-Allow-Origin") is None,
                "CORS unexpectedly allows an unrelated origin",
            )
        print("PASS exact-origin CORS and rejection of an unrelated origin", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("api_url", help="For example, http://127.0.0.1:8001/api")
    parser.add_argument("--origin", help="Actual HTTPS frontend origin, without a trailing slash")
    args = parser.parse_args()
    try:
        verify(args.api_url, args.origin)
    except (RuntimeError, OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"FAIL {error}\n")
    print("Public demo checks passed.")


if __name__ == "__main__":
    main()
