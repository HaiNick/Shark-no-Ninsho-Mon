# SNM-D01 · MEDIUM

**Isolate Docker networks (public/internal split)**

| Field | Value |
|-------|-------|
| **Priority** | MEDIUM |
| **Phase** | 2 — Short Term (Within Sprint) |
| **File** | `docker-compose.yml` |
| **Status** | ⬜ Open |

---

## Problem

All services share the default bridge network — no isolation between public-facing and internal services.

## Fix

```yaml
networks:
  public:
    driver: bridge
  internal:
    internal: true

services:
  oauth2-proxy:
    networks: [public, internal]
  app:
    networks: [internal]
  caddy:
    networks: [internal]
```

## PR Checkpoints

- [ ] `internal` network defined with `internal: true`
- [ ] Flask app only on `internal` network
- [ ] Caddy only on `internal` network
- [ ] oauth2-proxy on both `public` and `internal`
- [ ] `docker compose up` starts cleanly with new network config
- [ ] End-to-end auth flow still works after network changes
