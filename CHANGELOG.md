# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] - 2026-03-03

### Security Enhancements

#### Network & Port Hardening
- **FIXED**: Removed Caddy Admin API public port mapping (`2019:2019`) from `docker-compose.yml`
- **FIXED**: Flask port no longer published to host; only accessible via internal Docker network
- **ADDED**: Docker network isolation — `internal: true` network for app/Caddy, `public` for oauth2-proxy
- **ADDED**: HMAC-based `OAUTH_PROXY_SHARED_SECRET` validation for proxy header authentication

#### CSRF Protection
- **ADDED**: Flask-WTF CSRF protection on all state-changing endpoints (POST/PUT/DELETE)
- **ADDED**: CSRF meta tag in `base.html` and `X-CSRFToken` header in all JS fetch calls
- **ADDED**: `/health` endpoint exempted from CSRF checks

#### SSRF Prevention
- **IMPROVED**: Expanded IP blocklist with link-local, reserved, and cloud metadata endpoint checks
- **ADDED**: `BLOCKED_IPS` set covering AWS, GCP, Azure, Alibaba Cloud, and OpenStack metadata IPs
- **ADDED**: `is_link_local` and `is_reserved` IP validation checks

#### Input Validation
- **ADDED**: `validate_target_path()` rejects `..`, `//`, and non-alphanumeric characters
- **IMPROVED**: Email validation with RFC 5321 length limits (254 total, 64 local part) and consecutive dot rejection
- **FIXED**: `target_path` default changed from `''` to `'/'`

#### Security Headers
- **ADDED**: Flask-Talisman for `Strict-Transport-Security`, `X-Content-Type-Options`, and `X-Frame-Options` headers
- **ADDED**: `force_https=False` since TLS termination is handled by Caddy/Tailscale

#### Setup Wizard Hardening
- **FIXED**: Setup wizard now binds to `127.0.0.1` (localhost only)
- **ADDED**: Single-use security token required for wizard access (printed once at startup)

#### DEV_MODE Safety
- **ADDED**: CRITICAL log banner when `DEV_MODE=true`
- **ADDED**: Warnings when DEV_MODE is active inside Docker or alongside OAuth credentials

#### Email Allowlist Security
- **ADDED**: File locking (`fcntl.flock()`) for atomic email allowlist read/write operations

### Reliability Improvements

#### Storage Migration
- **CHANGED**: Routes storage migrated from TinyDB to SQLite with WAL mode
- **ADDED**: Indexes on `path` and `enabled` columns for faster queries
- **REMOVED**: TinyDB dependency from `requirements.txt`

#### Health Check Worker
- **IMPROVED**: Health checks use `ThreadPoolExecutor(max_workers=5)` with 10s per-check timeout
- **ADDED**: Exponential backoff for failing routes (max 30 min between retries)

#### Caddy Sync
- **ADDED**: `threading.Lock()` with 30s timeout around `sync()` to prevent race conditions
- **ADDED**: 1-second debounce between consecutive syncs

#### Rate Limiting
- **CHANGED**: Route test endpoint rate limit reduced from 30/hr to 10/hr
- **ADDED**: Per-route 30-second cooldown with `retry_after` in 429 response

#### TLS Verification
- **FIXED**: `classify_service_status()` defaults to `verify=True` (was `verify=False`)
- **ADDED**: `SSLError` caught and returned as `DOWN/tls_error` state
- **ADDED**: Per-route `insecure_skip_verify` flag support

#### Secrets Handling
- **FIXED**: `generate-secrets.py` no longer prints secret values to stdout

#### Docker Health Check
- **CHANGED**: Container health check uses `urllib.request` instead of `requests` library

### Code Quality

#### New Files
- **ADDED**: `app/constants.py` with `Limits`, `RateLimits`, `Defaults` classes
- **ADDED**: `app/errors.py` with `AppError`, `ValidationError`, `AuthorizationError`, `NotFoundError`
- **ADDED**: `app/requirements.lock` with pinned dependency versions

#### Middleware
- **ADDED**: `X-Request-ID` middleware for request correlation across logs

#### Type Safety
- **ADDED**: Type hints on public functions in `app.py`, `routes_db.py`, `caddy_manager.py`

#### CI/CD
- **ADDED**: `.github/workflows/security.yml` with Bandit scan and test runner on push/PR to main

### Dependencies

#### Added
- `flask-wtf>=1.2.1` — CSRF protection
- `flask-talisman>=1.1.0` — Security headers

#### Removed
- `tinydb>=4.8.0` — Replaced by SQLite (stdlib)

### Migration Notes

- **Breaking**: Routes storage changed from TinyDB (`routes.json`) to SQLite (`routes.db`). Manual migration required for existing deployments.
- **Breaking**: Setup wizard now requires `?token=<value>` query parameter (token printed at startup).
- **Config**: New optional env var `OAUTH_PROXY_SHARED_SECRET` for proxy header validation (see `.env.template`).
- Flask port `8000` is no longer exposed to host — access via oauth2-proxy/Caddy only.

---

## [2.0.0] - 2025-09-30

### Security Enhancements

#### Critical Fixes
- **FIXED**: Removed anonymous user bypass in production mode
  - Anonymous users are now properly blocked when `FLASK_ENV=production`
  - Development mode still allows anonymous for testing purposes
  - Added environment variable checks for security-critical code paths

#### Rate Limiting
- **ADDED**: Flask-Limiter for DDoS protection
  - Global limits: 200 requests/day, 50 requests/hour per IP
  - Logs endpoint: 10 requests/minute (prevents log flooding)
  - Health endpoint: Exempt from rate limiting (for monitoring)

#### Container Security
- **ADDED**: Non-root user in Docker container
  - Application runs as `appuser` (UID 1000)
  - Proper file permissions and ownership
  - Reduced attack surface

### Performance Improvements

#### Email Authorization Caching
- **ADDED**: Smart caching for authorized emails
  - Emails cached with file modification time tracking
  - Automatic cache invalidation on file changes
  - Reduces I/O operations from O(n) per request to O(1)
  - ~95% reduction in disk reads

#### Optimized Logging
- **IMPROVED**: Conditional debug logging
  - IP detection logs only in development mode
  - Reduced log noise in production
  - Better log level management

### Reliability & Monitoring

#### Health Checks
- **ADDED**: Comprehensive Docker health checks
  - Application health endpoint with status validation
  - Email file accessibility check
  - Log file writability verification
  - Returns HTTP 503 on degraded status
  - OAuth2-Proxy ping endpoint monitoring

#### Dependency Ordering
- **IMPROVED**: Service startup dependencies
  - OAuth2-Proxy waits for app health check
  - `condition: service_healthy` in docker-compose
  - Prevents race conditions on startup

### Code Quality

#### Error Handling
- **IMPROVED**: File permission error handling
  - Graceful fallback when log file is not writable
  - Proper HTTP status codes (403, 404, 503)
  - User-friendly error messages

#### Environment Configuration
- **ADDED**: Environment variable support
  - `FLASK_ENV` for environment detection
  - `EMAILS_FILE_PATH` for flexible email file location
  - `LOG_FILE_PATH` for configurable log location

#### Path Resolution
- **FIXED**: Robust file path handling
  - Multiple fallback paths for email file
  - Absolute path support via environment variables
  - Eliminates path resolution ambiguity

### Testing

#### Test Suite
- **ADDED**: Comprehensive unit tests
  - Authorization logic tests
  - Rate limiting validation
  - Health endpoint verification
  - Security header checks
  - API endpoint coverage
  - Run with: `python -m pytest test_app.py -v`

### Documentation

#### Security Documentation
- **ADDED**: SECURITY.md
  - Security policy and supported versions
  - Vulnerability reporting process
  - Security best practices guide
  - Deployment security checklist
  - Compliance considerations (GDPR)

#### Changelog
- **ADDED**: CHANGELOG.md (this file)
  - Detailed version history
  - Breaking changes documentation
  - Migration guides

### Configuration

#### Docker Compose
- **UPDATED**: Enhanced docker-compose.yml
  - Health check configurations
  - Environment variable propagation
  - Service dependency management
  - Start period and retry configuration

#### Requirements
- **ADDED**: Flask-Limiter==3.5.0
  - Rate limiting functionality
  - Memory-based storage (Redis optional)

#### Dockerfile
- **IMPROVED**: Production-ready Dockerfile
  - Non-root user execution
  - Proper working directory permissions
  - Gunicorn timeout configuration
  - Log directory creation

### Application Updates

#### Version Bump
- **UPDATED**: Application version to 2.0.0
  - Updated in health endpoint response
  - Reflects major security improvements

## [1.0.0] - 2024-XX-XX

### Initial Release

#### Features
- Google OAuth2 authentication integration
- Email-based authorization allowlist
- Tailscale Funnel for public access
- Docker Compose deployment
- Interactive setup scripts (Bash & PowerShell)
- Flask web application with multiple endpoints
- Access logging and monitoring
- Beautiful Dracula-themed terminal UI
- Cross-platform support (Linux, macOS, Windows)

#### Endpoints
- `/` - Main application page
- `/api/whoami` - User information API
- `/headers` - Authentication headers display
- `/logs` - Access logs viewer
- `/health` - Health check endpoint
- `/unauthorized` - Unauthorized access page

#### Security
- OAuth2-Proxy integration
- HTTPS via Tailscale Funnel
- Secure cookie handling
- Email allowlist authorization
- Incident tracking for security events

## Migration Guide

### Upgrading from 1.0.x to 2.0.0

#### Breaking Changes
None - fully backward compatible

#### Recommended Actions

1. **Update Dependencies**
   ```bash
   cd app/
   pip install -r requirements.txt --upgrade
   ```

2. **Set Environment Variables** (Optional but recommended)
   ```bash
   # Add to .env or docker-compose.yml
   FLASK_ENV=production
   EMAILS_FILE_PATH=/app/emails.txt
   LOG_FILE_PATH=/app/access.log
   ```

3. **Rebuild Containers**
   ```bash
   docker compose down
   docker compose up -d --build
   ```

4. **Verify Health Checks**
   ```bash
   docker compose ps
   # Both services should show "healthy" status
   ```

5. **Test Rate Limiting**
   ```bash
   # Should get 429 after 10 requests
   for i in {1..12}; do curl https://your-host.ts.net/logs; done
   ```

6. **Review Security Policy**
   - Read SECURITY.md for deployment best practices
   - Update secrets if using defaults
   - Configure monitoring/alerting

#### New Features to Leverage

1. **Rate Limiting**: Protects against abuse automatically
2. **Health Checks**: Better orchestration and monitoring
3. **Email Caching**: Improved performance
4. **Security Hardening**: Production-ready security

## Development

### Running Tests

```bash
cd app/
pip install pytest
python -m pytest test_app.py -v
```

### Local Development

```bash
# Install dependencies
pip install -r app/requirements.txt

# Run in development mode
export FLASK_ENV=development
export EMAILS_FILE_PATH=./emails.txt
python app/app.py
```

## Contributors

- [@HaiNick](https://github.com/HaiNick) - Original author and maintainer

## Links

- [GitHub Repository](https://github.com/HaiNick/Shark-no-Ninsho-Mon)
- [Issue Tracker](https://github.com/HaiNick/Shark-no-Ninsho-Mon/issues)
- [Security Policy](SECURITY.md)
- [License](LICENSE)

---

[3.0.0]: https://github.com/HaiNick/Shark-no-Ninsho-Mon/releases/tag/v3.0.0
[2.0.0]: https://github.com/HaiNick/Shark-no-Ninsho-Mon/releases/tag/v2.0.0
[1.0.0]: https://github.com/HaiNick/Shark-no-Ninsho-Mon/releases/tag/v1.0.0
