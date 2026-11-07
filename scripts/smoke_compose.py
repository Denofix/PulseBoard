"""Exercise the real Compose stack using only the Python standard library and Docker CLI."""

import json
import os
import subprocess
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get("PULSE_TEST_API_URL", "http://127.0.0.1:8000/api").rstrip("/")
FRONTEND = os.environ.get("PULSE_TEST_FRONTEND_URL", "http://127.0.0.1:8080").rstrip(
    "/"
)


def request(path, body=None, base=BASE):
    data = json.dumps(body).encode() if body is not None else None
    req = Request(
        base + path,
        data=data,
        headers={"Content-Type": "application/json"} if data else {},
    )
    with urlopen(req, timeout=8) as response:
        return json.load(response)


def compose(*args):
    subprocess.run(["docker", "compose", *args], cwd=ROOT, check=True)


def wait_for(predicate, label, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            value = predicate()
            if value:
                print(f"PASS {label}", flush=True)
                return value
        except (URLError, HTTPError, TimeoutError, ConnectionError, KeyError):
            pass
        time.sleep(0.5)
    raise AssertionError(f"Timed out: {label}")


def main():
    config = request("/config")
    assert not config["read_only"], (
        "Use a local owner-mode stack for this failure drill"
    )
    timeout = max(40, config["interval_seconds"] * 4 + config["timeout_seconds"] * 2)
    services = request("/services")
    target = next(
        (s for s in services if s["url"] == "http://demo-service:8081/ok"), None
    )
    if target is None:
        target = request(
            "/services",
            {"name": "Compose smoke API", "url": "http://demo-service:8081/ok"},
        )
    service_id = target["id"]

    def frontend_ready():
        with urlopen(FRONTEND + f"/services/{service_id}", timeout=5) as response:
            return response.status == 200 and b"PulseBoard" in response.read()

    wait_for(
        frontend_ready, "frontend serves deep routes with the SPA fallback", timeout
    )
    assert (
        request("/api/config", base=FRONTEND)["interval_seconds"]
        == config["interval_seconds"]
    )
    print("PASS frontend /api proxy returns backend JSON", flush=True)
    service = lambda: request(f"/services/{service_id}")
    incidents = lambda: request(f"/services/{service_id}/incidents?limit=200")["items"]
    compose("start", "demo-service")
    wait_for(lambda: service()["status"] == "UP", "demo endpoint is UP", timeout)
    baseline_incidents = len(incidents())
    try:
        compose("stop", "-t", "2", "demo-service")
        wait_for(
            lambda: service()["status"] == "DOWN", "stopped demo becomes DOWN", timeout
        )
        open_incident = incidents()[0]
        count = service()["check_count"]
        wait_for(
            lambda: service()["check_count"] >= count + 2,
            "repeated failures recorded",
            timeout,
        )
        assert len(incidents()) == baseline_incidents + 1
        assert len([i for i in incidents() if i["closed_at"] is None]) == 1
        evidence_id = open_incident["opening_check_id"]
        assert request(f"/checks/{evidence_id}")["status"] == "DOWN"
        print("PASS one open incident with exact check evidence", flush=True)
        count, last_check_id = service()["check_count"], service()["latest_check"]["id"]
        compose("restart", "backend", "frontend")
        wait_for(
            lambda: request("/health")["monitor_running"], "backend restarted", timeout
        )
        assert service()["check_count"] >= count
        assert request(f"/checks/{last_check_id}")["service_id"] == service_id
        assert incidents()[0]["id"] == open_incident["id"]
        print("PASS checks and the open incident survived the restart", flush=True)
    finally:
        compose("start", "demo-service")
    wait_for(
        lambda: service()["status"] == "UP" and incidents()[0]["closed_at"] is not None,
        "recovery closes the same incident",
        timeout,
    )
    count = service()["check_count"]
    wait_for(
        lambda: service()["check_count"] >= count + 2,
        "background checks continue without a browser",
        timeout,
    )
    print("Compose smoke passed. No volumes were removed.", flush=True)


if __name__ == "__main__":
    main()
