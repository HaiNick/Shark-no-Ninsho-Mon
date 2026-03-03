# SNM-D01 · MEDIUM

**Isolate Docker networks (public/internal split)**

| Field | Value |
|-------|-------|
| **Priority** | MEDIUM |
| **Phase** | 2 — Short Term (Within Sprint) |
| **File** | `docker-compose.yml` |
| **Status** | ✅ Done |

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

- [x] `internal` network defined with `internal: true`
- [x] Flask app only on `internal` network
- [x] Caddy only on `internal` network
- [x] oauth2-proxy on both `public` and `internal`
- [x] `docker compose up` starts cleanly with new network config
- [x] End-to-end auth flow still works after network changes
