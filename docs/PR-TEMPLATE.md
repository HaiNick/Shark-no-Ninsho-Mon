# Pull Request: Move Data Path to Caddy Edge Proxy

## Summary

This PR migrates the reverse proxy data path from Flask's WSGI-based proxy to Caddy, while keeping Flask as the route management UI (control plane). This architecture change brings WebSocket support, HTTP/2, and better performance while maintaining the existing user experience.

## Architecture Change

### Before
```
User → Tailscale Funnel → OAuth2 Proxy → Flask (WSGI proxy) → Backend Services
```

### After
```
User → Tailscale Funnel → OAuth2 Proxy → Caddy (edge proxy) → Backend Services
                                            ↓
                                       Flask UI (control plane)
```

## Key Benefits

✅ **WebSockets work natively** - No more Upgrade header issues  
✅ **HTTP/2 support** - Better performance for modern apps  
✅ **Zero-copy streaming** - Caddy's Go-based proxy is highly efficient  
✅ **Subdir routing** - Works perfectly with Tailscale Funnel's single hostname  
✅ **Automatic compression** - Caddy handles gzip/brotli automatically  
✅ **Dynamic updates** - Routes pushed to Caddy via Admin API  

## Changes

### New Files
- `app/caddy_manager.py` - Syncs routes to Caddy Admin API
- `caddy/base.json` - Base Caddy configuration with Admin API
- `docs/edge-proxy-caddy.md` - Architecture and configuration guide
- `docs/MIGRATION.md` - Migration guide with troubleshooting

### Modified Files
- `docker-compose.yml` - Added Caddy service, updated OAuth2 Proxy upstream
- `app/app.py` - Added Caddy sync on startup and route changes, removed catch-all proxy

### Deprecated (Optional Cleanup)
These files are no longer used in the data path but kept for health checks:
- `app/proxy_handler.py` - Only used for `test_connection()` now
- `app/test_proxy_handler.py` - Tests for health check functionality

**Optional cleanup**: If you want to simplify, you can:
1. Move `test_connection()` logic to `caddy_manager.py`
2. Remove `proxy_handler.py` and `test_proxy_handler.py`
3. Update health checks to use Caddy's built-in health checking

## Test Plan

### 1. Verify Stack Startup
```bash
docker compose up -d
docker compose ps
# All services should be healthy
```

### 2. Test Caddy Admin API
```bash
curl http://localhost:2019/config | jq
# Should return Caddy config with base route
```

### 3. Add a Route via Flask UI
1. Open `http://localhost:4180`
2. Log in with Google
3. Add route: `/jellyfin` → `192.168.1.100:8096`
4. Verify Caddy config updates:
```bash
curl -s http://localhost:2019/config | jq .apps.http.servers.srv0.routes
# Should show new route
```

### 4. Test Proxying
1. Configure backend app's base path (e.g., Jellyfin Base URL = `/jellyfin`)
2. Access: `http://localhost:4180/jellyfin`
3. Verify assets load correctly
4. Check WebSockets work (if applicable)

### 5. Test Route Management
- **Update route**: Change target IP, verify Caddy config updates
- **Toggle route**: Disable/enable, verify route appears/disappears in Caddy
- **Delete route**: Remove route, verify removed from Caddy config

### 6. Test Health Checks
- Routes with health check enabled should still be monitored
- Check Flask logs for health check results

## Backend Configuration Required

Since we use subdir routing, backends must be prefix-aware:

### Jellyfin
- Dashboard → Networking → Base URL: `/jellyfin`
- Add proxy IP to Known Proxies

### Grafana
```ini
[server]
root_url = %(protocol)s://%(domain)s/grafana/
serve_from_sub_path = true
```

### BookStack
```env
APP_URL=https://your-funnel-host.ts.net/bookstack
URL_FORCE_ROOT=true
```

See `docs/edge-proxy-caddy.md` for more backend examples.

## Rollback Plan

If issues arise, rollback by:
1. Update docker-compose.yml: `OAUTH2_PROXY_UPSTREAMS: "http://app:8000"`
2. Uncomment catch-all proxy route in `app/app.py`
3. Remove `caddy` service from docker-compose.yml
4. Restart: `docker compose up -d`

## Performance Impact

Expected improvements:
- 🚀 Lower CPU usage for streaming (zero-copy I/O)
- 🚀 Better concurrent connection handling
- 🚀 Automatic HTTP/2 server push for static assets
- 🚀 Native WebSocket support without overhead

## Breaking Changes

⚠️ **Backend apps must set base path** - Apps now need to know their subdir mount point. This is a one-time configuration change per app.

⚠️ **Direct Flask proxy removed** - All requests now go through Caddy. The Flask catch-all route is disabled.

## Documentation

- `docs/edge-proxy-caddy.md` - Complete architecture guide
- `docs/MIGRATION.md` - Step-by-step migration with troubleshooting

## Checklist

- [x] Caddy base config created
- [x] CaddyManager class implemented
- [x] Docker compose updated
- [x] Flask app syncs to Caddy on startup
- [x] Flask app syncs on route add/update/delete/toggle
- [x] Documentation written
- [x] Catch-all proxy route removed
- [ ] Tested with real backends (Jellyfin, Grafana, etc.)
- [ ] Verified WebSockets work
- [ ] Verified HTTP/2 works
- [ ] Performance benchmarked

## Next Steps

After merge:
1. Test with production backends
2. Monitor Caddy logs for issues
3. Consider moving health checks to Caddy's built-in health checking
4. Optional: Remove `proxy_handler.py` if health checks migrated

## Questions?

See `docs/MIGRATION.md` for troubleshooting or reach out with any issues.
