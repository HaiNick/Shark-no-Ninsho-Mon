# Shark-no-Ninsho-Mon

**Secure Public Web Apps with Google OAuth via Tailscale Funnel**

A minimal, production-ready setup for exposing web applications to the internet with Google authentication, using Tailscale Funnel and oauth2-proxy. Perfect for self-hosted apps that need public access with authentication.

---

## Quick Start

```bash
# 1. Clone and setup
git clone <your-repo>
cd Shark-no-Ninsho-Mon

# 2. Configure environment
cp .env.template .env
# Edit .env with your values

# 3. Setup allowed users
# Edit emails.txt with allowed Google accounts

# 4. Deploy
docker compose up -d --build
tailscale funnel 4180

# 5. Access your app
# https://your-host.your-tailnet.ts.net
```

---

## Prerequisites

Ensure you have these installed and configured:

- [x] **Tailscale** - installed, logged in, with Funnel enabled
- [x] **Docker & Docker Compose** - for containerized deployment  
- [x] **Google Account** - for OAuth authentication

**Verification Commands:**
```bash
tailscale status
docker --version
docker compose version
```

---

## Architecture

```
Internet Users
      |
[Tailscale Funnel] <- https://your-host.your-tailnet.ts.net
      |
[oauth2-proxy:4180] <- Google OAuth Authentication
      |
[Flask App:8000] <- Your Application (internal only)
```

**Security Model:**
- [LOCKED] All traffic goes through Google OAuth
- [GLOBE] Only oauth2-proxy is exposed publicly (via Funnel)
- [KEY] Flask app is internal-only (no direct internet access)
- [MAIL] User access controlled by email whitelist

---

## Configuration

### 1. Google OAuth Setup

1. **Google Cloud Console** -> Create/Select Project
2. **OAuth Consent Screen:**
   - User Type: `External`
   - Scopes: `openid`, `email`, `profile` only
   - For testing: Add your Gmail to Test Users
3. **Credentials** -> Create OAuth Client ID:
   - Type: `Web Application`
   - Redirect URI: `https://your-host.your-tailnet.ts.net/oauth2/callback`

**Save:** Client ID & Client Secret (never commit these!)

### 2. Environment Configuration

Copy the template and fill in your values:

```bash
cp .env.template .env
```

Required variables in `.env`:
```bash
OAUTH2_PROXY_CLIENT_ID=your-google-client-id
OAUTH2_PROXY_CLIENT_SECRET=your-google-client-secret
OAUTH2_PROXY_COOKIE_SECRET=32-byte-base64-secret
FUNNEL_HOST=https://your-host.your-tailnet.ts.net
FUNNEL_HOSTNAME=your-host.your-tailnet.ts.net
```

**Generate Cookie Secret:**
```bash
# Linux/Mac
head -c 32 /dev/urandom | base64

# Windows PowerShell
./setup.ps1  # Generates automatically
```

### 3. User Access Control

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
```bash
# Stop containers (keep data)
docker compose stop

# Stop and remove containers
docker compose down

# Full cleanup (removes volumes & images)
docker compose down --volumes --rmi local
```

---

## Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| `redirect_uri_mismatch` | Ensure Google Console redirect URI exactly matches `FUNNEL_HOST/oauth2/callback` |
| Headers missing in app | Verify `OAUTH2_PROXY_PASS_USER_HEADERS=true` and `OAUTH2_PROXY_SET_XAUTHREQUEST=true` |
| Bypass security risk | Never add `ports:` to app service - only `expose:` allowed |
| 7-day re-consent | Switch OAuth consent screen from Testing to Production |

### Debug Commands
```bash
# Check oauth2-proxy logs
docker compose logs -f oauth2-proxy

# Test authentication headers
curl -H "Cookie: $(curl -c - -b - -L https://your-host.your-tailnet.ts.net)" \
     https://your-host.your-tailnet.ts.net/headers

# Verify container networking
docker compose exec oauth2-proxy wget -qO- http://app:8000/headers
```

---

## Security Best Practices

### Essential Security
- [x] **Never commit `.env`** - contains secrets
- [x] **Use break-glass email** - add second admin email to `emails.txt`  
- [x] **Keep app internal** - only oauth2-proxy should be publicly accessible
- [x] **Regular updates** - update Docker images regularly

### Advanced Security
- [ROTATE] **Rotate secrets** - Google Client Secret if compromised
- [LOG] **Monitor logs** - review access patterns
- [MINIMAL] **Minimal scopes** - only `openid email profile`
- [AUDIT] **Audit access** - review `emails.txt` regularly

---

## Use Cases & Alternatives

### When to Use This Setup
- [x] **Personal projects** needing public access
- [x] **Small team tools** with Google accounts
- [x] **Proof of concepts** requiring auth
- [x] **Self-hosted apps** behind home networks

### Alternatives

| Scenario | Alternative |
|----------|------------|
| **Private only** | Skip Funnel, use `tailscale serve` with Tailscale identity |
| **Complex policies** | Use enterprise access broker (Cloudflare Access, etc.) |
| **Many users** | Consider dedicated identity provider (Auth0, etc.) |
| **High availability** | Use cloud load balancer + managed OAuth |

---

## Project Structure

```
shark-no-ninsho-mon/
├── README.md              # This documentation
├── docker-compose.yml     # Service definitions
├── emails.txt             # Allowed users
├── .env.template          # Configuration template
├── .gitignore            # Git ignore rules
├── setup.ps1             # Windows setup script
├── setup.sh              # Linux/Mac setup script
└── app/                   # Flask application
    ├── Dockerfile         # Python container
    ├── requirements.txt   # Python dependencies
    └── app.py             # Flask application code
```

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Test your changes
4. Submit a pull request

## License

See [LICENSE](LICENSE) file for details.

---

**WARNING:** This setup exposes your application to the internet. Always review security settings and keep authentication properly configured.