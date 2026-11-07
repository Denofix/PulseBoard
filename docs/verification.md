# MVP verification record

Verified on 2026-11-07. Executed checks and prepared deployment work are distinguished below.

## Automated checks executed

| Check | Result | Evidence |
| --- | --- | --- |
| Backend and smoke-runner regression tests | **78 passed** | `python -m pytest backend/tests -q`, 1.03 seconds; includes ten public-demo preflight regression cases |
| Frontend tests | **9 passed** | `npm --prefix frontend test`, two test files |
| Vue / TypeScript type checking | **Passed** | `vue-tsc --noEmit`, included in the build |
| Frontend production build | **Passed** | Vite 7.3.7; JS 138.07 kB / 51.22 kB gzip; vue-tsc and build rerun after updating the repository link |
| Native process smoke test | **Passed** | Real local HTTP; 11 target observations, two closed incidents |
| Read-only preview preflight | **Passed with native HTTP processes** | Three seeded targets; POST/DELETE 403; exact CORS and wrong-origin failure; history and incidents survive backend restart |
| Production dependency audit | **Passed at time checked** | `npm audit --omit=dev --audit-level=high`: zero vulnerabilities reported |
| Compose / public Compose / CI YAML | **Static parse passed** | YAML parsing is not Docker Compose schema or runtime validation |
| Shell syntax | **Passed** | `bash -n scripts/smoke_compose.sh` |
| GitHub Actions | **Passed** | Commit `fc9520a`; backend, frontend, and containers; [run #1](https://github.com/Denofix/PulseBoard/actions/runs/42389935624), total duration 2m 10s |

Backend tests cover HTTP URL and environment validation; HTTP 200/204/299/301/500; disabled redirects;
network and total timeouts; connection, DNS, and TLS errors; and stopping at response headers without
reading the body. Database tests cover UNKNOWN, first failure, repeated failures, recovery, a separate
outage, persistence, pagination, cascade deletion, transaction rollback, and gaps including short restarts.
Scheduler tests cover concurrency, isolation, shutdown, and duplicate prevention across a scheduler tick.
API tests independently verify backend-enforced public-demo HTTP 403 and exact-origin CORS.

The suite now includes 14 smoke-runner regression cases: readiness polling recovers from connection
reset/refused/aborted errors, broken pipes, early disconnects, URL/HTTP errors and timeouts. It also
exercises the real request helper with controlled reset-then-healthy responses, checks the overall
waiting deadline, and ensures assertions and unexpected programming errors still fail immediately.

The native smoke test starts separate actual HTTP processes, stops demo-service, verifies one incident
across repeated failures, restarts FastAPI against the same SQLite file with an incident open, verifies
evidence and observation gaps, restores the demo, repeats an outage, and checks background monitoring.
It uses temporary files and local ports, without external websites or a browser.

## Browser checks executed

The real Vue app was tested against real FastAPI and demo-service through Vite's `/api` proxy.

- Empty onboarding screen, add dialog, and service creation through the UI.
- Healthy endpoint initially UNKNOWN, then UP. HTTP 500 DOWN with a measured latency; timeout DOWN
  with no latency value.
- Search, status filters, service details, latency chart, and an exact opening-check evidence link.
- Keyboard focus showed the corresponding check's timestamp, state, HTTP code and latency.
- Pagination: at 55 observations, the older page contained the remaining five rows.
- Narrow viewport: 390 px iframe, 375 px content width after scrollbar, and 375 px document width.
  Wide tables scroll within their own container. The narrow-screen add form was usable.
- Closed the dashboard tab at **44** observations. Reopening showed **51**, later **55**; monitoring
  continued with no dashboard tab open.
- Stopped the API: a separate **PulseBoard API unavailable** notice appeared; Demo API retained UP
  and the UI labeled its saved data with the last successful refresh time.
- Restarted the processes: the same service had **56** persisted observations and one chart gap.
  Existing demo incidents were retained.
- Read-only mode showed its header label with **zero add/delete controls**. The dashboard continued
  to show actual checks. Backend write rejection was covered independently by the API tests.

Screenshots in `docs/screenshots/` show actual observations. The responsive QA HTML entry is only
used for development and is not an entry in the production build.

## Real Docker Compose verification on the user's VM

The user supplied actual Ubuntu VM terminal output and dashboard screenshots on 2026-11-07:

- All three Docker images built and the Compose stack started. Backend and demo-service were healthy;
  frontend was running. Ports were bound to `127.0.0.1` as intended.
- `/api/health` returned `{"status":"ok","monitor_running":true}`.
- The container drill passed frontend deep-link fallback, Nginx `/api` proxying, successful HTTP checks,
  detection of the stopped demo, repeated failed observations, and one incident with exact evidence.
- Fixed `scripts/smoke_compose.py`: its bounded readiness wait also catches `ConnectionError`, including
  connection resets and early disconnects, and retries until the API is ready or the deadline expires.
  All 68 local tests passed, including the 14 new regression cases. The exact VM patch command was
  checked against the original source and verified to be idempotent.

The user then reran the corrected full drill on the Ubuntu VM. Every assertion passed, ending with:

```text
PASS backend restarted
PASS checks and the open incident survived the restart
PASS recovery closes the same incident
PASS background checks continue without a browser
Compose smoke passed. No volumes were removed.
```

**Full Compose drill: passed.** This verifies Nginx proxying and deep routes, real HTTP failure
detection, continuation of one incident through repeated failures, persistence of checks and the open
incident across a backend restart, recovery closure, and subsequent scheduled observations.
The dashboard screenshots also show two resolved incidents from the two separate induced outages,
no current open incident, real check history, null HTTP/latency values for timeouts, and hatched gaps.
The successful run's outage opened at check #64, and check #67 recorded recovery after a monitoring gap.

The runner makes its assertions through HTTP requests and does not require an open dashboard. It does
not itself close browser tabs. The user subsequently completed the separate manual browser-closed
check on the VM: before closing the tabs, the latest observation was **#101 at 15:42:03 UTC**; after
reopening, it was **#109 at 15:44:03 UTC**. The supplied history screenshots show eight additional
HTTP 200 observations at 15-second intervals over those two minutes. **VM browser-closed check: passed.**

## Public demo verification

Deployed and checked on 2026-11-07 using a Vercel frontend and the separate VM preview stack.

| Check | Result | Evidence |
| --- | --- | --- |
| Vercel production frontend | **Deployed** | Vercel reported Ready / Deployed to Production; initial deployment took 14 seconds |
| Production URL | **Dashboard verified in the user's browser** | [pulse-board-gilt.vercel.app](https://pulse-board-gilt.vercel.app); read-only badge, three services and real observations |
| Preview Docker Compose | **Passed on the Ubuntu VM** | Backend and demo-service healthy; separate `pulseboard-preview_preview-data` volume created |
| Public HTTPS API | **Passed from the VM and user's browser** | Actual Quick Tunnel URL returned `status: ok` and `monitor_running: true`; no certificate bypass |
| Backend write protection | **Passed over the public URL** | `scripts/check_public_demo.py` required read-only configuration and HTTP 403 for POST/DELETE |
| Exact-origin CORS | **Passed over the public URL** | GET and OPTIONS allowed `https://pulse-board-gilt.vercel.app`; an unrelated origin received no allow-origin header |
| Real demo states | **Passed in the deployed dashboard** | Demo API UP / HTTP 200; Demo failure DOWN / HTTP 500; Demo timeout DOWN / TIMEOUT; two open incidents |
| Public SPA fallback | **Passed in the cloud browser** | Direct opening and reload of `/services/1` loaded the Vue application rather than a platform 404 |

The active API URL during verification was
`https://improving-arrived-stations-delivered.trycloudflare.com/api`. The Quick Tunnel runs
`cloudflared` 2026.10.7. It has no permanent hostname or uptime guarantee; the VM and tunnel must stay
running for the dashboard to retrieve live data. See [the temporary demo guide](local-public-demo.md).

The cloud browser loaded the production Vue application but could not retrieve the API data. It
displayed the separate API-unavailable state after one reload. The user's browser and public CLI
preflight succeeded. Dynamic service-detail and incident-evidence interactions on the deployed site
are therefore not claimed as checked by the cloud browser. Their local browser tests remain valid.
The public dashboard screenshot is preserved at `docs/screenshots/public-demo-20261107.png`.

## Remaining deployment checks

- Record the latest GitHub Actions result after the preview and publication changes.
- Complete the deployed service-detail, incident-evidence and narrow-viewport browser checks.
- A permanent always-on API host, stable API hostname, and real Caddy TLS deployment remain future work.

The 5–6 hour target is a planning estimate, not a claim of measured engineering time. Local MVP
acceptance is complete, including the Compose drill and the manual browser-closed check on the VM.
Source publication to [Denofix/PulseBoard](https://github.com/Denofix/PulseBoard) and hosted CI are
complete. The temporary public dashboard, HTTPS API, backend read-only enforcement, and exact-origin
CORS are verified. Permanent hosting and the remaining public browser checks are distinguished above.
