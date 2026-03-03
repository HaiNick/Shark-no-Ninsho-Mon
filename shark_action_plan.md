# Shark-no-Ninsho-Mon — Fix Action Plan & Task List

**Project:** Shark-no-Ninsho-Mon  
**Review Date:** 2026-03-02  
**Source:** Claude Code Security & Code Quality Review  
**Total Findings:** 25 (7 HIGH · 11 MEDIUM · 5 LOW + 3 Docker/Infra)  
**Agent:** Copilot

> Each ticket has its own file under `tickets/<phase>/`. Click the links below to view full details, fix instructions, and PR checklists.

---

## Phase 1 — Immediate (Before Production)

> All HIGH priority items. Do not ship without these resolved.

| ID | Title | File | Status |
|----|-------|------|--------|
| [SNM-001](tickets/phase1/SNM-001.md) | Remove Caddy Admin API public port exposure | `docker-compose.yml:96` | ⬜ Open |
| [SNM-002](tickets/phase1/SNM-002.md) | Secure / disable setup wizard after initial setup | `setup-wizard.py:833` | ⬜ Open |
| [SNM-003](tickets/phase1/SNM-003.md) | Validate OAuth2 header source in Flask | `app/app.py:144-158` | ⬜ Open |
| [SNM-004](tickets/phase1/SNM-004.md) | Add DEV_MODE safety checks and startup warnings | `app/app.py:155-156` | ⬜ Open |
| [SNM-005](tickets/phase1/SNM-005.md) | Add CSRF protection to all state-changing endpoints | `app/app.py` (all POST/PUT/DELETE) | ⬜ Open |
| [SNM-006](tickets/phase1/SNM-006.md) | Fix email allowlist race conditions with file locking | `app/app.py:584-651` | ⬜ Open |
| [SNM-007](tickets/phase1/SNM-007.md) | Expand SSRF blocklist for cloud metadata IPs | `app/routes_db.py:202-219` | ⬜ Open |

---

## Phase 2 — Short Term (Within Sprint)

> MEDIUM priority items. Required for production reliability and security hardening.

| ID | Title | File | Status |
|----|-------|------|--------|
| [SNM-008](tickets/phase2/SNM-008.md) | Migrate routes storage from TinyDB to SQLite | `app/routes_db.py:37` | ⬜ Open |
| [SNM-009](tickets/phase2/SNM-009.md) | Prevent secrets from printing to console/logs | `setup-wizard.py:278`, `generate-secrets.py:100` | ⬜ Open |
| [SNM-010](tickets/phase2/SNM-010.md) | Reduce rate limit on route test endpoint | `app/app.py:484-507` | ⬜ Open |
| [SNM-011](tickets/phase2/SNM-011.md) | Add concurrency + backoff to health check worker | `app/app.py:861-890` | ⬜ Open |
| [SNM-012](tickets/phase2/SNM-012.md) | Add mutex lock + debounce to Caddy sync | `app/caddy_manager.py:56-87` | ⬜ Open |
| [SNM-013](tickets/phase2/SNM-013.md) | Add input validation on `target_path` | `app/routes_db.py:273` | ⬜ Open |
| [SNM-014](tickets/phase2/SNM-014.md) | Fix insecure TLS verification in health checks | `app/caddy_manager.py:333` | ⬜ Open |
| [SNM-015](tickets/phase2/SNM-015.md) | Tighten email validation regex | `app/app.py:85` | ⬜ Open |
| [SNM-D01](tickets/phase2/SNM-D01.md) | Isolate Docker networks (public/internal split) | `docker-compose.yml` | ⬜ Open |
| [SNM-D02](tickets/phase2/SNM-D02.md) | Confirm non-root container users for all services | `docker-compose.yml` | ⬜ Open |
| [SNM-D03](tickets/phase2/SNM-D03.md) | Replace Python health check with wget/curl | `docker-compose.yml:23` | ⬜ Open |

---

## Phase 3 — Long Term (Next Quarter)

> LOW priority / code quality items. Improve maintainability, observability, and robustness.

| ID | Title | File(s) | Status |
|----|-------|---------|--------|
| [SNM-016](tickets/phase3/SNM-016.md) | Add comprehensive type hints throughout | All Python files | ⬜ Open |
| [SNM-017](tickets/phase3/SNM-017.md) | Extract magic numbers/strings to constants file | Multiple | ⬜ Open |
| [SNM-018](tickets/phase3/SNM-018.md) | Standardize error handling with custom exception classes | `app/errors.py` (new) | ⬜ Open |
| [SNM-019](tickets/phase3/SNM-019.md) | Add request ID tracking middleware | All endpoints | ⬜ Open |
| [SNM-020](tickets/phase3/SNM-020.md) | Fix client-side cache expiration in admin.js | `app/static/js/admin.js:39-46` | ⬜ Open |
| [SNM-021](tickets/phase3/SNM-021.md) | Fix `target_path` default value (`''` → `'/'`) | `app/routes_db.py:66` | ⬜ Open |
| [SNM-022](tickets/phase3/SNM-022.md) | Simplify and harden setup wizard permission fixing | `setup-wizard.py:27-95` | ⬜ Open |
| [SNM-023](tickets/phase3/SNM-023.md) | Pin dependency versions in requirements.lock | `app/requirements.txt` | ⬜ Open |
| [SNM-024](tickets/phase3/SNM-024.md) | Add Flask-Talisman for security headers | `app/app.py` | ⬜ Open |
| [SNM-025](tickets/phase3/SNM-025.md) | Set up automated security scanning (safety, bandit) | CI / `.github/workflows` | ⬜ Open |

---

## Recommended Execution Order

```
Phase 1 (Security — do first, do together):
  SNM-001 → SNM-003 → SNM-004 → SNM-002 → SNM-006 → SNM-005 → SNM-007

Phase 2 (Reliability — next sprint):
  SNM-D01 → SNM-008 → SNM-011 → SNM-012 → SNM-013 → SNM-014 → SNM-009 → SNM-010 → SNM-015 → SNM-D02 → SNM-D03

Phase 3 (Quality — ongoing):
  SNM-018 → SNM-019 → SNM-016 → SNM-017 → SNM-020 → SNM-023 → SNM-024 → SNM-025 → SNM-021 → SNM-022
```