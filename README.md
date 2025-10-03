<a id="readme-top"></a>

# Shark-no-Ninsho-Mon

> Protect every self-hosted web app with Google OAuth, smart routing, and delightful tooling.

[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Tailscale](https://img.shields.io/badge/Tailscale-000000?style=for-the-badge&logo=tailscale&logoColor=white)](https://tailscale.com/)
[![OAuth2](https://img.shields.io/badge/OAuth2-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://developers.google.com/identity/protocols/oauth2)
[![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)

![GitHub stars](https://img.shields.io/github/stars/HaiNick/Shark-no-Ninsho-Mon?style=social)
![GitHub forks](https://img.shields.io/github/forks/HaiNick/Shark-no-Ninsho-Mon?style=social)
![GitHub issues](https://img.shields.io/github/issues/HaiNick/Shark-no-Ninsho-Mon)
![GitHub last commit](https://img.shields.io/github/last-commit/HaiNick/Shark-no-Ninsho-Mon)

Shark-no-Ninsho-Mon is an opinionated reverse proxy gateway that combines Tailscale Funnel, OAuth2 Proxy, and a rich Flask dashboard to publish internal services safely. Manage routes, monitor health, and stay productive whether you deploy from Linux or Windows.

---

## Table of Contents

- [What's inside](#whats-inside)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Architecture](#architecture)
- [Day-2 operations](#day-2-operations)
- [Local development](#local-development)
- [Project structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [Customization](#customization)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgments](#acknowledgments)
- [Support](#support)
- [Star history](#star-history)

---

## What's inside

### Security & access control
- Google OAuth2 front door with email allow lists
- Tight integration with Tailscale Funnel (no port-forwarding required)
- Configurable upstream TLS verification for zero-trust backends

### Route management & health
- Web-based Route Manager with create/update/delete/enable/disable
- Background connectivity checks with configurable intervals
- REST API for automation (`/api/routes`, `/api/routes/<id>/toggle`, etc.)

### Developer experience
- Cross-platform setup wizard served locally via Flask
- Centralised configuration loader (`app/config.py`) for predictable overrides
- Development mode toggle that bypasses OAuth while you iterate locally
- Unit tests that cover TinyDB routing logic and proxy behaviour

### Operations-friendly by default
- Structured request logging and `/health` heartbeat endpoint
- Headers/logs viewers for quick debugging of forwarded identity
- Works seamlessly on Linux, macOS, and Windows machines

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Quick start

Clone the repository first:

```bash
git clone https://github.com/HaiNick/Shark-no-Ninsho-Mon
cd Shark-no-Ninsho-Mon
```

### Option A — Web-based setup wizard (recommended)

The wizard validates prerequisites, generates secrets, and writes your `.env`.

```bash
python -m venv .venv
source .venv/bin/activate        # PowerShell: .venv\Scripts\Activate.ps1
pip install flask
python setup-wizard.py
```

Open your browser to [http://localhost:8080](http://localhost:8080) and follow the guided checks:

1. Confirm Docker, Docker Compose, and Tailscale are installed and running.
2. Paste Google OAuth2 client credentials and a Tailscale Funnel hostname.
3. Generate secrets and save the resulting `.env`.
4. (Optional) Start the Docker stack from the wizard once configuration is complete.

### Option B — Manual configuration & compose

1. Copy the template and edit the resulting file:
   ```bash
   cp .env.template .env
   # Windows PowerShell
   # copy .env.template .env
   ```
2. Fill in the required values (see [Configuration](#configuration)).
3. Allow desired accounts by editing `app/emails.txt` (one email per line).
4. Build and launch the stack:
   ```bash
   docker compose up -d --build
   tailscale funnel --bg 4180
   ```
5. Visit `https://<your-hostname>.ts.net` and sign in with an authorised email.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Configuration

### Required secrets (`.env`)

```bash
# Google OAuth2
OAUTH2_PROXY_CLIENT_ID=your-client-id
OAUTH2_PROXY_CLIENT_SECRET=your-client-secret

# Session cookie secret (32 random bytes, base64)
OAUTH2_PROXY_COOKIE_SECRET=your-cookie-secret

# Tailscale Funnel
FUNNEL_HOST=https://your-hostname.your-tailnet.ts.net
FUNNEL_HOSTNAME=your-hostname.your-tailnet.ts.net
```

Generate a cookie secret:

```bash
# Linux / macOS
head -c 32 /dev/urandom | base64

# Windows PowerShell
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
```

The setup wizard performs these steps automatically, but manual deployments can still follow the template above.

### Optional overrides (read by `app/config.py`)

| Variable | Default | Description |
| --- | --- | --- |
| `ROUTES_DB_PATH` | `/app/routes.json` | TinyDB route store location |
| `EMAILS_FILE` | `/app/emails.txt` | Authorised email list |
| `HEALTH_CHECK_ENABLED` | `true` | Toggle background route health worker |
| `HEALTH_CHECK_INTERVAL` | `300` | Seconds between health probes (>= 0) |
| `UPSTREAM_SSL_VERIFY` | `false` | Verify upstream TLS certificates when proxying |
| `DEV_MODE` | `false` | Bypass OAuth and treat every user as authorised |
| `SECRET_KEY` | auto-generated | Flask session key (wizard fills this in) |

> **Windows note:** Replace Unix-style paths with native paths when running natively (e.g. `ROUTES_DB_PATH=C:\\Users\\you\\Shark-no-Ninsho-Mon\\app\\routes.json`).

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Architecture

### High-level infrastructure

```mermaid
graph TB
  subgraph Client
    U[Internet user]
  end
  subgraph Host[Your Tailscale node]
    subgraph TS[Tailscale]
      Funnel[Tailscale Funnel]
    end
    subgraph Compose[Docker Compose]
      OAuth[oauth2-proxy :4180]
      App[Flask gateway :5000]
      Emails[(emails.txt)]
      Routes[(routes.json)]
    end
  end
  U -->|HTTPS| Funnel
  Funnel --> OAuth
  OAuth -->|X-Forwarded headers| App
  OAuth -.-> Emails
  App -.-> Routes
  OAuth -.->|/oauth2/callback| Google[Google OAuth]
  App -.->|UI/API| U
```

### Request flow

```mermaid
sequenceDiagram
  participant U as User
  participant F as Funnel (HTTPS)
  participant O as oauth2-proxy
  participant G as Google OAuth
  participant A as Flask Gateway
  participant D as Route Manager (TinyDB)

  U->>F: GET https://host.ts.net/
  F->>O: Forward request
  O-->>U: Redirect to Google login
  U->>G: Authenticate
  G-->>O: Authorisation code
  O->>G: Exchange for ID token
  O->>O: Check email against allow list
  O->>A: Forward request with identity headers
  A->>D: Resolve route definition
  A-->>U: Proxy response or dashboard
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Day-2 operations

### Start or update the stack

```bash
docker compose up -d --build
```

### Verify

```bash
# Show running containers
docker compose ps

# Stream application logs
docker compose logs -f app

docker compose logs -f oauth2-proxy

# Check Tailscale Funnel
tailscale funnel status
```

### Stop safely

```bash
# Disable public access
tailscale funnel off

# Stop containers (retain volumes)
docker compose stop

# Tear everything down
docker compose down
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Local development

1. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate        # PowerShell: .venv\Scripts\Activate.ps1
   pip install -r app/requirements.txt
   ```
2. Copy `.env.template` to `.env` and set `DEV_MODE=true` (no OAuth required).
3. Run the development server:
   ```bash
   python app/dev.py
   ```
4. Visit [http://localhost:8000](http://localhost:8000). The dev runner auto-adds `dev@localhost` to the allow list and keeps health checks disabled unless you opt in.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Project structure

```
Shark-no-Ninsho-Mon/
├── docker-compose.yml
├── setup-wizard.py              # Cross-platform configuration wizard
├── setup_templates/             # Wizard UI assets
├── generate-secrets.py          # Stand-alone secret generator
├── app/
│   ├── app.py                   # Flask gateway + REST API
│   ├── config.py                # Centralised settings loader
│   ├── proxy_handler.py         # Reverse proxy implementation
│   ├── routes_db.py             # TinyDB route manager
│   ├── dev.py                   # Local development entry point
│   ├── requirements.txt         # Python dependencies
│   ├── templates/               # Jinja templates for UI
│   └── static/                  # CSS/JS assets
├── README.md
├── CHANGELOG.md
├── SECURITY.md
└── LICENSE
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Troubleshooting

### Docker or Compose issues

```bash
# Permission problems
sudo docker compose up -d --build

# Tail container logs
docker compose logs -f app
docker compose logs -f oauth2-proxy
```

### Tailscale Funnel issues

```bash
# Ensure the daemon is connected
tailscale status

# Restart the funnel
tailscale funnel off
tailscale funnel --bg 4180

# Grant operator privileges (Linux)
sudo tailscale set --operator=$USER
```

### Authentication issues

```bash
# Double-check OAuth values
grep OAUTH2 .env

# Inspect authorised emails
cat app/emails.txt

# Confirm redirect URL
python - <<'PY'
from dotenv import dotenv_values
env = dotenv_values('.env')
print(f"https://{env.get('FUNNEL_HOSTNAME','<missing>')}/oauth2/callback")
PY
```

### Route or proxy debugging

```bash
# Check route definitions
python - <<'PY'
from app.routes_db import RouteManager
rm = RouteManager('app/routes.json')
print(rm.get_all_routes())
PY

# Exercise the REST API
curl -H "X-Forwarded-Email: dev@localhost" http://localhost:8000/api/routes
```

### Need a fresh configuration?

Re-run the setup wizard:

```bash
python setup-wizard.py
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Customization

- **Bring your own app:** Replace the Flask routes in `app/app.py` or proxy to additional backends through the Route Manager.
- **Integrate with other identity providers:** OAuth2 Proxy supports many providers—adjust the environment variables and compose file accordingly.
- **Harden security:** Enforce IP restrictions, tweak cookie policies, or enable TLS verification upstream using the optional environment variables.
- **Automate routes:** Use the REST API to seed or edit routes from CI/CD pipelines.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Contributing

1. Fork the repository and create a branch: `git checkout -b feature/my-feature`
2. Make your changes and include tests where practical
3. Run the Flask tests or your Linux-based validation pipeline
4. Open a pull request describing the motivation and testing performed

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## License

This project is distributed under the [MIT License](LICENSE).

---

## Acknowledgments

- [Tailscale](https://tailscale.com/) for effortless secure networking
- [OAuth2 Proxy](https://oauth2-proxy.github.io/oauth2-proxy/) for rock-solid auth
- [Dracula Theme](https://draculatheme.com/) inspiration for the setup wizard facelift
- [Material Symbols](https://fonts.google.com/icons) by Google, used under the Apache License 2.0

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Support

- **Issues & bugs:** [github.com/HaiNick/Shark-no-Ninsho-Mon/issues](https://github.com/HaiNick/Shark-no-Ninsho-Mon/issues)
- **Ideas & feedback:** [github.com/HaiNick/Shark-no-Ninsho-Mon/discussions](https://github.com/HaiNick/Shark-no-Ninsho-Mon/discussions)
- **Questions:** Start a discussion or re-run the setup wizard to gather diagnostics

Before opening an issue, capture:

1. OS and version (Windows, Ubuntu, etc.)
2. Output from `tailscale status`, `docker compose ps`, and key container logs
3. Any modifications to `.env`, Docker Compose, or Route Manager data

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Star history

<div align="center">

[![Star History Chart](https://api.star-history.com/svg?repos=HaiNick/Shark-no-Ninsho-Mon&type=Date)](https://star-history.com/#HaiNick/Shark-no-Ninsho-Mon&Date)

</div>

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

<div align="center">

**Made with <3 for secure self-hosting**

[![Star this repo](https://img.shields.io/github/stars/HaiNick/Shark-no-Ninsho-Mon?style=social)](https://github.com/HaiNick/Shark-no-Ninsho-Mon)
•
[![Report Bug](https://img.shields.io/badge/Report-Bug-red)](https://github.com/HaiNick/Shark-no-Ninsho-Mon/issues)
•
[![Request Feature](https://img.shields.io/badge/Request-Feature-blue)](https://github.com/HaiNick/Shark-no-Ninsho-Mon/issues)

If this project helps you, a star goes a long way!

</div>

<p align="right">(<a href="#readme-top">back to top</a>)</p>
