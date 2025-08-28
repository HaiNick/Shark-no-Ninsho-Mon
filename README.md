# Shark-no-Ninsho-Mon

> **Secure Public Web Apps with Google OAuth via Tailscale Funnel**

[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Tailscale](https://img.shields.io/badge/Tailscale-000000?style=for-the-badge&logo=tailscale&logoColor=white)](https://tailscale.com/)
[![OAuth2](https://img.shields.io/badge/OAuth2-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://developers.google.com/identity/protocols/oauth2)
[![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)

A **production-ready**, **zero-configuration** solution for exposing self-hosted web applications to the internet with enterprise-grade Google authentication. Built with Tailscale Funnel, OAuth2 Proxy, and Docker for maximum security and minimal setup complexity.

---

## Features

- [SECURE] **Enterprise Google OAuth2 Authentication** - Secure user verification
- [GLOBAL] **Public Internet Access** - Via Tailscale Funnel (no port forwarding)
- [SHIELD] **Zero Trust Security** - Email-based authorization control
- [DOCKER] **Containerized Deployment** - Docker Compose for easy management
- [THEME] **Beautiful Setup Experience** - Interactive scripts with Dracula theme
- [LIGHTNING] **One-Command Deployment** - Automated setup for Linux and Windows
- [MOBILE] **Cross-Platform Support** - Works on Linux, macOS, and Windows
- [REFRESH] **Auto-Recovery** - Intelligent error handling and failsafes

---

## Quick Start

### Automated Setup (Recommended)

**Linux/macOS:**

```bash
# Clone and run
git clone https://github.com/HaiNick/Shark-no-Ninsho-Mon
cd Shark-no-Ninsho-Mon
chmod +x setup.sh
./setup.sh
```

**Windows:**

```powershell
# Clone and run
git clone https://github.com/HaiNick/Shark-no-Ninsho-Mon
cd Shark-no-Ninsho-Mon
.\setup.ps1
```

The interactive setup will guide you through:

- [CHECK] **Prerequisites verification** (Docker, Tailscale, etc.)
- [KEY] **Google OAuth2 credential configuration**
- [HOME] **Tailscale hostname setup**
- [MAIL] **Authorized user email management**
- [ROCKET] **Automatic container deployment**
- [GLOBE] **Tailscale Funnel activation**

### Setup Experience

<details>
<summary>Click to see the beautiful Dracula-themed setup process</summary>

```
    _____ __               __
   / ___// /_  ____ ______/ /__
   \__ \/ __ \/ __ \/ ___/ //_/
  ___/ / / / / /_/ / /  / ,<
 /____/_/ /_/\__,_/_/  /_/|_|

 Shark-no-Ninsho-Mon Setup Script
 =================================

STEP 1: Prerequisites Check
===============================

[OK] Docker is installed
[OK] Docker Compose is available
[OK] Tailscale is running and authenticated

STEP 2: Generate Cookie Secret
==================================

Generated secure cookie secret (Base64 URL-safe)
```

</details>

# 3. Setup allowed users

### Edit emails.txt with allowed Google accounts

# 4. Deploy

docker compose up -d --build
tailscale funnel 4180

# 5. Access your app

### https://your-host.your-tailnet.ts.net

```

---

## Prerequisites

---

## Architecture

```mermaid
graph TB
    Internet[Internet Users]
    Funnel[Tailscale Funnel<br/>your-host.tailnet.ts.net]
    OAuth[OAuth2 Proxy<br/>Google Authentication]
    App[Your Flask App<br/>Protected Content]

    Internet --> Funnel
    Funnel --> OAuth
    OAuth --> App

    OAuth -.-> Google[Google OAuth2<br/>Identity Verification]
    OAuth -.-> Emails[emails.txt<br/>Authorization List]
````

**Security Flow:**

1. [GLOBE] **Public Access** → User visits your Tailscale Funnel URL
2. [LOCK] **Authentication** → OAuth2 Proxy redirects to Google login
3. [CHECK] **Authorization** → Email verified against authorized list
4. [SHARK] **App Access** → User granted access to your protected application

---

## Prerequisites

### Required Software

- **Docker & Docker Compose** - Container runtime
- **Tailscale** - VPN and Funnel access
- **Git** - Repository cloning

### Required Accounts

- **Google Cloud Console** - OAuth2 application setup
- **Tailscale Account** - Funnel capability enabled

### Quick Install Commands

**Ubuntu/Debian:**

```bash
# Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Tailscale
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale login
```

**Windows:**

```powershell
# Docker Desktop - Download from https://www.docker.com/products/docker-desktop
# Tailscale - Download from https://tailscale.com/download/windows
```

---

## Configuration

### Google OAuth2 Setup

1. **Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)**
2. **Create OAuth2 Client ID** (Web application)
3. **Set Authorized Redirect URI:**
   ```
   https://your-hostname.your-tailnet.ts.net/oauth2/callback
   ```
4. **Copy Client ID and Secret** for setup script

### Tailscale Configuration

1. **Enable Funnel** (if not already enabled):
   ```bash
   sudo tailscale funnel --help  # Check if available
   ```
2. **Note your hostname:**
   ```bash
   tailscale status | grep "your-hostname"
   ```
   Look for format: `your-hostname.your-tailnet.ts.net`

### Email Authorization

The setup script will help you configure `emails.txt` with authorized users:

```
# Authorized emails for Shark Authentication
user1@company.com
user2@gmail.com
admin@domain.org
```

FUNNEL_HOSTNAME=your-host.your-tailnet.ts.net

````

**Generate Cookie Secret:**

```bash
# Linux/Mac
head -c 32 /dev/urandom | base64

# Windows PowerShell
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))

# Or use interactive setup (automatically generates)
./setup.sh  # Linux/Mac
.\setup.ps1  # Windows
````

#### 3. User Access Control

Edit `emails.txt` with allowed Google accounts:

```
your.primary@gmail.com
colleague@company.com
# Add break-glass account recommended
```

---

## Deployment

### Start the Stack

```bash
# Build and start services
docker compose up -d --build

# Check service status
docker compose ps
docker compose logs -f oauth2-proxy
```

### Enable Public Access

```bash
# Start Tailscale Funnel
tailscale funnel 4180

# Or run in background
tailscale funnel --bg 4180

# Verify setup
tailscale funnel status
```

---

## Testing & Verification

### Web Testing

1. **Main App:** `https://your-host.your-tailnet.ts.net`

   - Should redirect to Google login
   - Sign in with allowed email
   - See "It works" page with your email

2. **API Endpoints:**
   - `https://your-host.your-tailnet.ts.net/api/whoami` - JSON user info
   - `https://your-host.your-tailnet.ts.net/headers` - Authentication headers

### CLI Verification

```bash
# Check Funnel status
tailscale funnel status

# Verify port binding (Linux)
ss -tulpen | grep 4180

# Check container logs
docker compose logs oauth2-proxy
docker compose logs app
```

---

## Stopping & Cleanup

### Stop Public Access

```bash
# Turn off Funnel
tailscale funnel off

# Verify it's off
tailscale funnel status
```

### Stop Services

````bash
# Stop containers (keep data)
docker compose stop

# Stop and remove containers
docker compose down

---

## Manual Configuration

<details>
<summary>Advanced users can configure manually</summary>

### Environment Variables (`.env`)
```bash
# Google OAuth2 Client Credentials
OAUTH2_PROXY_CLIENT_ID=your-client-id
OAUTH2_PROXY_CLIENT_SECRET=your-client-secret

# Cookie Secret (32 random bytes, URL-safe base64)
OAUTH2_PROXY_COOKIE_SECRET=your-base64-cookie-secret

# Tailscale Funnel Configuration
FUNNEL_HOST=https://your-hostname.your-tailnet.ts.net
FUNNEL_HOSTNAME=your-hostname.your-tailnet.ts.net
````

### Manual Deployment

```bash
# Start services
docker compose up -d --build

# Start Tailscale Funnel
tailscale funnel 4180 &

# Check status
docker compose logs
tailscale funnel status
```

</details>

---

## Project Structure

```
Shark-no-Ninsho-Mon/
├── docker-compose.yml     # Container orchestration
├── .env                   # Environment configuration
├── emails.txt             # Authorized users
├── setup.sh               # Linux/macOS setup script
├── setup.ps1              # Windows PowerShell setup
├── README.md              # This documentation
├── LICENSE                # MIT License
└── app/                   # Flask application
    ├── Dockerfile          # Application container
    ├── app.py              # Main Flask app
    ├── requirements.txt    # Python dependencies
    ├── templates/          # HTML templates
    │   ├── base.html
    │   ├── index.html
    │   ├── headers.html
    │   ├── health_page.html
    │   ├── logs.html
    │   ├── unauthorized.html
    │   └── 404.html
    └── static/             # CSS and JavaScript
        ├── css/style.css
        └── js/app.js
```

---

## Troubleshooting

### Common Issues & Solutions

**Docker Issues:**

```bash
# Permission errors
sudo docker compose up -d --build

# Check container logs
docker compose logs app
docker compose logs oauth2-proxy
```

**Tailscale Funnel Issues:**

```bash
# Check Tailscale status
tailscale status

# Restart funnel with sudo
sudo tailscale funnel 4180

# Set operator permissions
sudo tailscale set --operator=$USER
```

**Authentication Issues:**

```bash
# Verify OAuth2 configuration
cat .env | grep OAUTH2

# Check authorized emails
cat emails.txt

# Verify redirect URI in Google Console
echo "https://$(grep FUNNEL_HOSTNAME .env | cut -d= -f2)/oauth2/callback"
```

**Access Issues:**

```bash
# Check if services are running
docker compose ps

# Verify Tailscale Funnel status
tailscale funnel status

# Test local access
curl -I http://localhost:4180
```

### Debug Commands

```bash
# Full system check
./setup.sh  # Run setup again for diagnostics

# View all logs
docker compose logs -f

# Check Funnel logs
cat /tmp/tailscale_funnel.log

# Network connectivity test
tailscale ping $(tailscale status --json | jq -r '.Self.DNSName')
```

---

## Customization

### Customize Your App

**Replace the Flask app** with your own application:

1. **Modify `app/app.py`** with your application logic
2. **Update `app/requirements.txt`** with your dependencies
3. **Customize `app/templates/`** with your HTML templates
4. **Add assets to `app/static/`** for CSS/JS/images
5. **Rebuild:** `docker compose up -d --build`

### Advanced Security

**IP Restrictions** (add to `docker-compose.yml`):

```yaml
environment:
  OAUTH2_PROXY_TRUSTED_IPS: "192.168.1.0/24,10.0.0.0/8"
```

**Session Management:**

```yaml
environment:
  OAUTH2_PROXY_COOKIE_EXPIRE: "24h"
  OAUTH2_PROXY_COOKIE_REFRESH: "1h"
```

**Additional OAuth2 Scopes:**

```yaml
environment:
  OAUTH2_PROXY_SCOPE: "openid email profile"
```

---

## Contributing

We welcome contributions! Here's how to get started:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Development Setup

```bash
# Clone your fork
git clone https://github.com/your-username/Shark-no-Ninsho-Mon
cd Shark-no-Ninsho-Mon

# Create development branch
git checkout -b feature/my-feature

# Test your changes
./setup.sh  # Test setup script
docker compose up -d --build  # Test deployment
```

---

## License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- **[Tailscale](https://tailscale.com/)** - For making secure networking simple
- **[OAuth2 Proxy](https://oauth2-proxy.github.io/oauth2-proxy/)** - For robust authentication
- **[Docker](https://www.docker.com/)** - For containerization excellence
- **[Dracula Theme](https://draculatheme.com/)** - For beautiful terminal colors

---

## Support

**Need help?** We're here for you:

- [DOCS] **Documentation:** Check this README thoroughly
- [BUG] **Bug Reports:** [Open an issue](https://github.com/HaiNick/Shark-no-Ninsho-Mon/issues)
- [IDEA] **Feature Requests:** [Start a discussion](https://github.com/HaiNick/Shark-no-Ninsho-Mon/discussions)
- [CHAT] **Community:** Join our discussions for community support

**Before opening an issue:**

1. [CHECK] Run the setup script again to verify configuration
2. [CHECK] Check the troubleshooting section above
3. [CHECK] Include relevant logs and error messages
4. [CHECK] Specify your operating system and versions

---

<div align="center">

**Made with <3 for secure self-hosting**

[Star this repo](https://github.com/HaiNick/Shark-no-Ninsho-Mon) • [Report Bug](https://github.com/HaiNick/Shark-no-Ninsho-Mon/issues) • [Request Feature](https://github.com/HaiNick/Shark-no-Ninsho-Mon/issues)

</div>
