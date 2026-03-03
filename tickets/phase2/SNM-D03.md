# SNM-D03 · LOW

**Replace Python health check with wget/curl**

| Field | Value |
|-------|-------|
| **Priority** | LOW |
| **Phase** | 2 — Short Term (Within Sprint) |
| **File** | `docker-compose.yml:23` |
| **Status** | ⬜ Open |

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

- [ ] Health check uses `wget` or `curl` instead of Python
- [ ] `docker compose ps` shows `healthy` status for app container
- [ ] Health check interval, timeout, and retries are explicitly set
