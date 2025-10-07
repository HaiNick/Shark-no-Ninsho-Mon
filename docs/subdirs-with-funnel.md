# Running Multiple Apps Under Subdirs With Tailscale Funnel

This setup keeps a single Funnel hostname and mounts multiple apps at subpaths like:

- `/jellyfin`
- `/grafana`
- `/bookstack`

Key rules:
1) Make each app aware of its path base (no HTML rewriting).
2) Send `X-Forwarded-Prefix` and `X-Forwarded-PathBase` from the proxy.
3) Proxy must handle redirects and preserve compression; do not re-compress.

## Tailscale Serve / Funnel

Expose your auth front end (oauth2-proxy) and the app portal:

```bash
tailscale serve --reset
tailscale serve --bg --https=443 --set-path=/ http://127.0.0.1:4180
tailscale funnel --bg --https=443 on
```

## App-specific base path settings

Jellyfin:
- Dashboard -> Networking -> Base URL: `/jellyfin`
- Add the proxy host IP to Known Proxies.
- Restart Jellyfin.

Grafana (grafana.ini):
```
server:
  root_url = %(protocol)s://%(domain)s/grafana/
  serve_from_sub_path = true
```

BookStack (example .env):
```
APP_URL=https://YOUR-FUNNEL-HOST/bookstack
URL_FORCE_ROOT=true
```

## Proxy behavior (this repo)

- Streams compressed bytes unchanged (Content-Encoding preserved).
- Strips hop-by-hop headers (including names listed in `Connection`).
- Preserves multi-valued response headers (Set-Cookie, WWW-Authenticate, Link, Warning).
- Rewrites only `Location` for same-backend redirects.
- Sends `X-Forwarded-Prefix` and `X-Forwarded-PathBase` using the mount path.
- Adds `Forwarded` on the upstream request (RFC 7239).

## Sanity checks
1) `curl -i https://YOUR-FUNNEL-HOST/jellyfin` -> `Location: /jellyfin/web/`.
2) Assets: `/jellyfin/web/...` load without HTML rewriting.
3) HEAD requests: no body; `Content-Length` present if upstream provided it.
4) Multi `Set-Cookie`: verify headers are duplicated, not collapsed.
5) Range requests against media URIs return `206` with `Content-Range`.
