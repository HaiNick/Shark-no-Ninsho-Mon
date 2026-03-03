# SNM-D02 · MEDIUM

**Confirm non-root container users for all services**

| Field | Value |
|-------|-------|
| **Priority** | MEDIUM |
| **Phase** | 2 — Short Term (Within Sprint) |
| **File** | `docker-compose.yml` |
| **Status** | ⬜ Open |

---

## Problem

`user:` directive not set for all services. Some images may default to root.

## Fix

Verify each image's default user. Where root, add:

```yaml
user: "1000:1000"
```

## PR Checkpoints

- [ ] Each service verified for its default runtime user
- [ ] `user:` directive added to any service running as root
- [ ] Flask app UID confirmed to match `appuser` in Dockerfile
- [ ] All services start without permission errors after change
