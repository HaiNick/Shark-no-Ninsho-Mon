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

Shark-no-Ninsho-Mon is an opinionated reverse proxy gateway that combines Tailscale Funnel, OAuth2 Proxy, Caddy edge proxy, and a rich Flask dashboard to publish internal services safely. Routes are managed dynamically and hot-reloaded without service interruption. Stay productive whether you deploy from Linux or Windows.

---

## Table of Contents

- [What's inside](#whats-inside)
- [Quick start](#quick-start)
- [Documentation](#documentation)
- [Project structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)
- [Support](#support)

---

## What's inside

### Security & access control
- Google OAuth2 front door with email allow lists
- Tight integration with Tailscale Funnel (no port-forwarding required)
- Configurable upstream TLS verification for zero-trust backends
- Caddy edge proxy with dynamic routing and hot-reload capabilities

### Route management & health
- Web-based Route Manager with create/update/delete/enable/disable
- Dynamic route synchronization via Caddy Admin API (no container restarts)
- Background connectivity checks with configurable intervals
- REST API for automation (`/api/routes`, `/api/routes/<id>/toggle`, etc.)
- Per-route configuration: protocol (HTTP/HTTPS), host preservation, compression settings

### Developer experience
- Cross-platform setup wizard served locally via Flask
- Centralised configuration loader (`app/config.py`) for predictable overrides
- Development mode toggle that bypasses OAuth while you iterate locally
- Separation of concerns: Flask handles control plane, Caddy handles data plane
- Unit tests that cover TinyDB routing logic, Caddy sync, and proxy behaviour

### Operations-friendly by default
- Structured request logging and `/health` heartbeat endpoint
- Headers/logs viewers for quick debugging of forwarded identity
- Hot-reload of routes without service interruption
- Caddy Admin API accessible on port 2019 for advanced operations
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

**Note for Linux users**: If you need to run with `sudo` (for Docker checks), the wizard automatically handles file permissions:
```bash
sudo .venv/bin/python3 setup-wizard.py
```
Files created will be owned by your actual user (not root), and the `.env` will include your user/group IDs for proper Docker volume permissions.

Open your browser to [http://localhost:8080](http://localhost:8080) (or `http://<your-ip>:8080` from another device on your LAN) and follow the guided checks:

1. Confirm Docker, Docker Compose, and Tailscale are installed and running.
2. Paste Google OAuth2 client credentials and a Tailscale Funnel hostname.
3. **Add your authorized email address** (the Google account that will access the dashboard).
4. Generate secrets and save the resulting `.env` and `emails.txt`.
5. (Optional) Start the Docker stack from the wizard once configuration is complete.

The stack will launch three services:
- **Caddy** (port 8080): Edge proxy handling all data plane traffic
- **OAuth2 Proxy** (port 4180): Google OAuth2 authentication layer
- **Flask** (port 8000): Control plane for route management and dashboard

> **Security Note**: The wizard is accessible on your local network only. It is NOT exposed to the internet unless you explicitly configure port forwarding. No authentication is required, so only run it on trusted networks.

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

## Documentation

Comprehensive documentation is available in the `docs/` directory:

### [Architecture](docs/ARCHITECTURE.md)
Deep dive into component design, request flow, and security model.

### [Configuration](docs/CONFIGURATION.md)
Complete reference for environment variables, OAuth2 providers, and advanced settings.

### [Operations](docs/OPERATIONS.md)
Production deployment, monitoring, logging, backup/restore, and maintenance.

### [Troubleshooting](docs/TROUBLESHOOTING.md)
Common issues, diagnostic steps, and solutions (including Docker volume permission fixes).

### [Development](docs/DEVELOPMENT.md)
Local setup, testing, code structure, and contributing guidelines.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Project structure

```
Shark-no-Ninsho-Mon/
├── .github/                     # GitHub configuration
│   ├── ISSUE_TEMPLATE/          # Issue templates
│   ├── copilot-instructions.md  # AI assistant instructions
│   ├── dependabot.yml           # Dependency updates
│   └── pull_request_template.md # PR template
├── app/                         # Flask application
│   ├── static/
│   │   ├── css/                 # Stylesheets
│   │   │   ├── admin.css
│   │   │   ├── animations.css
│   │   │   ├── dashboard.css
│   │   │   ├── emails.css
│   │   │   ├── shared.css
│   │   │   └── style.css
│   │   ├── icons/               # SVG icons
│   │   └── js/                  # JavaScript
│   │       ├── admin.js
│   │       ├── app.js
│   │       ├── config.js
│   │       ├── emails.js
│   │       └── utils.js
│   ├── templates/               # Jinja2 HTML templates
│   │   ├── 404.html
│   │   ├── admin.html
│   │   ├── base.html
│   │   ├── emails.html
│   │   ├── index.html
│   │   ├── logs.html
│   │   ├── route_disabled.html
│   │   └── unauthorized.html
│   ├── test/                    # Unit tests
│   │   ├── test_app.py
│   │   ├── test_caddy_manager.py
│   │   ├── test_classification.py
│   │   └── test_routes_db.py
│   ├── app.py                   # Flask control plane + REST API
│   ├── caddy_manager.py         # Caddy Admin API client
│   ├── config.py                # Centralized settings loader
│   ├── dev.py                   # Local development entry point
│   ├── Dockerfile               # Production container
│   ├── requirements.txt         # Python dependencies
│   └── routes_db.py             # TinyDB route manager
├── caddy/                       # Caddy configuration
│   ├── base.json                # Caddy JSON config template
│   └── Caddyfile                # Base Caddy configuration
├── docs/                        # Comprehensive documentation
│   ├── ARCHITECTURE.md          # System design & request flow
│   ├── CONFIGURATION.md         # Environment variables & settings
│   ├── COOKIE_MANAGEMENT.md     # Cookie configuration guide
│   ├── DEVELOPMENT.md           # Local dev & contributing
│   ├── OPERATIONS.md            # Deployment & maintenance
│   └── TROUBLESHOOTING.md       # Common issues & solutions
├── LICENSES/                    # Third-party licenses
│   └── Apache-2.0.txt
├── setup_templates/             # Setup wizard UI
│   ├── css/
│   │   └── setup_wizard.css
│   ├── js/
│   │   └── setup_wizard.js
│   └── setup_wizard.html
├── .env.template                # Environment variables template
├── .gitignore                   # Git ignore rules
├── CHANGELOG.md                 # Version history
├── docker-compose.yml           # Docker services configuration
├── generate-secrets.py          # Secret generator utility
├── LICENSE                      # MIT License
├── README.md                    # This file
├── SECURITY.md                  # Security policy
├── setup-wizard.py              # Interactive setup wizard
└── THIRD_PARTY_NOTICES.md       # Third-party attributions
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Contributing

We welcome contributions! See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for local setup and guidelines.

**Quick steps**:
1. Fork the repository and create a branch: `git checkout -b feature/my-feature`
2. Make your changes and include tests where practical
3. Run tests: `cd app && pytest -q`
4. Open a pull request describing the motivation and testing performed

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## License

This project is distributed under the [MIT License](LICENSE).

---

## Support

- **Issues & bugs**: [github.com/HaiNick/Shark-no-Ninsho-Mon/issues](https://github.com/HaiNick/Shark-no-Ninsho-Mon/issues)
- **Ideas & feedback**: [github.com/HaiNick/Shark-no-Ninsho-Mon/discussions](https://github.com/HaiNick/Shark-no-Ninsho-Mon/discussions)
- **Questions**: Start a discussion or check [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

Before opening an issue, capture:

1. OS and version (Windows, Ubuntu, etc.)
2. Output from `tailscale status`, `docker compose ps`, and key container logs
3. Any modifications to `.env`, Docker Compose, or Route Manager data

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
