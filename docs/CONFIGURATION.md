<a id="configuration-top"></a>

# Configuration

> Complete reference for environment variables, file locations, and configuration options.

[![Back to README](https://img.shields.io/badge/←_Back_to-README-blue?style=for-the-badge)](../README.md)

---

## Table of Contents

- [Environment variables](#environment-variables)
- [Required secrets](#required-secrets)
- [Optional overrides](#optional-overrides)
- [OAuth2 provider setup](#oauth2-provider-setup)
- [Tailscale Funnel setup](#tailscale-funnel-setup)
- [File locations](#file-locations)
- [Advanced configuration](#advanced-configuration)

---

## Environment variables

All configuration is managed via environment variables defined in `.env`. Copy `.env.template` to `.env` and customize for your deployment.

```bash
# Linux / macOS
cp .env.template .env

# Windows PowerShell
Copy-Item .env.template .env
```

<p align="right">(<a href="#configuration-top">back to top</a>)</p>

---

## Required secrets

These variables **must** be set for the application to function:

### Google OAuth2 credentials

```bash
OAUTH2_PROXY_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
OAUTH2_PROXY_CLIENT_SECRET=GOCSPX-your-client-secret-here
```

Obtain from [Google Cloud Console](https://console.cloud.google.com/):
1. Create a new project or select existing
2. Enable Google+ API
3. Create OAuth 2.0 credentials (Web Application)
4. Add authorized redirect URI: `https://your-hostname.ts.net/oauth2/callback`

### Session cookie secret

```bash
OAUTH2_PROXY_COOKIE_SECRET=your-32-byte-base64-secret-here
```

**Generate securely**:

```bash
# Linux / macOS
head -c 32 /dev/urandom | base64

# Windows PowerShell
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))

# Or use the provided script
python generate-secrets.py
```

### Tailscale Funnel hostname

```bash
FUNNEL_HOST=https://your-hostname.your-tailnet.ts.net
FUNNEL_HOSTNAME=your-hostname.your-tailnet.ts.net
```

Find your hostname:
```bash
tailscale status
```

### Flask secret key

```bash
SECRET_KEY=your-flask-session-secret-here
```

**Generate**:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

The setup wizard generates this automatically.

<p align="right">(<a href="#configuration-top">back to top</a>)</p>

---

## Optional overrides

These variables have sensible defaults but can be customized:

### Application behavior

| Variable | Default | Description |
| --- | --- | --- |
| `DEV_MODE` | `false` | **Development only**. Bypasses OAuth authentication. Never enable in production. |
| `APP_PORT` | `8000` | Flask application port (internal) |
| `CADDY_HTTP_PORT` | `8080` | Caddy edge proxy port (internal) |
| `CADDY_ADMIN_PORT` | `2019` | Caddy Admin API port (localhost only) |
| `OAUTH2_PROXY_PORT` | `4180` | OAuth2 Proxy port (internal) |

### Route management

| Variable | Default | Description |
| --- | --- | --- |
| `ROUTES_DB_PATH` | `/app/routes.json` | TinyDB route database location |
| `EMAILS_FILE` | `/app/emails.txt` | Authorized email list location |

**Windows note**: When running natively (not in Docker), use native paths:
```bash
ROUTES_DB_PATH=C:\\Users\\you\\Shark-no-Ninsho-Mon\\app\\routes.json
EMAILS_FILE=C:\\Users\\you\\Shark-no-Ninsho-Mon\\app\\emails.txt
```

### Health checks

| Variable | Default | Description |
| --- | --- | --- |
| `HEALTH_CHECK_ENABLED` | `true` | Enable background route health monitoring |
| `HEALTH_CHECK_INTERVAL` | `300` | Seconds between health probes (minimum 0) |

Set to `false` or `0` to disable health checks entirely.

### Flask session management

| Variable | Default | Description |
| --- | --- | --- |
| `SESSION_COOKIE_SECURE` | `true` | Only send Flask session cookies over HTTPS |
| `SESSION_COOKIE_HTTPONLY` | `true` | Prevent JavaScript access to session cookies |
| `SESSION_COOKIE_SAMESITE` | `Lax` | Cookie SameSite policy (`Lax`, `Strict`, `None`) |
| `PERMANENT_SESSION_LIFETIME` | `604800` | Flask session lifetime in seconds (default: 7 days) |

**Flask session lifetime examples**:
```bash
# 1 hour
PERMANENT_SESSION_LIFETIME=3600

# 1 day
PERMANENT_SESSION_LIFETIME=86400

# 7 days (default, recommended)
PERMANENT_SESSION_LIFETIME=604800

# 30 days
PERMANENT_SESSION_LIFETIME=2592000
```

**Note**: Flask session cookies are separate from OAuth2 Proxy authentication cookies. Flask manages the dashboard session state, while OAuth2 Proxy handles authentication. Both should be configured for your security requirements.

### Upstream connection security

| Variable | Default | Description |
| --- | --- | --- |
| `UPSTREAM_SSL_VERIFY` | `false` | Verify TLS certificates when proxying to HTTPS backends |

**Recommended**: Set to `true` in production if your backends have valid certificates.

### OAuth2 Proxy advanced settings

| Variable | Default | Description |
| --- | --- | --- |
| `OAUTH2_PROXY_COOKIE_SECURE` | `true` | Only send cookies over HTTPS |
| `OAUTH2_PROXY_COOKIE_SAMESITE` | `lax` | Cookie SameSite policy (`lax`, `strict`, `none`) |
| `OAUTH2_PROXY_COOKIE_REFRESH` | `0` | Cookie refresh interval (e.g., `1h`, `24h`, `168h` for weekly, `720h` for monthly) |
| `OAUTH2_PROXY_COOKIE_EXPIRE` | `168h` | Cookie expiration time (default 7 days / 168 hours) |
| `OAUTH2_PROXY_EMAIL_DOMAINS` | `*` | Restrict to specific email domains (e.g., `example.com`) |
| `OAUTH2_PROXY_WHITELIST_DOMAINS` | Not set | Allow redirects to these domains |

**Cookie refresh examples**:
```bash
# Refresh every minute (testing only)
OAUTH2_PROXY_COOKIE_REFRESH=1m

# Refresh every hour
OAUTH2_PROXY_COOKIE_REFRESH=1h

# Refresh daily (24 hours)
OAUTH2_PROXY_COOKIE_REFRESH=24h

# Refresh weekly (168 hours)
OAUTH2_PROXY_COOKIE_REFRESH=168h

# Refresh monthly (720 hours / 30 days)
OAUTH2_PROXY_COOKIE_REFRESH=720h

# No automatic refresh (default)
OAUTH2_PROXY_COOKIE_REFRESH=0
```

**Note**: Setting `OAUTH2_PROXY_COOKIE_REFRESH` to a non-zero value causes OAuth2 Proxy to automatically refresh the authentication token at the specified interval, requiring users to re-authenticate periodically for enhanced security.

<p align="right">(<a href="#configuration-top">back to top</a>)</p>

---

## OAuth2 provider setup

### Google (recommended)

1. Visit [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select a project
3. Navigate to **APIs & Services** → **Credentials**
4. Click **Create Credentials** → **OAuth client ID**
5. Select **Web application**
6. Add authorized redirect URI:
   ```
   https://your-hostname.your-tailnet.ts.net/oauth2/callback
   ```
7. Copy **Client ID** and **Client Secret** to `.env`

### GitHub (alternative)

1. Visit [GitHub Developer Settings](https://github.com/settings/developers)
2. Click **New OAuth App**
3. Set **Authorization callback URL**:
   ```
   https://your-hostname.your-tailnet.ts.net/oauth2/callback
   ```
4. Copy **Client ID** and **Client Secret**
5. Update `docker-compose.yml` OAuth2 Proxy arguments:
   ```yaml
   - --provider=github
   - --client-id=${OAUTH2_PROXY_CLIENT_ID}
   - --client-secret=${OAUTH2_PROXY_CLIENT_SECRET}
   ```

### Azure AD / Entra ID

1. Register application in [Azure Portal](https://portal.azure.com/)
2. Add redirect URI: `https://your-hostname.ts.net/oauth2/callback`
3. Create client secret
4. Update `docker-compose.yml`:
   ```yaml
   - --provider=azure
   - --client-id=${OAUTH2_PROXY_CLIENT_ID}
   - --client-secret=${OAUTH2_PROXY_CLIENT_SECRET}
   - --azure-tenant=${AZURE_TENANT_ID}
   ```

<p align="right">(<a href="#configuration-top">back to top</a>)</p>

---

## Tailscale Funnel setup

### Prerequisites

1. **Install Tailscale**:
   - Linux: `curl -fsSL https://tailscale.com/install.sh | sh`
   - Windows: Download from [tailscale.com/download](https://tailscale.com/download)
   - macOS: `brew install tailscale`

2. **Authenticate**:
   ```bash
   tailscale up
   ```

3. **Verify connection**:
   ```bash
   tailscale status
   ```

### Enable Funnel

Funnel exposes your service to the public internet with a valid HTTPS certificate:

```bash
# Start Funnel on port 4180 (OAuth2 Proxy)
tailscale funnel --bg 4180

# Verify Funnel status
tailscale funnel status
```

### Disable Funnel

Stop public access immediately:

```bash
tailscale funnel off
```

### Funnel requirements

- Tailscale account with Funnel enabled (free tier supported)
- Node must be connected to your tailnet
- Port must be available (4180 for OAuth2 Proxy)
- Funnel provides automatic HTTPS with valid certificate

<p align="right">(<a href="#configuration-top">back to top</a>)</p>

---

## File locations

### Docker deployment (default)

| File | Container Path | Host Path (volume) |
| --- | --- | --- |
| Routes DB | `/app/routes.json` | `./app/routes.json` |
| Email list | `/app/emails.txt` | `./app/emails.txt` |
| Environment | N/A | `./.env` |
| Caddy config | `/etc/caddy/` | `./caddy/` |

### Native Python deployment

| File | Default Path |
| --- | --- |
| Routes DB | `app/routes.json` |
| Email list | `app/emails.txt` |
| Environment | `.env` (loaded by python-dotenv) |

**Override via environment variables**:
```bash
export ROUTES_DB_PATH=/path/to/routes.json
export EMAILS_FILE=/path/to/emails.txt
python app/dev.py
```

<p align="right">(<a href="#configuration-top">back to top</a>)</p>

---

## Advanced configuration

### Custom Caddy configuration

Edit `caddy/base.json` to modify the base Caddy configuration. Changes require restart:

```bash
docker compose restart caddy
```

**Common customizations**:
- Custom logging format
- Rate limiting
- Custom headers
- TLS client authentication

### Email allow list format

`emails.txt` supports:
- One email per line
- Comments (lines starting with `#`)
- Blank lines (ignored)

**Example**:
```
# Production administrators
admin@company.com
ops@company.com

# Development team
dev1@company.com
dev2@company.com
```

Changes take effect immediately (no restart required).

### Per-route options

Configure via the web UI or REST API:

| Option | Type | Description |
| --- | --- | --- |
| `path` | string | URL path prefix (e.g., `/jellyfin`) |
| `target_ip` | string | Backend IP address |
| `target_port` | integer | Backend port |
| `protocol` | string | `http` or `https` |
| `enabled` | boolean | Route active/inactive |
| `preserve_host` | boolean | Forward original `Host` header |
| `no_upstream_compression` | boolean | Send `Accept-Encoding: identity` |
| `force_content_encoding` | string | Override `Content-Encoding` (`gzip`, `br`, or null) |
| `sni` | string | Custom SNI hostname for HTTPS backends |
| `insecure_skip_verify` | boolean | Skip TLS certificate verification |

**Example route**:
```json
{
  "path": "/jellyfin",
  "target_ip": "192.168.1.100",
  "target_port": 8096,
  "protocol": "https",
  "enabled": true,
  "preserve_host": true,
  "sni": "jellyfin.local",
  "insecure_skip_verify": false
}
```

### Docker Compose profiles

The project supports development and production profiles:

```bash
# Production (default)
docker compose up -d

# Development (if defined)
docker compose --profile dev up -d
```

<p align="right">(<a href="#configuration-top">back to top</a>)</p>

---

<div align="center">

[![Back to README](https://img.shields.io/badge/←_Back_to-README-blue?style=for-the-badge)](../README.md)

**Made with <3 for secure self-hosting**

</div>

<p align="right">(<a href="#configuration-top">back to top</a>)</p>
