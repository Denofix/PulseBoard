# Reproducible failure drill

Run every command from the `pulseboard` repository root. Keep the default writable owner mode.
This drill stops only the demo service and later restarts PulseBoard. It never removes the volume.
Default monitoring interval: 15 seconds; allow up to about 25 seconds for each visible transition.
The dashboard itself refreshes every five seconds.

## Automated container drill

```bash
cp .env.example .env     # First setup only; do not overwrite an existing configuration
docker compose up -d --build --wait
bash scripts/smoke_compose.sh
```

Expected: PASS lines for success, failure, repeated checks, one incident, restart persistence,
recovery, and background monitoring. The script reuses or creates the demo `/ok` service.
Its `finally` block restarts demo-service if an assertion fails during the outage.
It leaves test observations in the database for inspection.

If Docker requires elevated privileges on your host, run `sudo bash scripts/smoke_compose.sh`.
While the backend restarts, readiness requests can temporarily receive a connection reset, refused
connection, or early disconnect. The runner retries these errors within its existing deadline. A
backend that does not recover still fails the drill instead of being silently marked ready.

## Manual browser and API drill

1. **Start everything.** `docker compose up -d --build --wait`. `docker compose ps` shows backend and
   demo-service healthy, frontend running. Open http://127.0.0.1:8080.
2. **Add a service.** Name `Demo API`, URL `http://demo-service:8081/ok`. If already present, use it.
   Initially `UNKNOWN`, with no fake heartbeat bars or latency values.
3. **Wait for success.** The first observation becomes `UP`, HTTP 200, a measured response time, and a UTC
   timestamp. Wait for a second heartbeat. Open the service page and compare check IDs, values and times.
4. **Stop only the demo.** `docker compose stop -t 2 demo-service`. The next failed check becomes `DOWN`
   with no response code/latency if the connection fails. PulseBoard remains running.
5. **Verify one open incident.** Open Incidents. One new incident for Demo API is open. Its
   **Opening check** link shows the exact failed observation, even if it is outside the current history page.
6. **Wait through repeated failures.** Wait at least two more check cycles. New failed heartbeat entries
   appear; the same incident remains open. No duplicate open incidents exist for that service.
7. **Restore the demo.** `docker compose start demo-service`.
8. **Verify recovery.** The first HTTP 200 becomes `UP` and closes the existing incident. Detection,
   recovery, and observed span are visible. Repeat stop/start to confirm a separate outage creates a new ID.
9. **Verify persistence.** Note a check ID and incident ID, then run
   `docker compose restart backend frontend`. Reopen the same service. Check and incident IDs, counts,
   and history are preserved. A restart gap is hatched in the strip/chart; it is not fabricated downtime.
10. **Close all dashboard tabs.** Note the latest check ID and close the browser tab. Wait 35–45 seconds,
    then reopen the dashboard. The history contains checks taken while the browser was closed.

Optional API inspection (replace `1` with the actual service ID):

```bash
curl -fsS http://127.0.0.1:8000/api/health
curl -fsS http://127.0.0.1:8000/api/services/1
curl -fsS 'http://127.0.0.1:8000/api/services/1/checks?limit=10'
curl -fsS 'http://127.0.0.1:8000/api/services/1/incidents?limit=10'
```

## API failure is a different state

Keep a dashboard tab open, then `docker compose stop backend`. The UI must show **PulseBoard API
unavailable** and explicitly retain the last displayed states. It must not set every target to DOWN.
After the stale threshold, last successful observations are historical, not a live guarantee.
Run `docker compose start backend`; polling should recover without a browser reload. An observation
gap is recorded across runs. Close/reopen the details page to verify direct-route SPA fallback.

## Other deterministic failures

Add `/error` and `/slow` as separate URLs. HTTP 500 is DOWN **with** status and latency. The slow
endpoint is DOWN/TIMEOUT **without** a latency value. With the defaults, the 3-second network inactivity
limit can expire before the 5-second total deadline; both are intentional limits. Unit tests separately
exercise the outer deadline independently of the transport timeout.
