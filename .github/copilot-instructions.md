# GitHub Copilot Instructions for Shark-no-Ninsho-Mon

## Repository Summary

Shark-no-Ninsho-Mon is an opinionated reverse proxy gateway combining Tailscale Funnel, OAuth2 Proxy, Caddy, and a Flask dashboard to safely publish internal services. Routes are managed dynamically and hot-reloaded without interruption.

**Details**

* Type: Self-hosted reverse proxy with web dashboard
* Languages: Python (Flask), JavaScript, HTML/CSS
* Runtime: Docker Engine 24+ with Docker Compose v2.20+ (plugin)
* Frameworks: Flask 3.0+, Caddy v2, OAuth2-Proxy 7.12+
* Platforms: Linux, macOS, Windows; amd64 and arm64
* Architecture: Microservices via Docker Compose (dev/prod profiles)

## File Creation Policy (for AI assistants)

* Do not create new .md files unless explicitly requested.
* Prioritize code functionality and bug fixes over documentation unless asked.

## Quick Start (TL;DR)

```bash
# Linux/macOS
cp .env.template .env
python generate-secrets.py
# Add OAuth2 provider credentials to .env
docker compose up -d
docker compose ps
# Visit http://localhost:8000 (or APP_PORT from .env)
```

Windows (PowerShell) equivalents:

```powershell
Copy-Item .env.template .env
python generate-secrets.py
docker compose up -d
docker compose ps
```

## Command Execution Context

All commands are executed by the user locally. Ask the user to run commands and paste output back; do not execute terminals yourself.

## Prerequisites

* Python 3.11+ (tested on 3.11.x)
* Docker Engine 24+ and Docker Compose v2.20+ (plugin). On Linux install the package named docker-compose-plugin.
* Optional: Tailscale installed and authenticated for Funnel.

## Environment Setup

1. Copy environment template
   Linux/macOS:

```bash
cp .env.template .env
```

Windows (PowerShell):

```powershell
Copy-Item .env.template .env
```

2. Generate secrets (cookie secrets, salts):

```bash
python generate-secrets.py
```

3. Optional interactive setup:

```bash
python setup-wizard.py
```

## Build and Run

Production profile:

```bash
docker compose build
docker compose up -d
docker compose ps
```

Development mode:

* Set DEV_MODE=true in .env for local development only. Do not commit or deploy with DEV_MODE enabled.
* Run Flask directly:

  ```bash
  cd app
  pip install -r requirements.txt
  python app.py
  ```
* Or use a dev Compose profile (if defined):

  ```bash
  docker compose --profile dev up -d --build
  ```

## Logging and Debugging

```bash
# Linux/macOS/WSL
docker compose logs -f app
docker compose logs -f caddy
docker compose logs -f oauth2-proxy
```

Port checks:

* Linux/macOS: `lsof -iTCP -sTCP:LISTEN -nP | grep -E '8000|8080|4180|2019'`
* Windows: `netstat -ano | findstr "8000 8080 4180 2019"`

## Testing

Tests are under `app/tests/`.

Run all tests:

```bash
cd app
pytest -q
```

Run a single test:

```bash
pytest -q app/tests/test_routes_db.py::test_add_route
```

Coverage (if pytest-cov is installed):

```bash
pytest --cov=./ app/tests
```

## Project Layout

```
├── .env.template
├── .github/
├── app/
├── caddy/
├── docker-compose.yml
├── generate-secrets.py
├── setup-wizard.py
├── setup_templates/
└── LICENSES/
```

### Key Application Files

* `app/app.py`            : Flask entry point
* `app/routes_db.py`      : Route management (TinyDB)
* `app/caddy_manager.py`  : Caddy Admin API integration
* `app/config.py`         : Config management
* `app/static/js/`        : Frontend JS (admin.js, utils.js, config.js)
* `app/templates/`        : Jinja2 templates

### Configuration

* `.env`                  : Environment variables (OAuth2, secrets, hostnames, ports)
* `app/requirements.txt`  : Python dependencies
* `caddy/base.json`       : Caddy base config
* `docker-compose.yml`    : Services and profiles

## Architecture

1. Flask App (APP_PORT, default 8000): route dashboard
2. OAuth2-Proxy (OAUTH2_PROXY_PORT, default 4180): authentication
3. Caddy (CADDY_HTTP_PORT, default 8080): edge proxy with dynamic routing
4. Caddy Admin (CADDY_ADMIN_PORT, default 2019): configuration API

Security-critical note: Caddy Admin must bind to `127.0.0.1:2019` (or a Unix socket). Never expose port 2019 publicly.

## Data Persistence

* `routes.json` : route database (TinyDB). Persist via a named volume or host bind mount.
* `emails.txt`  : allowlist of user emails. Persist similarly.
* Backups: include these files in nightly snapshots. TinyDB provides file-level locking only; avoid concurrent writers and consider periodic compaction.

## Required Environment Variables

Align names with `.env.template`.

* `OAUTH2_PROXY_CLIENT_ID`
* `OAUTH2_PROXY_CLIENT_SECRET`
* `OAUTH2_PROXY_COOKIE_SECRET` (32-byte base64)
* `DEV_MODE` (true/false; development only)
* `APP_PORT`, `CADDY_HTTP_PORT`, `OAUTH2_PROXY_PORT`, `CADDY_ADMIN_PORT`
* Tailscale/Funnel variables if used (for example, `TAILSCALE_FUNNEL_URL`)

## Security Best Practices

* Do not commit `.env`.
* Rotate OAuth2 secrets regularly.
* Set `OAUTH2_PROXY_COOKIE_SECURE=true` behind TLS and `OAUTH2_PROXY_COOKIE_SAMESITE=lax`.
* Restrict login domains in OAuth2-Proxy when feasible.
* Ensure Caddy Admin is bound to localhost and firewalled.
* Enable strict security headers at the edge (Caddy) and verify TLS certificates.

## Common Issues and Workarounds

* Port conflicts:

  * Linux/macOS: `lsof -iTCP -sTCP:LISTEN -nP | grep -E '8000|8080|4180|2019'`
  * Windows: `netstat -ano | findstr "8000 8080 4180 2019"`
  * Adjust ports via `.env` (APP_PORT, CADDY_HTTP_PORT, OAUTH2_PROXY_PORT, CADDY_ADMIN_PORT).
* Docker permissions:

  * Linux: add your user to the `docker` group and re-login.
* OAuth2 setup:

  * Ensure redirect URI matches provider (for example, `http://localhost:4180/oauth2/callback`).
  * Verify `OAUTH2_PROXY_CLIENT_ID`, `OAUTH2_PROXY_CLIENT_SECRET`, and a valid 32-byte cookie secret.

## Code Quality and CI (recommended)

* Python: Ruff, Black, Mypy, Bandit
* JavaScript: ESLint, Prettier
* Images: Trivy scan
* Add GitHub Actions to run lint, tests, and scans on pull requests.
* Consider Renovate to manage dependency updates and image tags/digests.

## Assistant Guidance: When to search further

Search or request new information only if:

* Commands fail with concrete error output the user can paste.
* New or missing dependencies are introduced (check `requirements.txt` or image tags).
* Docker or Compose incompatibilities are suspected (older engine or plugin).
  Avoid generic searches for topics already covered here.
