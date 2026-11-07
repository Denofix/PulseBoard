# Temporary public demo from a local VM

Use this when only a local Ubuntu VMware VM is available. The frontend runs on Vercel; an isolated
read-only backend and demo-service run on the VM. Cloudflare Quick Tunnel supplies the temporary
HTTPS API address. No Cloudflare account, domain, or inbound router port forwarding is required.

This is a temporary demonstration, not permanent hosting. The API is available only while the host,
VM, Docker services, Internet connection, and tunnel are running. A new tunnel process receives a
new hostname. Update `VITE_API_BASE_URL` and redeploy the frontend after that hostname changes.
Cloudflare does not guarantee Quick Tunnel uptime. Polling works within its documented limitations.

Official documentation checked on 2026-11-07:

- [Cloudflare Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)
- [Official cloudflared Docker image](https://developers.cloudflare.com/tunnel/downloads/)
- [Vite on Vercel](https://vercel.com/docs/frameworks/frontend/vite)
- [Vercel environment variables](https://vercel.com/docs/environment-variables)

## Verified deployment on 2026-11-07

- Frontend production URL: [pulse-board-gilt.vercel.app](https://pulse-board-gilt.vercel.app).
- API URL during verification: `https://improving-arrived-stations-delivered.trycloudflare.com/api`.
- Exact allowed frontend origin: `https://pulse-board-gilt.vercel.app`.
- Public preflight passed, including read-only HTTP 403 and positive/negative CORS checks.
- The user's browser loaded all three demo services and their real observations.

These URLs describe this deployment, not reusable default values. New deployments must use their own
actual Vercel domain and assigned tunnel address. See [the verification record](verification.md).

## 1. Start the isolated demo API

Run from the repository root. Add `sudo` to Docker commands if required by your VM.
Copy the example once; keep the existing file when resuming a demo:

```bash
test -f deploy/.env.tunnel || cp deploy/tunnel.env.example deploy/.env.tunnel
docker compose --env-file deploy/.env.tunnel -f deploy/compose.tunnel.yaml config --quiet
docker compose --env-file deploy/.env.tunnel -f deploy/compose.tunnel.yaml up -d --build --wait backend demo-service
python3 scripts/check_public_demo.py http://127.0.0.1:8001/api
```

The script must pass before sharing the API. It checks read-only mode before sending any write
probes, verifies the monitoring loop and three seeded endpoints, and requires POST/DELETE to return
403. Its DELETE probe uses the nonexistent service ID zero. No owner data is copied or exposed.

The new Compose project is `pulseboard-preview`, its network is separate, and SQLite is stored in
`pulseboard-preview_preview-data`. The existing `pulseboard` owner project keeps its own database.
The preview API binds only to `127.0.0.1:8001`; demo-service has no published host port.
`PULSE_READ_ONLY=true` and demo seeding are fixed in this deployment file.

The healthy endpoint returns HTTP 200. The other two demonstrate an intentional HTTP 500 and a
timeout. Two open incidents are therefore expected once their first failed checks complete.

## 2. Start the HTTPS tunnel

```bash
docker compose --env-file deploy/.env.tunnel -f deploy/compose.tunnel.yaml up -d tunnel
docker compose --env-file deploy/.env.tunnel -f deploy/compose.tunnel.yaml logs --tail=80 tunnel
```

Find the actual `https://...trycloudflare.com` address in the logs. The tunnel service uses an
explicit Compose profile and does not start during the default local API setup or CI. It connects
only to the preview backend through the preview network. The official `cloudflared:latest` image is
used for this temporary tool; pull it deliberately before a new demo session if an update is needed.

Verify the actual assigned address, including `/api`, without disabling certificate verification:

```bash
python3 scripts/check_public_demo.py https://YOUR-ACTUAL-TUNNEL.trycloudflare.com/api
```

If DNS or the tunnel is still initializing, wait briefly and retry. Until the frontend origin is
configured below, CORS deliberately allows no browser origin; these command-line checks still work.

## 3. Import the frontend into Vercel

Open [New Project](https://vercel.com/new), connect GitHub, and import `Denofix/PulseBoard`.

| Setting | Value |
| --- | --- |
| Root Directory | `frontend` |
| Framework Preset | Vite |
| Install Command | `npm ci` |
| Build Command | `npm run build` |
| Output Directory | `dist` |
| Environment variable | `VITE_API_BASE_URL=https://YOUR-ACTUAL-TUNNEL.trycloudflare.com/api` |

Deploy with that public variable set for Production. Use the actual returned production URL, not a
guessed project hostname. The initial UI may show an API connection error until CORS is configured.
The repository already supplies `frontend/vercel.json` for direct opening of `/services/{id}` routes.

## 4. Allow the exact frontend origin

Edit `deploy/.env.tunnel`, replacing the empty CORS list with the actual production origin:

```dotenv
TUNNEL_BACKEND_PORT=8001
TUNNEL_CORS_ORIGINS=["https://YOUR-ACTUAL-PROJECT.vercel.app"]
```

Use HTTPS with no trailing slash, path, or wildcard. Recreate only the backend; leave the existing
tunnel process running so its hostname remains the same:

```bash
docker compose --env-file deploy/.env.tunnel -f deploy/compose.tunnel.yaml up -d --wait backend
python3 scripts/check_public_demo.py https://YOUR-ACTUAL-TUNNEL.trycloudflare.com/api --origin https://YOUR-ACTUAL-PROJECT.vercel.app
```

This checks positive CORS, the OPTIONS preflight, and the absence of allow-origin headers for an
unrelated origin. CORS is a browser policy; API writes are independently forbidden by the backend.

## 5. Verify before sharing

Open the returned Vercel URL from a browser outside the VM. Confirm all three services, fresh checks,
the read-only indicator, and absent add/delete controls. Open and reload a real `/services/{id}` URL.
Close all dashboard tabs for at least 30 seconds, reopen, and verify the intervening server checks.
Record both actual URLs and the verification date before adding a demo link to the README.

## Pause or stop the preview

Stop public access while keeping backend monitoring and its database:

```bash
docker compose --env-file deploy/.env.tunnel -f deploy/compose.tunnel.yaml stop tunnel
```

Stop the entire preview while keeping its SQLite history:

```bash
docker compose --env-file deploy/.env.tunnel -f deploy/compose.tunnel.yaml --profile tunnel down
```

Do not use `down -v` when you want to keep history. The local owner stack is a different project.
The quick tunnel intentionally does not auto-start after a VM reboot. Starting it again may assign
a new URL; repeat the API environment variable and Vercel deployment steps when that happens.

For a stable permanent URL, use the [persistent server deployment](deployment.md), or configure a
managed tunnel with a domain and an always-on backend host.
