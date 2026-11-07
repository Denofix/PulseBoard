"""Run backend, demo endpoint, and Vite together for native development on Linux/macOS."""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    python = Path(os.environ.get("PULSE_PYTHON", str(ROOT / ".venv/bin/python")))
    if not python.exists():
        python = Path(sys.executable)
    vite = ROOT / "frontend/node_modules/vite/bin/vite.js"
    if not vite.exists():
        raise SystemExit("Install the frontend dependencies: npm --prefix frontend ci")
    env = {
        **os.environ,
        "PULSE_DEMO_BASE_URL": os.environ.get(
            "PULSE_DEMO_BASE_URL", "http://127.0.0.1:8081"
        ),
    }
    commands = [
        [
            str(python),
            "-m",
            "uvicorn",
            "app.main:app",
            "--app-dir",
            "backend",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
            "--workers",
            "1",
            "--timeout-graceful-shutdown",
            "2",
        ],
        [
            str(python),
            "-m",
            "uvicorn",
            "app:app",
            "--app-dir",
            "demo-service",
            "--host",
            "127.0.0.1",
            "--port",
            "8081",
            "--timeout-graceful-shutdown",
            "1",
        ],
        ["node", str(vite), *sys.argv[1:]],
    ]
    children = []
    stopping = False

    def shutdown(*_args):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    try:
        for index, command in enumerate(commands):
            children.append(
                subprocess.Popen(
                    command, cwd=ROOT / "frontend" if index == 2 else ROOT, env=env
                )
            )
        while not stopping and all(child.poll() is None for child in children):
            time.sleep(0.1)
    finally:
        for child in reversed(children):
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
    if not stopping and any(child.returncode for child in children):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
