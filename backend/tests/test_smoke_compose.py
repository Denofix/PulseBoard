"""Readiness polling must survive a real class of transient restart errors."""

import importlib.util
import io
from http.client import RemoteDisconnected
from pathlib import Path
from unittest.mock import Mock
from urllib.error import HTTPError, URLError

import pytest


class FakeClock:
    def __init__(self):
        self.elapsed = 0.0

    def monotonic(self):
        return self.elapsed

    def sleep(self, seconds):
        self.elapsed += seconds


@pytest.fixture
def smoke(monkeypatch):
    source = Path(__file__).resolve().parents[2] / "scripts" / "smoke_compose.py"
    spec = importlib.util.spec_from_file_location("pulseboard_smoke_compose_test", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    clock = FakeClock()
    monkeypatch.setattr(module, "time", clock)
    return module, clock


@pytest.mark.parametrize(
    "error",
    [
        ConnectionResetError(104, "Connection reset by peer"),
        ConnectionRefusedError(111, "Connection refused"),
        ConnectionAbortedError(103, "Connection aborted"),
        BrokenPipeError(32, "Broken pipe"),
        RemoteDisconnected("Remote end closed connection without response"),
        URLError("API is restarting"),
        HTTPError("http://localhost/api/health", 503, "Service unavailable", None, None),
        TimeoutError("API startup is not complete"),
    ],
)
def test_wait_retries_transient_restart_errors(smoke, error, capsys):
    module, clock = smoke
    predicate = Mock(side_effect=[error, False, {"monitor_running": True}])

    result = module.wait_for(predicate, "backend restarted", 5)

    assert result == {"monitor_running": True}
    assert predicate.call_count == 3
    assert 0 < clock.elapsed < 5
    assert "PASS backend restarted" in capsys.readouterr().out


def test_real_request_helper_recovers_after_a_socket_reset(smoke, monkeypatch):
    module, _clock = smoke
    opener = Mock(
        side_effect=[
            ConnectionResetError(104, "Connection reset by peer"),
            io.BytesIO(b'{"status":"ok","monitor_running":false}'),
            io.BytesIO(b'{"status":"ok","monitor_running":true}'),
        ]
    )
    monkeypatch.setattr(module, "urlopen", opener)

    assert module.wait_for(lambda: module.request("/health")["monitor_running"], "backend restarted", 5)
    assert opener.call_count == 3
    assert all(call.args[0].full_url.endswith("/health") for call in opener.call_args_list)


@pytest.mark.parametrize("outcome", [False, ConnectionResetError(104, "Still restarting")])
def test_unavailable_backend_still_fails_at_the_deadline(smoke, outcome):
    module, clock = smoke
    predicate = Mock(side_effect=outcome) if isinstance(outcome, Exception) else Mock(return_value=outcome)

    with pytest.raises(AssertionError, match="Timed out: backend restarted"):
        module.wait_for(predicate, "backend restarted", 1)

    assert clock.elapsed == 1


@pytest.mark.parametrize(
    "error", [AssertionError("Lost history"), ValueError("Bad payload"), RuntimeError("Bug")]
)
def test_unexpected_failures_are_not_hidden_by_retry(smoke, error):
    module, clock = smoke
    with pytest.raises(type(error), match=str(error)):
        module.wait_for(Mock(side_effect=error), "backend restarted", 5)
    assert clock.elapsed == 0
