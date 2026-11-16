# Temporary public demo from a local VM

Use this when only a local Ubuntu VMware VM is available. The frontend runs on Vercel; an isolated
read-only backend and demo-service run on the VM. Cloudflare Quick Tunnel supplies the temporary
HTTPS API address. No Cloudflare account, domain, or inbound router port forwarding is required.

This is a temporary demonstration, not permanent hosting. The API is available only while the host,
VM, Docker services, Internet connection, and tunnel are running. A new tunnel process receives a
new hostname. Update `VITE_API_BASE_URL` and redeploy the frontend after that hostname changes.
Cloudflare does not guarantee Quick Tunnel uptime. Polling works within its documented limitations.

Official platform documentation checked on 2026-11-16. The deployment verification below remains
the historical record from 2026-11-07.

- [Cloudflare Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)
- [Official cloudflared Docker image](https://developers.cloudflare.com/tunnel/downloads/)
- [Vite on Vercel](https://vercel.com/docs/frameworks/frontend/vite)
- [Vercel environment variables](https://vercel.com/docs/environment-variables)
- [Vercel Config and Secret types](https://vercel.com/docs/environment-variables/sensitive-environment-variables)

For installation and everyday dashboard use, see the [English user guide](user-guide.md).

## Resume after a VM shutdown

Use this shortcut for an existing checkout and an already configured Vercel project. For the first
setup, follow the numbered sections below. Start the Ubuntu VM, open its terminal, and change to
your existing PulseBoard repository folder. Keep the computer and VM awake with Internet access.

1. Start Docker and the isolated preview API. Copy the environment template only if it is missing:

   ```bash
   sudo systemctl start docker
   test -f deploy/.env.tunnel || cp deploy/tunnel.env.example deploy/.env.tunnel
   sudo docker compose --env-file deploy/.env.tunnel -f deploy/compose.tunnel.yaml up -d --build --wait backend demo-service
   python3 scripts/check_public_demo.py http://127.0.0.1:8001/api
   ```

   This is the `pulseboard-preview` project. Running only `docker compose up` in the repository root
   starts the separate local owner workspace and does not bring the Vercel API online.

2. Check `deploy/.env.tunnel`. For the maintainer's existing deployment it must contain:

   ```dotenv
   TUNNEL_BACKEND_PORT=8001
   TUNNEL_CORS_ORIGINS=["https://pulse-board-gilt.vercel.app"]
   ```

   For your own deployment, use your actual production origin instead, without a path or trailing
   slash. If you edited the file, apply it without restarting the tunnel:

   ```bash
   sudo docker compose --env-file deploy/.env.tunnel -f deploy/compose.tunnel.yaml up -d --wait backend
   ```

3. Start the tunnel and read its HTTPS URL:

   ```bash
   sudo docker compose --env-file deploy/.env.tunnel -f deploy/compose.tunnel.yaml up -d tunnel
   sudo docker compose --env-file deploy/.env.tunnel -f deploy/compose.tunnel.yaml logs -f --tail=80 tunnel
   ```

   Copy the full `https://...trycloudflare.com` URL printed by cloudflared. An `ip=...` value in a
   connection log is a Cloudflare server address, not your public API URL. Press Ctrl+C to leave the
   log viewer; the detached container keeps running. Allow a short time for DNS/tunnel setup.
   If logs repeat `Unauthorized: Tunnel not found`, use the recovery command in Troubleshooting.

4. Open your Vercel project and select **Environment Variables**. Set `VITE_API_BASE_URL` to the
   current tunnel URL **ending in `/api`**, for example:

   ```text
   https://YOUR-ACTUAL-TUNNEL.trycloudflare.com/api
   ```

   Choose **Config**, since `VITE_*` values are public browser configuration. Select **Production**
   for the public site; add Preview only if you also need branch previews. If the existing value is
   a saved Secret, delete that variable and recreate the same key as Config. Vercel does not allow
   converting a saved Secret to Config in place. Never put passwords or API tokens into this key.

5. When the URL changed, open **Deployments**, redeploy the production deployment with environment
   **Production**, and wait for **Ready**. Use a fresh build; leave **Use existing Build Cache**
   unchecked for this recovery. A Preview deployment does not update the production site.
   If the existing API URL is still correct and working, no environment update or redeploy is needed.

6. Verify the new URL and exact frontend origin, replacing the example tunnel hostname:

   ```bash
   python3 scripts/check_public_demo.py https://YOUR-ACTUAL-TUNNEL.trycloudflare.com/api --origin https://pulse-board-gilt.vercel.app
   ```

   Use your own frontend origin for a fork. Open the Vercel site, reload with Ctrl+Shift+R, and check
   **Read-only demo**, three services, and advancing check timestamps. The intentional HTTP 500 and
   timeout mean one Up service, two Down services, and two open incidents are expected.

The tunnel deliberately has `restart: "no"`; it must be started again after a VM reboot. Every new
Quick Tunnel process can receive a new hostname. The Vercel frontend remains hosted when the VM is
off, but its live API data is unavailable. You can close the terminal and browser after a successful
detached start; keep the host computer, VM, Docker, and tunnel running.

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
| Variable type | Config (public build-time URL) |

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

## Troubleshooting

| Symptom | Recovery |
| --- | --- |
| `Unauthorized: Tunnel not found` repeats | Recreate only the tunnel with the command below, copy its new HTTPS hostname, update the Config variable, and redeploy Production. |
| Vercel refuses a `VITE_*` Secret | Keep the key `VITE_API_BASE_URL`; recreate it as Config. The API URL is public, not a credential. |
| `198.41...` or another bare IP is in the variable | Replace it with the actual `https://...trycloudflare.com/api` URL from the tunnel logs. |
| Local API works, public API fails | Inspect tunnel logs, check the VM's Internet connection, and wait briefly for DNS propagation. |
| Public command-line checks pass, browser fails | Run the check script with `--origin`; verify exact CORS and the URL baked into the latest Production build. |
| Header says Local workspace while API configuration fails | The header can show its fallback label before config loads; it does not mean the public API became writable. Recover API connectivity first. |
| Vercel still calls the old hostname | Update the variable for Production, redeploy Production, then reload the page. |

Recover a dead or invalid tunnel without deleting preview data:

```bash
docker compose --env-file deploy/.env.tunnel -f deploy/compose.tunnel.yaml up -d --no-deps --force-recreate tunnel
docker compose --env-file deploy/.env.tunnel -f deploy/compose.tunnel.yaml logs -f --tail=80 tunnel
```

Add `sudo` when required. The preview backend must already be healthy. This starts a new tunnel
session, so use the newly printed URL and repeat the Vercel variable/redeploy steps above.

For a stable permanent URL, use the [persistent server deployment](deployment.md), or configure a
managed tunnel with a domain and an always-on backend host.
