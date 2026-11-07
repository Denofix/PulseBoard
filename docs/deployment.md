# Vercel frontend + persistent FastAPI server

This is prepared configuration, not a completed deployment. No account, server, domain, or public
demo URL has been provisioned. Platform documentation was checked on 2026-11-07:

- [Vercel: Vite and SPA deep links](https://vercel.com/docs/frameworks/frontend/vite)
- [Vercel project configuration](https://vercel.com/docs/project-configuration)
- [FastAPI: containers](https://fastapi.tiangolo.com/deployment/docker/)
- [FastAPI: CORS](https://fastapi.tiangolo.com/tutorial/cors/)
- [Caddy: automatic HTTPS and prerequisites](https://caddyserver.com/docs/automatic-https)

## 1. Prepare the persistent server

Use an Ubuntu server with Docker Engine and Compose v2. Copy or clone this repository, preserving
the `backend`, `demo-service`, and `deploy` directories. Choose a real domain such as `api.your-domain.tld`
and point its A/AAAA records to the server. Remove an unusable AAAA record if IPv6 is unavailable.
Allow inbound TCP 80/443 (and UDP 443 only if desired for HTTP/3).

The supplied public stack exposes only Caddy. FastAPI and demo-service have no host-published ports.
Its backend read-only flag is hardcoded to true. Its volume is separate from the local owner's stack.

```bash
cd pulseboard
cp deploy/.env.example deploy/.env
```

Edit `deploy/.env` with real values, no trailing slash:

```dotenv
API_DOMAIN=api.your-domain.tld
FRONTEND_ORIGIN=https://your-actual-project.vercel.app
```

Use the exact planned Vercel production origin; update it if Vercel assigns a different URL.
Start the separate public stack:

```bash
docker compose --env-file deploy/.env -f deploy/compose.public.yaml up -d --build --wait
docker compose --env-file deploy/.env -f deploy/compose.public.yaml ps
docker compose --env-file deploy/.env -f deploy/compose.public.yaml logs --tail=80 caddy backend
```

Caddy obtains and renews certificates when DNS and port reachability are correct. Its certificate
data and config are persisted. SQLite lives in `pulseboard-public_pulseboard-data` under `/data` in
the backend container. Keep one backend container and one worker; do not scale this service.

Verify actual HTTPS without bypassing certificate checks:

```bash
curl -fsS https://api.your-domain.tld/api/health
curl -fsS https://api.your-domain.tld/api/config
curl -fsS https://api.your-domain.tld/api/services
```

Expected health: `status: ok`, `monitor_running: true`; config: `read_only: true`.
Three seeded services use the same real monitor, including intentional HTTP 500 and timeout failures.
Seeding is idempotent and does not filter or hide any existing database rows.

## 2. Deploy the Vue frontend on Vercel

Push the source to your own GitHub repository, then import that repository into Vercel.

| Setting | Value |
| --- | --- |
| Root Directory | `frontend` |
| Framework Preset | Vite |
| Install Command | `npm ci` |
| Build Command | `npm run build` |
| Output Directory | `dist` |
| Environment variable | `VITE_API_BASE_URL=https://api.your-domain.tld/api` |

Set the variable for the Vercel environments you use, then deploy. `VITE_*` values are public and baked
into the build; changing one requires a new deployment. They contain no keys, tokens or passwords.
The API must use HTTPS when the frontend does. In this split deployment, requests go directly to the
absolute API URL; they do not use the local Vite/Nginx proxy.

`frontend/vercel.json` supplies the SPA rewrite to `/index.html`, so `/services/1` can be opened directly.
It is placed under the selected Root Directory. Default `cleanUrls` behavior is retained.

If the returned Vercel URL differs from `FRONTEND_ORIGIN`, update `deploy/.env` and re-run the public
Compose `up -d` command. CORS accepts only that exact origin. Additional known origins can be configured
by editing the array in the deployment file; do not use a wildcard for random preview deployments.

## 3. Verify before sharing a URL

- Open the exact returned Vercel URL and verify that observations continue changing.
- Open and reload a real `/services/{id}` link directly; it must render, not return a platform 404.
- Check the UI's read-only label and absence of add/delete controls.
- Confirm backend rejection independently of the UI:

```bash
curl -sS -o /tmp/pulseboard-write-response.json -w '%{http_code}\n' \
  -H 'Content-Type: application/json' \
  -d '{"name":"Forbidden","url":"https://example.com"}' \
  https://api.your-domain.tld/api/services
curl -sS -o /tmp/pulseboard-delete-response.json -w '%{http_code}\n' \
  -X DELETE https://api.your-domain.tld/api/services/1
```

Both return **403**. Only run this against the public read-only stack.
Verify `Access-Control-Allow-Origin` with the actual frontend origin:

```bash
curl -i -H 'Origin: https://your-actual-project.vercel.app' \
  https://api.your-domain.tld/api/config
```

The response should include that exact origin. A different origin must not receive the allow-origin
header. CORS restricts browser access; it is not authentication or a network firewall.
Close the browser for at least two intervals, reopen, and confirm intervening server-side observations.
Only after these checks replace the README deployment status with the actual verified URL.

## Backup

For a consistent online backup, use SQLite's backup API instead of copying an active WAL database:

```bash
docker compose --env-file deploy/.env -f deploy/compose.public.yaml exec backend \
  python -c "import sqlite3; src=sqlite3.connect('/data/pulseboard.sqlite3'); dst=sqlite3.connect('/data/pulseboard-backup.sqlite3'); src.backup(dst); dst.close(); src.close()"
docker compose --env-file deploy/.env -f deploy/compose.public.yaml cp \
  backend:/data/pulseboard-backup.sqlite3 ./pulseboard-backup.sqlite3
```

Keep backups outside the server. Do not run `down -v` when updating production. The owner-mode API
remains private behind loopback/SSH; the MVP provides no public owner login. If public writable owner
access becomes necessary, implement authentication and network-target policy before exposing it.
