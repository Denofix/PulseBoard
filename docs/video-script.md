# PulseBoard: 80-second video outline

Use actual observations. Prepare the Compose stack and a healthy Demo API before recording.
Keep a terminal with `docker compose stop -t 2 demo-service` and `docker compose start demo-service` ready.
If editing out the sampling wait, show a small “15 seconds later” caption rather than implying instant detection.

| Time | Screen | Narration |
| --- | --- | --- |
| 0–8s | Dashboard, services and metrics | “This is PulseBoard, an open source HTTP monitor for small projects.” |
| 8–19s | Add-service form with the local demo URL | “Add a name and a URL. Checks run on the backend, even when this dashboard is closed.” |
| 19–30s | Service page: actual heartbeat, latency chart, history | “Every heartbeat maps to a real check. You can inspect the status, time to response headers, and any error.” |
| 30–42s | Terminal: stop demo-service; return to dashboard | “Now I'll stop only the monitored service. The next failed check opens one incident.” |
| 42–53s | Repeated failed bars, one open incident, opening-check link | “Repeated failures continue that incident. This link shows the exact check that detected it.” |
| 53–65s | Start demo-service; show UP and resolved incident | “The first successful response closes the incident and records recovery.” |
| 65–74s | Restart backend, then refresh history | “Checks and incidents persist in SQLite. A monitoring gap stays a gap; PulseBoard never invents uptime.” |
| 74–82s | README architecture, tests, final dashboard | “Built with FastAPI, httpx, SQLite, Vue 3 and Docker Compose. Original code is MIT licensed.” |

Only show a public URL if it has actually been deployed and verified. Avoid claiming an SLA,
percentage productivity improvement, or time-weighted uptime from check-based statistics.
