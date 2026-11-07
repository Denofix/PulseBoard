# PulseBoard: 86-second video outline

Use actual observations. Prepare the Compose stack and a healthy Demo API before recording.
Record add-service and failure/recovery actions against the local owner stack. Use the public
read-only Vercel demo for the closing segment.
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
| 74–86s | Public Vercel dashboard, README architecture and tests | “Built with FastAPI, httpx, SQLite, Vue and Docker. The read-only frontend runs on Vercel; its API runs on my local VM. The code is MIT licensed.” |

The verified temporary demo is https://pulse-board-gilt.vercel.app. Check that the VM and tunnel are
running before recording. Describe it as a temporary VM-backed demo. Avoid claiming an SLA,
percentage productivity improvement, or time-weighted uptime from check-based statistics.
