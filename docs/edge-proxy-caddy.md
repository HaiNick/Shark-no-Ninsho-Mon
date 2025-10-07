# Edge proxy with subdirs (Tailscale Funnel + Caddy)

Goal:
- Keep a single Funnel hostname and mount multiple apps as subdirs: /jellyfin, /grafana, /bookstack.
- Let Caddy handle WebSockets, HTTP/2, buffering, and compression.
- Keep your Flask UI and DB, but use it only as a route manager (control plane).

## How it works

- OAuth2 Proxy stays as the public front door (port 4180).
- OAuth2 Proxy forwards to Caddy (:8080).
- Caddy forwards "/" to Flask UI (portal).
- Each configured route (e.g., /jellyfin) is pushed by Flask to Caddy via Admin API as a reverse_proxy rule.
- Apps must be prefix-aware (set their base path or rely on X-Forwarded-Prefix).

## Run with Funnel

Expose OAuth2 Proxy via Tailscale Funnel:

```bash
tailscale serve --reset
tailscale serve --bg --https=443 --set-path=/ http://127.0.0.1:4180
tailscale funnel --bg --https=443 on
```

## App base path hints

* **Jellyfin**: Base URL = /jellyfin; add proxy IP to Known Proxies; restart Jellyfin.
* **Grafana**: grafana.ini: root_url = %(protocol)s://%(domain)s/grafana/ and serve_from_sub_path = true
* **BookStack**: APP_URL ends with /bookstack; URL_FORCE_ROOT=true
* **Others**: set basePath or rely on X-Forwarded-Prefix.

## Notes

* Caddy Admin API is on :2019; we PUT the full JSON config each time routes change.
* WebSockets work out of the box through Caddy; no special case in Flask.
* If a single app needs Host preservation, set preserve_host=true in that route; we add "Host: {http.request.host}" upstream.

## Architecture

```
User → Tailscale Funnel (HTTPS) → OAuth2 Proxy (4180) → Caddy (8080) → Backend Services
                                                              ↓
                                                         Flask UI (8000)
                                                              ↓
                                                         Route Manager DB
```

## Advantages

1. **WebSockets work reliably** - Caddy handles Upgrade headers natively
2. **HTTP/2 support** - Better performance for modern apps
3. **Zero-copy streaming** - Caddy's Go-based proxy is highly efficient
4. **Subdir routing** - Works perfectly with Tailscale Funnel's single hostname requirement
5. **Simple configuration** - Flask manages routes, Caddy handles the data path
6. **Dynamic updates** - Routes are pushed to Caddy via Admin API when you add/update/delete them

## Troubleshooting

### Route not working
1. Check Caddy config: `curl -s http://localhost:2019/config | jq .apps.http.servers.srv0.routes`
2. Check if route is enabled in Flask UI
3. Verify backend is accessible from Caddy container: `docker exec -it <caddy-container> wget -O- http://<backend-ip>:<port>/`

### WebSocket connection fails
- Ensure backend app supports WebSockets
- Check browser console for errors
- Verify Caddy is proxying the connection (should work automatically)

### Backend returns 404 for assets
- Ensure backend's base path is configured correctly (e.g., Jellyfin Base URL = /jellyfin)
- Check X-Forwarded-Prefix header is being read by the backend
- Some apps need explicit subpath configuration in their settings
