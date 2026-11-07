import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_public_demo.py"
spec = importlib.util.spec_from_file_location("check_public_demo", SCRIPT)
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


@pytest.mark.parametrize("flag", [False, None, "true", 1])
def test_write_probes_require_explicit_read_only_mode(monkeypatch, flag):
    calls = []

    def request(base, path, **kwargs):
        calls.append(path)
        return 200, {}, {"read_only": flag}

    monkeypatch.setattr(demo, "request", request)
    with pytest.raises(RuntimeError, match="Refusing write probes"):
        demo.verify("http://127.0.0.1:8001/api")
    assert calls == ["/config"]


@pytest.mark.parametrize(
    "value",
    ["https://frontend.vercel.app/", "https://frontend.vercel.app/path", "https://*.vercel.app", "http://frontend.vercel.app"],
)
def test_invalid_frontend_origin_is_rejected_before_requests(monkeypatch, value):
    def request(*args, **kwargs):
        pytest.fail("No API request should be made for an invalid origin")

    monkeypatch.setattr(demo, "request", request)
    with pytest.raises(ValueError, match="exact HTTPS frontend origin"):
        demo.verify("http://127.0.0.1:8001/api", value)


@pytest.mark.parametrize("method", ["POST", "DELETE"])
def test_write_protection_must_reject_each_method(monkeypatch, method):
    def request(base, path, request_method="GET", body=None, **kwargs):
        if request_method == method:
            return 201 if method == "POST" else 404, {}, None
        if request_method in ("POST", "DELETE"):
            return 403, {}, None
        if path == "/config":
            return 200, {}, {"read_only": True}
        if path == "/health":
            return 200, {}, {"status": "ok", "monitor_running": True}
        return 200, {}, [{"url": f"http://demo-service:8081/{path}"} for path in ("ok", "error", "slow")]

    monkeypatch.setattr(demo, "request", request)
    with pytest.raises(RuntimeError, match=f"{method} must return 403"):
        demo.verify("http://127.0.0.1:8001/api")
