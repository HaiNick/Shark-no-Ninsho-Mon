# Security Policy

## Supported Versions

We release patches for security vulnerabilities in the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 3.0.x   | :white_check_mark: |
| 2.0.x   | :x:                |
| 1.0.x   | :x:                |

**Note**: We use Dependabot for automated dependency updates. Security patches are applied weekly for Python dependencies and Docker images.

## Security Features

### Built-in Security Measures

1. **OAuth2 Authentication**
   - Google OAuth2 integration for user authentication
   - Email-based allowlist for authorization
   - Secure cookie handling with proper secrets
   - HMAC-based proxy header validation (`OAUTH_PROXY_SHARED_SECRET`)

2. **CSRF Protection**
   - Flask-WTF CSRF tokens on all state-changing endpoints
   - Meta tag injection and JS header integration
   - Health endpoint exempted for monitoring tools

3. **Rate Limiting**
   - Default: 200 requests per day, 50 per hour per IP
   - Route test endpoint: 10 per hour with 30s per-route cooldown
   - Logs endpoint: 30 requests per minute
   - Prevents brute force and DDoS attacks

4. **Environment Separation**
   - Production mode blocks anonymous users
   - DEV_MODE logs CRITICAL banner and warns in Docker/OAuth contexts
   - Environment-specific configurations

5. **Input Validation**
   - Email normalization with RFC 5321 length checks (254 total, 64 local part)
   - Target path validation (rejects `..`, `//`, invalid characters)
   - IP validation with SSRF blocklist (AWS, GCP, Azure, Alibaba, OpenStack metadata)
   - Header sanitization and path traversal prevention

6. **Security Headers**
   - Flask-Talisman provides `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`
   - HTTPS enforcement via Tailscale Funnel at edge
   - Secure cookie flags (Secure, SameSite=Lax)
   - No secrets in repository (`.env` in `.gitignore`)

7. **Network Isolation**
   - Docker networks split into `public` and `internal` (with `internal: true`)
   - Flask app and Caddy on internal network only
   - Caddy Admin API not exposed to host
   - Non-root user in Docker container
   - Read-only volumes for sensitive files

8. **File Locking & Concurrency**
   - Email allowlist operations use `fcntl.flock()` for atomicity
   - Caddy sync guarded by `threading.Lock()` with debounce
   - Routes stored in SQLite with WAL mode for concurrent access

9. **Logging & Monitoring**
   - Comprehensive access logging with `X-Request-ID` correlation
   - Unauthorized access attempt tracking
   - Incident ID generation for security events

10. **Automated Dependency Management**
    - Dependabot configured for weekly security updates
    - Python (pip), Docker, and Docker Compose dependencies monitored
    - Automated pull requests for vulnerability patches
    - `requirements.lock` with pinned dependency versions

11. **CI Security Scanning**
    - Bandit static analysis on push and pull requests
    - Automated test suite in GitHub Actions

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please follow these steps:

### 1. **DO NOT** create a public GitHub issue

Security vulnerabilities should be reported privately to avoid exploitation.

### 2. Contact Us

- **Primary**: Create a private security advisory on GitHub (preferred)
  - Go to the Security tab → Report a vulnerability
- **Email**: [Create an issue with "SECURITY" label for non-sensitive reports]
- **Subject**: "SECURITY: [Brief description]"
- **Include**:
  - Description of the vulnerability
  - Steps to reproduce
  - Potential impact
  - Suggested fix (if any)
  - Affected versions

### 3. Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Fix Timeline**: Depends on severity
  - Critical: 24-48 hours
  - High: 7 days
  - Medium: 30 days
  - Low: 90 days

### 4. Disclosure Policy

- We follow coordinated disclosure
- Security advisories published after fix is available
- Credit given to reporters (unless they prefer anonymity)

## Security Best Practices for Deployment

### Environment Configuration

```bash
# Always use production mode
FLASK_ENV=production

# Use strong, unique secrets
OAUTH2_PROXY_COOKIE_SECRET=$(openssl rand 32 | base64 | tr -d '\n' | tr '+/' '-_')

# Restrict authorized users
# Only add trusted email addresses to emails.txt
```

### Network Security

1. **Use Tailscale Funnel**
   - Provides automatic HTTPS
   - No port forwarding needed
   - Built-in DDoS protection

2. **Firewall Configuration**
   - Only expose port 4180 to Tailscale
   - Block direct access to port 8000
   - Use `127.0.0.1` binding for OAuth2-Proxy

### File Permissions

```bash
# Restrict .env file permissions
chmod 600 .env

# Make emails.txt readable only by app
chmod 644 emails.txt

# Secure log files
chmod 640 /app/access.log
```

### Regular Updates

1. **Automated Dependency Updates**
   ```bash
   # Dependabot runs weekly and creates PRs automatically
   # Review and merge Dependabot PRs promptly
   
   # Manual check (if needed)
   pip list --outdated
   docker compose pull
   ```

2. **Monitor Security Advisories**
   - GitHub Security Advisories (enabled for this repo)
   - Dependabot alerts for vulnerable dependencies
   - Subscribe to Flask security announcements
   - Check OAuth2-Proxy and Caddy security notices

3. **Docker Image Updates**
   - Dependabot monitors base images in Dockerfile
   - Service images in docker-compose.yml tracked automatically
   - Review and test updates before merging

### Monitoring

1. **Check Logs Regularly**
   ```bash
   # Review unauthorized access attempts
   docker compose logs app | grep "SECURITY BLOCK"
   
   # Monitor for suspicious patterns
   docker compose logs app | grep "AUTHORIZATION FAILED"
   ```

2. **Set Up Alerts** (Optional)
   - Configure log forwarding to SIEM
   - Set up Prometheus/Grafana monitoring
   - Enable email alerts for security events

## Security Checklist

Before deploying to production:

- [ ] Changed all default secrets
- [ ] Configured `OAUTH_PROXY_SHARED_SECRET` for proxy validation (see `.env.template`)
- [ ] Configured authorized emails properly
- [ ] Set `FLASK_ENV=production`
- [ ] Ensure `DEV_MODE` is **not** set to `true`
- [ ] Enabled HTTPS via Tailscale Funnel
- [ ] Restricted file permissions
- [ ] Tested authentication flow
- [ ] Reviewed access logs
- [ ] Configured backup strategy
- [ ] Documented incident response plan
- [ ] Set up monitoring/alerting
- [ ] Enabled Dependabot security alerts
- [ ] Reviewed and configured `.github/dependabot.yml`
- [ ] Verified Caddy Admin API (port 2019) is not exposed publicly
- [ ] Verified Flask port (8000) is not exposed publicly

## Known Security Considerations

### Rate Limiting

The built-in rate limiting uses in-memory storage. For multi-instance deployments, consider using Redis:

```yaml
# docker-compose.yml
services:
  redis:
    image: redis:alpine
    
  app:
    environment:
      - RATELIMIT_STORAGE_URL=redis://redis:6379
```

### Session Management

OAuth2-Proxy sessions are stored in cookies. For long-lived sessions:

```yaml
environment:
  OAUTH2_PROXY_COOKIE_EXPIRE: "24h"
  OAUTH2_PROXY_COOKIE_REFRESH: "1h"
```

### Email Allowlist

The `emails.txt` file is checked on every request (with caching). For large allowlists (>1000 emails), consider:
- Using a database
- Implementing group-based authorization
- Optimizing cache strategy

## Compliance

### GDPR Considerations

- User emails are logged for security purposes
- Logs contain IP addresses and user agents
- Configure log retention policies appropriately
- Provide data deletion mechanisms if required

### Audit Trail

All authentication attempts are logged with:
- Timestamp
- User email
- IP address
- Request path
- Success/failure status

## Security Updates

### Automated Updates

This repository uses **Dependabot** for automated security updates:

- **Python dependencies**: Checked weekly (Mondays at 10:00 Europe/Berlin)
- **Docker images**: Checked weekly for both Dockerfile and docker-compose.yml
- **GitHub Actions**: Ready to enable when needed

Dependabot will automatically:
1. Detect vulnerable dependencies
2. Create pull requests with updates
3. Group related updates to reduce PR noise
4. Provide changelog and release notes

### Manual Monitoring

1. Watch this repository for releases
2. Enable GitHub security alerts (Repository Settings → Security & analysis)
3. Review Dependabot PRs promptly
4. Follow [@HaiNick](https://github.com/HaiNick) for announcements

## Credits

We thank the following for responsible disclosure:

- (List will be updated as vulnerabilities are reported and fixed)

---

**Last Updated**: 2026-03-03  
**Version**: 3.0.0
