# Migration to Caddy Edge Proxy

## What Changed

This PR moves the data path from Flask's WSGI-based proxy to Caddy, while keeping Flask as the route management UI (control plane).

### Before (Flask as Data Path)
```
User → Tailscale Funnel → OAuth2 Proxy → Flask (WSGI proxy) → Backend Services
```

Problems:
- WebSockets don't work reliably through WSGI
- No HTTP/2 support
- Buffering issues with large streams
- Complex redirect rewriting logic

### After (Caddy as Data Path)
```
User → Tailscale Funnel → OAuth2 Proxy → Caddy → Backend Services
                                            ↓
                                       Flask UI (Control Plane)
```

Benefits:
- ✅ WebSockets work natively
- ✅ HTTP/2 support
- ✅ Zero-copy streaming
- ✅ Automatic compression
- ✅ Simpler configuration
- ✅ Better performance

## Architecture

1. **Flask App** (port 8000): 
   - Serves the route management UI
   - Stores routes in TinyDB
   - Syncs routes to Caddy via Admin API on every change
   - Handles health checks and connection testing

2. **Caddy** (port 8080):
   - Edge proxy that handles all data path requests
   - Receives config updates via Admin API (port 2019)
   - Forwards "/" to Flask UI
   - Forwards subdir routes (e.g., /jellyfin) to backends
   - Handles WebSockets, HTTP/2, compression automatically

3. **OAuth2 Proxy** (port 4180):
   - Public entry point
   - Handles Google OAuth authentication
   - Forwards authenticated requests to Caddy

## Files Changed

### New Files
- `app/caddy_manager.py` - Syncs routes to Caddy Admin API
- `caddy/base.json` - Base Caddy configuration
- `docs/edge-proxy-caddy.md` - Architecture documentation
- `docs/MIGRATION.md` - This file

### Modified Files
- `docker-compose.yml` - Added Caddy service, updated OAuth2 Proxy upstream
- `app/app.py` - Added Caddy sync on startup and route changes, removed catch-all proxy route

### Deprecated Files (kept for health checks)
- `app/proxy_handler.py` - Still used for connection testing, but not for data path
- `app/test_proxy_handler.py` - Tests still valid for health check functionality

## Configuration

### Backend Apps Must Be Prefix-Aware

Since we're using subdir routing (e.g., `/jellyfin`, `/grafana`), each backend app needs to know its base path:

#### Jellyfin
1. Dashboard → Networking
2. Base URL: `/jellyfin`
3. Add your proxy IP to Known Proxies
4. Restart Jellyfin

#### Grafana
Edit `grafana.ini`:
```ini
[server]
root_url = %(protocol)s://%(domain)s/grafana/
serve_from_sub_path = true
```

#### BookStack
Edit `.env`:
```env
APP_URL=https://your-funnel-host.ts.net/bookstack
URL_FORCE_ROOT=true
```

#### Other Apps
Most apps support:
- Base path / base URL setting
- Reading `X-Forwarded-Prefix` header
- Reading `X-Forwarded-PathBase` header

## Testing

### Test Caddy is running
```bash
curl http://localhost:2019/config
```

Should return the current Caddy config.

### Test route sync
1. Add a route in the Flask UI
2. Check Caddy config:
```bash
curl -s http://localhost:2019/config | jq .apps.http.servers.srv0.routes
```

You should see your route in the output.

### Test proxying
1. Start the stack: `docker compose up -d`
2. Access via OAuth2 Proxy: `http://localhost:4180`
3. Log in with Google
4. Add a route (e.g., `/jellyfin` → `192.168.1.100:8096`)
5. Access: `http://localhost:4180/jellyfin`

### Test WebSockets
If your backend supports WebSockets (e.g., Jellyfin's real-time updates), they should work automatically through Caddy.

## Rollback

If you need to rollback to the Flask-based proxy:

1. Revert docker-compose.yml:
```yaml
OAUTH2_PROXY_UPSTREAMS: "http://app:8000"  # instead of caddy:8080
```

2. Uncomment the catch-all proxy route in `app/app.py`

3. Remove the `caddy` service from `docker-compose.yml`

4. Restart: `docker compose up -d`

## Troubleshooting

### Route not working
1. Check if enabled in Flask UI
2. Check Caddy config: `curl -s http://localhost:2019/config | jq`
3. Check Caddy logs: `docker compose logs caddy`
4. Test backend directly: `curl http://<backend-ip>:<port>/`

### Caddy sync fails
- Check Caddy is running: `docker compose ps caddy`
- Check network connectivity: `docker compose exec app ping caddy`
- Check Flask logs: `docker compose logs app | grep CADDY_SYNC`

### Backend returns 404 for assets
- Ensure backend's base path is configured correctly
- Check that the backend reads `X-Forwarded-Prefix` header
- Some apps need explicit subpath configuration

## Performance Notes

Caddy is written in Go and uses zero-copy I/O where possible, making it significantly faster than Flask's WSGI proxy for:
- Large file transfers
- Video streaming
- WebSocket connections
- HTTP/2 multiplexing

You should see reduced CPU usage and better response times, especially for media streaming applications like Jellyfin or Plex.
