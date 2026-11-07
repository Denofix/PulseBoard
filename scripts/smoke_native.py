#!/usr/bin/env python3
"""Real HTTP/process smoke test; no browser, containers, or external websites required."""

import argparse
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def wait_for(predicate, description, seconds=20):
    deadline = time.monotonic() + seconds
    last_error = None
    while time.monotonic() < deadline:
        try:
            result = predicate()
            if result:
                print(f"PASS {description}", flush=True)
                return result
        except (httpx.HTTPError, KeyError, TypeError) as error:
            last_error = error
        time.sleep(0.1)
    raise AssertionError(f"Timed out: {description}; {last_error}")


def stop(process):
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend-port", type=int, default=18000)
    parser.add_argument("--demo-port", type=int, default=18081)
    args = parser.parse_args()
    backend = demo = None
    with tempfile.TemporaryDirectory(prefix="pulseboard-smoke-") as directory:
        logs = open(Path(directory) / "processes.log", "w+")
        environment = {
            **os.environ,
            "PULSE_DATABASE_PATH": str(Path(directory) / "pulse.sqlite3"),
            "PULSE_INTERVAL_SECONDS": "1",
            "PULSE_TIMEOUT_SECONDS": "0.2",
            "PULSE_NETWORK_TIMEOUT_SECONDS": "0.1",
            "PULSE_READ_ONLY": "false",
            "PULSE_SEED_DEMO": "false",
        }

        def start_backend():
            return subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(args.backend_port),
                    "--workers",
                    "1",
                    "--timeout-graceful-shutdown",
                    "1",
                ],
                cwd=ROOT / "backend",
                env=environment,
                stdout=logs,
                stderr=logs,
            )

        def start_demo():
            return subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(args.demo_port),
                    "--timeout-graceful-shutdown",
                    "1",
                ],
                cwd=ROOT / "demo-service",
                stdout=logs,
                stderr=logs,
            )

        try:
            with httpx.Client(
                base_url=f"http://127.0.0.1:{args.backend_port}/api",
                timeout=2,
                trust_env=False,
            ) as client:

                def get(path):
                    response = client.get(path)
                    response.raise_for_status()
                    return response.json()

                backend, demo = start_backend(), start_demo()
                wait_for(
                    lambda: get("/health")["monitor_running"],
                    "backend lifespan starts the monitor",
                )
                services = []
                for name, path in [
                    ("Smoke API", "ok"),
                    ("Smoke HTTP 500", "error"),
                    ("Smoke timeout", "slow"),
                ]:
                    response = client.post(
                        "/services",
                        json={
                            "name": name,
                            "url": f"http://127.0.0.1:{args.demo_port}/{path}",
                        },
                    )
                    response.raise_for_status()
                    services.append(response.json()["id"])
                target, error_service, timeout_service = services
                service = lambda: get(f"/services/{target}")
                incidents = lambda: get(f"/services/{target}/incidents")["items"]
                wait_for(
                    lambda: (
                        service()["status"] == "UP" and service()["check_count"] >= 2
                    ),
                    "real HTTP 200 observations",
                )
                wait_for(
                    lambda: (
                        get(f"/services/{error_service}")["latest_check"]["http_status"]
                        == 500
                    ),
                    "real HTTP 500 observation",
                )
                wait_for(
                    lambda: (
                        get(f"/services/{timeout_service}")["latest_check"][
                            "error_type"
                        ]
                        == "TIMEOUT"
                    ),
                    "real slow endpoint reaches the timeout, without a latency value",
                )
                assert (
                    get(f"/services/{timeout_service}")["latest_check"][
                        "response_time_ms"
                    ]
                    is None
                )
                stop(demo)
                wait_for(lambda: service()["status"] == "DOWN", "stopped demo is DOWN")
                count = service()["check_count"]
                wait_for(
                    lambda: service()["check_count"] >= count + 2,
                    "additional failures are recorded",
                )
                assert len(incidents()) == 1 and incidents()[0]["closed_at"] is None
                first = incidents()[0]
                evidence = get(f"/checks/{first['opening_check_id']}")
                assert evidence["status"] == "DOWN" and evidence["service_id"] == target
                print(
                    "PASS repeated failures keep one incident, linked to the exact evidence",
                    flush=True,
                )
                before_restart = service()["check_count"]
                stop(backend)
                time.sleep(
                    3.3
                )  # Deliberately exceed the test configuration's gap threshold.
                backend = start_backend()
                wait_for(
                    lambda: get("/health")["monitor_running"],
                    "backend restarted with the same SQLite file",
                )
                assert service()["check_count"] >= before_restart
                assert incidents()[0]["id"] == first["id"] and len(incidents()) == 1
                wait_for(
                    lambda: any(
                        c["gap_before_seconds"] > 0
                        for c in get(f"/services/{target}/checks")["items"]
                    ),
                    "restart downtime is recorded as an observation gap",
                )
                demo = start_demo()
                wait_for(
                    lambda: (
                        service()["status"] == "UP"
                        and incidents()[0]["closed_at"] is not None
                    ),
                    "first successful response closes the original incident",
                )
                stop(demo)
                wait_for(
                    lambda: len(incidents()) == 2,
                    "a separate outage opens a new incident",
                )
                demo = start_demo()
                wait_for(
                    lambda: (
                        service()["status"] == "UP"
                        and incidents()[0]["closed_at"] is not None
                    ),
                    "second incident recovers",
                )
                count = service()["check_count"]
                wait_for(
                    lambda: service()["check_count"] >= count + 2,
                    "monitoring continues without a browser",
                )
                print(
                    f"Native smoke passed: {service()['check_count']} target observations, 2 closed incidents."
                )
        except BaseException:
            logs.flush()
            logs.seek(0)
            print(logs.read()[-10000:], file=sys.stderr)
            raise
        finally:
            stop(backend)
            stop(demo)
            logs.close()


if __name__ == "__main__":
    main()
