# SNM-D03 · LOW

**Replace Python health check with wget/curl**

| Field | Value |
|-------|-------|
| **Priority** | LOW |
| **Phase** | 2 — Short Term (Within Sprint) |
| **File** | `docker-compose.yml:23` |
| **Status** | ✅ Done |

---

## Problem

Health check depends on Python + requests — unnecessary overhead.

## Fix

```yaml
healthcheck:
  test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

## PR Checkpoints

- [x] Health check uses `urllib.request` instead of `requests` library
- [x] `docker compose ps` shows `healthy` status for app container
- [x] Health check interval, timeout, and retries are explicitly set
