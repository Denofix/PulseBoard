# PulseBoard user guide

Use PulseBoard to check HTTP services from your own computer or server and investigate failures.
Monitoring continues while the backend runs, even after you close the browser.

- [Install on Linux or an Ubuntu VM](#install-on-linux-or-an-ubuntu-vm)
- [Install on Windows](#install-on-windows)
- [Use the dashboard](#use-the-dashboard)
- [Stop, restart, and update](#stop-restart-and-update)
- [Back up local monitoring data](#back-up-local-monitoring-data)
- [Troubleshooting](#troubleshooting)
- [Keep the Vercel demo online](local-public-demo.md#resume-after-a-vm-shutdown)

## Choose your workspace

| Workspace | What you can do | Where it runs |
| --- | --- | --- |
| Local owner workspace | Add and delete services; inspect checks, charts, and incidents | Your Docker installation, normally at http://127.0.0.1:8080 |
| [Public demo](https://pulse-board-gilt.vercel.app) | Browse the three demo services and their observations | Vercel frontend plus a separate read-only API on the maintainer's VM |

The public demo is temporary. Its live data needs the maintainer's VM, Internet connection,
backend, and tunnel to be running. To monitor your own URLs, install the local owner workspace.

The MVP has no registration, sign-in, or account settings. The **P** badge is a static workspace
avatar. Keep the writable owner workspace private; the public deployment deliberately rejects
adding and deleting services.

## Install on Linux or an Ubuntu VM

Run these commands in a terminal on the machine that will run PulseBoard. For VMware, that means
the terminal **inside Ubuntu**, not the Windows host terminal.

### 1. Prepare Docker and Git

Install Git if needed:

```bash
sudo apt update
sudo apt install -y git curl
```

Install [Docker Engine for Ubuntu](https://docs.docker.com/engine/install/ubuntu/) with the Docker
Compose plugin. For another Linux distribution, follow its
[Docker installation guide](https://docs.docker.com/engine/install/).
If Docker is already installed, keep that installation and check it:

```bash
git --version
sudo docker version
sudo docker compose version
```

Use `docker compose`, not the legacy `docker-compose` command. If the daemon is stopped on Ubuntu:

```bash
sudo systemctl start docker
```

These examples use `sudo` for Docker. You can omit it if your user already has Docker access.
Python and Node.js do not need to be installed on the host for this Compose setup.

### 2. Download and start

Open the folder where you want to keep the project, then run:

```bash
git clone https://github.com/Denofix/PulseBoard.git
cd PulseBoard
test -f .env || cp .env.example .env
sudo docker compose up -d --build --wait
sudo docker compose ps
```

The first build downloads dependencies and takes longer than later starts. The command finishes
after the services are ready. Keep an existing `.env` when restarting or updating.

If you already cloned the repository, open your existing project folder instead of cloning again.

### 3. Open the app

Open **http://127.0.0.1:8080** in a browser on the same Linux machine. In VMware, use the browser
inside the VM. The API documentation is at **http://127.0.0.1:8000/api/docs**.

The default ports bind to loopback. Opening `127.0.0.1:8080` in the Windows host browser does not
connect to an Ubuntu VM. For a server reached over SSH, forward the port from your client:

```bash
ssh -N -L 8080:127.0.0.1:8080 user@your-server
```

Replace `user@your-server` with your SSH login and address. Keep that SSH session open, then visit
http://127.0.0.1:8080 on the client. Use a different local forwarding port if 8080 is already occupied.

## Install on Windows

This runs PulseBoard directly through Docker Desktop. If you use an Ubuntu VMware VM instead,
follow the Linux section inside that VM; Docker Desktop on the Windows host is not required.

### 1. Prepare Docker Desktop and Git

1. Install [Git for Windows](https://git-scm.com/downloads/win).
2. Install [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/).
   Follow its WSL 2 setup instructions and restart Windows if requested.
3. Start Docker Desktop and wait for its engine to be ready. Use Linux containers.
4. Open a new PowerShell window and verify:

```powershell
git --version
docker version
docker compose version
```

Python and Node.js are not needed on Windows for this Compose setup.

### 2. Download and start

Open PowerShell in any folder where you want to keep the project, then run:

```powershell
git clone https://github.com/Denofix/PulseBoard.git
Set-Location PulseBoard
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose up -d --build --wait
docker compose ps
```

Open **http://127.0.0.1:8080** in your Windows browser. API documentation:
**http://127.0.0.1:8000/api/docs**.

For an existing checkout, open that folder and keep its `.env`. There is no required drive letter
or developer-specific installation path.

## Use the dashboard

### Add your first service

1. Open **Overview** or **Services**.
2. Click **Add service** or **Add your first service**.
3. Enter a name, such as `Demo API`.
4. Enter `http://demo-service:8081/ok` as the URL.
5. Click **Add service** and wait for the first completed check.

The new service starts as **Unknown**, then becomes **Up** after a successful response.
The URL is requested by the backend. The Docker hostname `demo-service` does not need to resolve
in your browser, and its external-link button may not open from the host.

For your own service, enter an HTTP or HTTPS URL reachable **from the backend container**.
`localhost` inside that container refers to the container itself. URLs must not contain a username,
password, or fragment. A duplicate URL is rejected.

You can also add these controlled failures to your local workspace:

| Name | URL | Expected observation |
| --- | --- | --- |
| Demo API | `http://demo-service:8081/ok` | Up, HTTP 200, measured response time |
| Demo failure | `http://demo-service:8081/error` | Down, HTTP 500, measured response time |
| Demo timeout | `http://demo-service:8081/slow` | Down, TIMEOUT, no HTTP response or latency |

By default, the backend waits at least 15 seconds after a completed observation before checking that
service again. The total request deadline is 5 seconds. The dashboard normally refreshes every
5 seconds; clicking Refresh fetches recorded data and does not force a new HTTP check.

Only HTTP **200–299** counts as Up. Redirects are not followed; other HTTP statuses and request
errors count as Down.

### Find services and read observations

- Use **Search services** to find a service by name or URL, and **All statuses** to filter the list.
- Open a service name to see its latest response, success ratio, last check, and check interval.
- **Response time** charts show elapsed time until HTTP response headers, in milliseconds.
  They do not measure a complete page download.
- **Recent heartbeat** shows real observations. Hover or focus a marker for details; select a
  check to open its **Check evidence**.
- **Check history** lists individual checks. Click a check ID to inspect its evidence; use
  **Older checks** and **Back to latest** to move through the history.
- On a narrow screen, swipe horizontally inside a wide table to see additional columns.

Green means Up, red means Down, and hatched gaps mean **No observations**. A timeout has no measured
HTTP latency: `—` is missing data, not zero milliseconds. An old Up state marked stale is the last
known observation, not a current availability guarantee.

**Successful checks** is the share of actual checks that succeeded. It is not time-weighted uptime
or an SLA. All displayed check and incident timestamps use **UTC**.

### Investigate incidents

Open **Incidents** or **Recent incidents → View all**. The first failure opens an incident; further
failures update it, and the first successful check resolves it automatically.

Use **Open on this page** or **Resolved on this page** to filter the current history page.
**Older incidents** loads earlier records when available.
Click **Opening check #…** to open the original failed observation, even when it is no longer
on the latest check-history page.

An observed incident span excludes recorded monitoring gaps. Detection and recovery timestamps
describe completed observations, not the exact physical start and end of an outage.

### Delete a service

In the local owner workspace, open the service, click **Delete service**, then **Delete permanently**.
This permanently removes that service, its checks, and its incidents. Cancel if you want to keep them.
Deletion is unavailable in the public demo.

## Stop, restart, and update

Run these commands from the project folder. On Linux, prefix Docker commands with `sudo` if required.

| Action | Command |
| --- | --- |
| Start or resume the owner workspace | `docker compose up -d --wait` |
| Show containers | `docker compose ps` |
| Read backend logs | `docker compose logs --tail=80 backend` |
| Follow logs | `docker compose logs -f backend` |
| Stop containers, keeping data | `docker compose stop` |
| Remove containers/network, keeping data | `docker compose down` |

With `-d`, closing the terminal does not stop the containers. Ctrl+C in a log-following session
stops only the log viewer. Shutting down or suspending the computer or VM stops live monitoring.

To update an existing installation with a clean Git working tree:

```bash
git pull --ff-only
docker compose up -d --build --wait
```

These two commands also work in PowerShell. If Git reports local changes or conflicting histories,
resolve them before updating; do not discard your work to force the update.

History is stored in the `pulseboard_pulseboard-data` Docker volume and survives normal container
recreation. **Do not use `docker compose down -v` when you want to keep your monitoring data.**

## Back up local monitoring data

From the owner project folder, make a consistent SQLite backup and copy it out of the container:

```bash
docker compose exec -T backend python -c "import sqlite3; src=sqlite3.connect('/data/pulseboard.sqlite3'); dst=sqlite3.connect('/data/pulseboard-backup.sqlite3'); src.backup(dst); dst.close(); src.close()"
docker compose cp backend:/data/pulseboard-backup.sqlite3 ./pulseboard-backup.sqlite3
```

Use `sudo docker` on Linux if needed. Both commands work in PowerShell.
Move the backup to a separate safe location; it contains your monitored URLs and history.
There is no automatic history retention in this MVP, so monitor available disk space.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Docker cannot connect to its daemon | Start Docker Desktop on Windows or `sudo systemctl start docker` on Ubuntu. |
| Permission denied for the Docker socket on Linux | Repeat the Docker command with `sudo`. |
| Local page does not open | Run `docker compose ps` and inspect backend logs. Open the browser on the machine running Docker, or use SSH port forwarding for a VM. |
| Port already in use | Change `FRONTEND_PORT`, `BACKEND_PORT`, or `DEMO_PORT` in `.env`, then run `docker compose up -d --build --wait`; open the new frontend port. |
| Add service is missing | A public workspace is read-only. In an owner workspace, API configuration must load successfully before management controls appear. |
| A monitored URL is Down | Check the actual HTTP status/error and reachability from the backend. A redirect also counts as Down. |
| Vercel shows API unavailable | Follow [VM and tunnel recovery](local-public-demo.md#resume-after-a-vm-shutdown); starting the local owner stack alone does not start the public preview. |

For a deeper local check, open http://127.0.0.1:8000/api/health on the Docker host. A healthy response
contains `"status":"ok"` and `"monitor_running":true`. Adjust the port if you changed `BACKEND_PORT`.
Advanced configuration is documented in the [README](../README.md#configuration).

For a reproducible failure/recovery exercise, see [the manual drill](failure-drill.md).
For permanent public hosting, see [the deployment guide](deployment.md).
