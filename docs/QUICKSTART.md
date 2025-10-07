# Quick Start: Caddy Edge Proxy

## TL;DR

Flask manages routes → syncs to Caddy → Caddy proxies everything.

## Start the Stack

```bash
docker compose up -d
docker compose ps  # all services should be running
```

## Access Points

| Service | Port | Purpose |
|---------|------|---------|
| OAuth2 Proxy | 4180 | Public entry point (expose with Tailscale Funnel) |
| Caddy | 8080 | Edge proxy (proxies to backends) |
| Caddy Admin | 2019 | Admin API (receives route updates) |
| Flask UI | 8000 | Route management portal |

## Add a Backend Route

1. Open `http://localhost:4180` (or your Funnel URL)
2. Log in with Google
3. Click "Add Route"
4. Fill in:
   - **Path**: `/jellyfin` (subdir mount point)
   - **Name**: `Jellyfin`
   - **Target IP**: `192.168.1.100`
   - **Target Port**: `8096`
   - **Protocol**: `http`
5. Click "Save"

Route is automatically pushed to Caddy. ✨

## Configure Backend App

Your backend must know its base path:

### Jellyfin
```
Dashboard → Networking
Base URL: /jellyfin
Known Proxies: <your-proxy-ip>
```

### Grafana (grafana.ini)
```ini
[server]
root_url = %(protocol)s://%(domain)s/grafana/
serve_from_sub_path = true
```

### BookStack (.env)
```env
APP_URL=https://your-funnel-host.ts.net/bookstack
URL_FORCE_ROOT=true
```

## Check Caddy Config

```bash
# View full config
curl http://localhost:2019/config | jq

# View routes only
curl -s http://localhost:2019/config | jq .apps.http.servers.srv0.routes
```

## Verify Proxying Works

```bash
# Test via Caddy directly
curl -I http://localhost:8080/jellyfin

# Test via OAuth2 Proxy
curl -I http://localhost:4180/jellyfin
```

## Logs

```bash
# All logs
docker compose logs -f

# Specific service
docker compose logs -f caddy
docker compose logs -f app

# Check Caddy sync
docker compose logs app | grep CADDY_SYNC
```

## Common Issues

### Route not working
```bash
# 1. Check route is enabled in UI
# 2. Check Caddy has the route
curl -s http://localhost:2019/config | jq .apps.http.servers.srv0.routes

# 3. Test backend directly
curl http://<backend-ip>:<backend-port>/
```

### Backend returns 404 for assets
**Problem**: Backend doesn't know it's mounted under a subdir.

**Fix**: Configure backend's base path (see examples above).

### WebSocket connection fails
- Caddy handles WebSockets automatically
- Check browser console for errors
- Ensure backend supports WebSockets

## Expose with Tailscale Funnel

```bash
tailscale serve --reset
tailscale serve --bg --https=443 --set-path=/ http://127.0.0.1:4180
tailscale funnel --bg --https=443 on
```

Access via: `https://<machine-name>.ts.net/`

## Architecture Flow

```
User Request
    ↓
Tailscale Funnel (HTTPS)
    ↓
OAuth2 Proxy :4180 (Authentication)
    ↓
Caddy :8080 (Edge Proxy)
    ↓
├─ / → Flask :8000 (Portal UI)
├─ /jellyfin → Backend 192.168.1.100:8096
├─ /grafana → Backend 192.168.1.101:3000
└─ /bookstack → Backend 192.168.1.102:80
```

## Files You Care About

```
app/
  app.py                 # Flask UI, syncs routes to Caddy
  caddy_manager.py       # Builds Caddy config, calls Admin API
  routes_db.py           # TinyDB route storage

caddy/
  base.json             # Base Caddy config (loaded on startup)

docker-compose.yml      # All services defined here

docs/
  edge-proxy-caddy.md   # Full architecture guide
  MIGRATION.md          # Migration from Flask proxy
  CLEANUP.md            # Optional cleanup guide
```

## Next Steps

1. ✅ Start stack
2. ✅ Add routes via UI
3. ✅ Configure backend base paths
4. ✅ Test access
5. ✅ Expose with Tailscale Funnel
6. 📖 Read `docs/edge-proxy-caddy.md` for details
7. 🧹 Consider cleanup (see `docs/CLEANUP.md`)

## Help

- **Architecture**: `docs/edge-proxy-caddy.md`
- **Migration**: `docs/MIGRATION.md`
- **Cleanup**: `docs/CLEANUP.md`
- **Troubleshooting**: Check logs with `docker compose logs -f`
