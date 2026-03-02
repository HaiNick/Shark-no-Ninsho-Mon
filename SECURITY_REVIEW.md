# Security & Code Quality Review - Shark-no-Ninsho-Mon

**Review Date:** 2026-03-02
**Reviewer:** Claude Code
**Scope:** Complete codebase analysis (app/, caddy/, setup_templates/, docker-compose.yml, .env.template, setup-wizard.py, generate-secrets.py)

---

## Executive Summary

### Biggest Risks & Opportunities

**CRITICAL SECURITY CONCERNS:**
1. **Caddy Admin API Exposed** (HIGH) - Port 2019 exposed in docker-compose.yml allows unauthenticated config modification
2. **Setup Wizard Unauthenticated** (HIGH) - Runs on 0.0.0.0:8080 without any authentication
3. **OAuth2 Header Trust Without Verification** (HIGH) - Flask trusts X-Forwarded-Email headers without validating source
4. **Email Allowlist Race Conditions** (HIGH) - File-based email management prone to concurrent write issues
5. **DEV_MODE Bypass** (HIGH) - Development mode bypasses all auth checks, easy to accidentally enable in production

**KEY OPPORTUNITIES:**
1. Add network isolation in Docker Compose to prevent Caddy Admin API exposure
2. Implement mTLS or network restrictions for inter-service communication
3. Add CSRF protection to state-changing API endpoints
4. Implement proper secret rotation mechanisms
5. Add input validation on all user-supplied data paths

---

## Detailed Findings by Priority

## HIGH PRIORITY (Security Vulnerabilities)

### H1: Caddy Admin API Publicly Exposed
**File:** `docker-compose.yml:96`
**Issue:** Caddy Admin API port 2019 is exposed publicly (`- "2019:2019"`), allowing unauthenticated configuration changes.

**Risk:** An attacker on the same network can:
- Modify routing rules to redirect traffic
- Inject malicious upstreams
- Disable security controls
- Exfiltrate data through proxy manipulation

**Fix:**
```yaml
# Remove public exposure - only allow internal Docker network access
# ports:
#   - "2019:2019"   # REMOVE THIS LINE
```

With the host port mapping removed, the Admin API remains reachable from other
containers on the internal Docker network at `http://caddy:2019`. **Do not**
bind the Admin API to `127.0.0.1:2019` *inside* the Caddy container in this
multi-container setup, because that would prevent the Flask app container from
reaching `http://caddy:2019`.

**Hardening options:**

1. **Rely on Docker network isolation (recommended default):**

   Keep the Admin API listening on the container’s network interface
   (for example, `":2019"`) so the Flask app can continue to use
   `http://caddy:2019`, but rely on the absence of a host port mapping and
   Docker’s internal network to prevent external access.

2. **Use a Unix socket for the Admin API (requires app changes):**

   ```json
   "admin": { "listen": "unix//var/run/caddy/admin.sock" }
---

### H2: Setup Wizard Runs Unauthenticated on Network
**File:** `setup-wizard.py:833`
**Issue:** Setup wizard binds to `0.0.0.0:8080` without any authentication, exposing sensitive configuration capabilities to the local network.

**Risk:** An attacker on the local network can:
- Read existing `.env` configuration (including secrets)
- Generate new secrets and overwrite configuration
- Modify authorized email lists
- Start/stop Docker containers
- Execute arbitrary Docker commands

**Current Code:**
```python
app.run(host='0.0.0.0', port=8080, debug=False)  # Line 833
```

**Fix Options:**
1. **Bind to localhost only** (recommended for initial setup):
```python
app.run(host='127.0.0.1', port=8080, debug=False)
```

2. **Add basic authentication** (if network access needed):
```python
from functools import wraps
from flask import request, Response

def check_auth(username, password):
    return username == 'admin' and password == os.environ.get('SETUP_PASSWORD')

def authenticate():
    return Response('Unauthorized', 401, {'WWW-Authenticate': 'Basic realm="Setup"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# Apply to all routes except status endpoint
```

3. **Generate single-use setup token** (best practice):
```python
import secrets
SETUP_TOKEN = secrets.token_urlsafe(32)
print(f"Setup token: {SETUP_TOKEN}")

@app.before_request
def check_token():
    if request.endpoint != 'static':
        token = request.headers.get('X-Setup-Token')
        if token != SETUP_TOKEN:
            return jsonify({'error': 'Invalid setup token'}), 403
```

---

### H3: OAuth2 Header Trust Without Validation
**File:** `app/app.py:144-158`
**Issue:** Flask application trusts `X-Forwarded-Email` and related headers without verifying they came from oauth2-proxy.

**Risk:** If an attacker can bypass oauth2-proxy or send requests directly to Flask (port 8000):
- Complete authentication bypass
- Arbitrary user impersonation
- Unauthorized access to all routes

**Current Code:**
```python
def get_user_email():
    """Get user email from OAuth2 proxy headers"""
    email = (
        request.headers.get('X-Forwarded-Email') or
        request.headers.get('X-Auth-Request-Email') or
        request.headers.get('X-Forwarded-User') or
        ''
    ).lower().strip()
    # ... no validation of header source
```

**Attack Vector:**
```bash
# Direct request to Flask container
curl -H "X-Forwarded-Email: admin@example.com" http://flask:8000/api/routes
```

**Fix:** Implement shared secret or request signature validation:

**Option 1: Shared Secret Header**
```python
OAUTH_PROXY_SECRET = os.environ.get('OAUTH_PROXY_SHARED_SECRET')

def validate_oauth_proxy_request():
    """Verify request came from oauth2-proxy"""
    if os.environ.get('DEV_MODE') == 'true':
        return True

    proxy_sig = request.headers.get('X-Auth-Request-Signature')
    if not proxy_sig or not OAUTH_PROXY_SECRET:
        return False

    # Verify signature
    import hmac
    import hashlib
    expected = hmac.new(
        OAUTH_PROXY_SECRET.encode(),
        request.path.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(proxy_sig, expected)

def get_user_email():
    if not validate_oauth_proxy_request():
        return None
    # ... rest of function
```

**Option 2: Network Isolation (Recommended)**
```yaml
# docker-compose.yml
services:
  app:
    # Remove public port exposure
    # ports:
    #   - "8000:8000"  # REMOVE THIS
    networks:
      - internal

networks:
  internal:
    internal: true  # No external access
  default:
```

---

### H4: DEV_MODE Authentication Bypass
**File:** `app/app.py:155-156, 164-165`
**Issue:** DEV_MODE environment variable bypasses all authentication checks, easy to accidentally leave enabled.

**Risk:**
- Accidental production deployment with DEV_MODE=true
- Complete authentication bypass
- No audit trail for unauthorized access

**Current Code:**
```python
if not email and (os.environ.get('FLASK_ENV') == 'development' or os.environ.get('DEV_MODE') == 'true'):
    return 'dev@localhost'

if os.environ.get('FLASK_ENV') == 'development' or os.environ.get('DEV_MODE') == 'true':
    return True
```

**Fix:** Add safety checks and logging:

```python
import warnings

DEV_MODE = os.environ.get('DEV_MODE', '').lower() == 'true'
FLASK_ENV = os.environ.get('FLASK_ENV', '')

# Startup validation
if DEV_MODE:
    warnings.warn(
        "⚠️  DEV_MODE is ENABLED - Authentication is DISABLED! "
        "NEVER use in production!",
        RuntimeWarning,
        stacklevel=2
    )
    logger.critical("=" * 80)
    logger.critical("DEV_MODE ENABLED - ALL AUTHENTICATION BYPASSED")
    logger.critical("This mode should ONLY be used for local development")
    logger.critical("=" * 80)

def is_dev_mode():
    """Centralized dev mode check with logging"""
    if DEV_MODE or FLASK_ENV == 'development':
        logger.warning("DEV_MODE: Authentication bypass used")
        return True
    return False

def is_authorized():
    if is_dev_mode():
        return True
    # ... rest of function
```

**Additional Protection:**
```python
# Refuse to start in dev mode if certain production indicators present
if DEV_MODE:
    if os.path.exists('/.dockerenv'):  # Running in Docker
        logger.error("DEV_MODE enabled in Docker - this is likely a mistake!")
    if os.environ.get('OAUTH2_PROXY_CLIENT_ID'):  # OAuth configured
        logger.error("DEV_MODE enabled with OAuth configured - this is unsafe!")
```

---

### H5: SSRF Potential in Dynamic Route Configuration
**File:** `app/routes_db.py:202-219`
**Issue:** IP validation only allows private IPs, but doesn't prevent SSRF to cloud metadata services.

**Risk:** While private IP restriction is good, the explicit block of `169.254.169.254` suggests awareness of cloud metadata risk, but:
- Other cloud providers use different IPs
- IPv6 link-local addresses not blocked
- DNS rebinding attacks possible

**Current Code:**
```python
def validate_ip(ip: str):
    """Validate IP address - only allow private IPs"""
    try:
        ip_obj = ipaddress.ip_address(ip)

        if ip_obj.is_loopback:
            raise ValueError("Localhost IPs are not allowed")

        if str(ip) == '169.254.169.254':  # AWS/GCP metadata
            raise ValueError("Cloud metadata IP is not allowed")

        if not ip_obj.is_private:
            raise ValueError("Only private IP addresses are allowed")
```

**Fix:** Add comprehensive cloud metadata blocking:

```python
def validate_ip(ip: str):
    """Validate IP address - only allow safe private IPs"""
    try:
        ip_obj = ipaddress.ip_address(ip)

        # Block loopback
        if ip_obj.is_loopback:
            raise ValueError("Localhost IPs are not allowed")

        # Block link-local (IPv4 and IPv6)
        if ip_obj.is_link_local:
            raise ValueError("Link-local IPs are not allowed")

        # Block cloud metadata endpoints (comprehensive list)
        BLOCKED_IPS = {
            '169.254.169.254',  # AWS/GCP/Azure metadata (IPv4)
            'fd00:ec2::254',    # AWS metadata (IPv6)
            '100.100.100.200',  # Alibaba Cloud
            '169.254.0.23',     # OpenStack
        }
        if str(ip_obj) in BLOCKED_IPS:
            raise ValueError("Cloud metadata IPs are not allowed")

        # Only allow RFC1918 private IPs
        if not ip_obj.is_private:
            raise ValueError("Only private IP addresses allowed (10.x, 192.168.x, 172.16-31.x)")

        # Additional check: block reserved ranges
        if ip_obj.is_reserved:
            raise ValueError("Reserved IP addresses are not allowed")

    except ValueError as e:
        raise ValueError(f"Invalid IP address: {e}")
```

---

### H6: No CSRF Protection on State-Changing Endpoints
**File:** `app/app.py` (all POST/PUT/DELETE endpoints)
**Issue:** No CSRF tokens on state-changing API endpoints. While behind OAuth2, still vulnerable to CSRF if user is authenticated.

**Risk:**
- Attacker can trick authenticated user into deleting routes
- Modifying email allowlist
- Toggling route states

**Fix:** Add Flask-WTF or implement custom CSRF protection:

```python
from flask_wtf.csrf import CSRFProtect, generate_csrf

csrf = CSRFProtect(app)

# Exempt health check
@app.route('/health')
@csrf.exempt
def health():
    # ...

# Add CSRF token to responses
@app.after_request
def set_csrf_token(response):
    if request.endpoint != 'health':
        csrf_token = generate_csrf()
        response.headers['X-CSRF-Token'] = csrf_token
    return response
```

Update JavaScript to include token:
```javascript
// In utils.js
async function apiRequest(url, options = {}) {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
    options.headers = options.headers || {};
    if (csrfToken) {
        options.headers['X-CSRF-Token'] = csrfToken;
    }
    // ... rest of request
}
```

---

### H7: Race Conditions in Email File Management
**File:** `app/app.py:584-651`
**Issue:** Email allowlist file operations are not atomic, leading to race conditions during concurrent modifications.

**Risk:**
- Concurrent adds/removes can corrupt file
- Lost updates when multiple admins modify simultaneously
- Inconsistent in-memory vs on-disk state

**Current Code:**
```python
# Read emails
with path_obj.open('r', encoding='utf-8') as f:
    for line in f:
        # ... process

# Write back without the removed email
with path_obj.open('w', encoding='utf-8') as f:
    for e in emails:
        f.write(f'{e}\n')
```

**Fix:** Use file locking:

```python
import fcntl
import contextlib

@contextlib.contextmanager
def locked_file(path, mode='r'):
    """Context manager for locked file operations"""
    with open(path, mode, encoding='utf-8') as f:
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            yield f
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

def add_email_to_file(email: str, path: Path):
    """Atomically add email to file"""
    with locked_file(path, 'a') as f:
        f.write(f'{email}\n')

def remove_email_from_file(email: str, path: Path):
    """Atomically remove email from file"""
    with locked_file(path, 'r+') as f:
        lines = f.readlines()
        f.seek(0)
        f.truncate()
        for line in lines:
            if line.strip().lower() != email.lower():
                f.write(line)
```

**Alternative:** Use database-backed storage instead of flat file:
```python
# Store in TinyDB instead
emails_db = TinyDB('emails.json')
emails_table = emails_db.table('emails')
```

---

## MEDIUM PRIORITY (Security & Reliability Issues)

### M1: TinyDB Not Suitable for Production at Scale
**File:** `app/routes_db.py:37`
**Issue:** TinyDB uses file-based JSON storage with basic locking, not suitable for high concurrency.

**Risk:**
- Performance degradation with many routes (>100)
- File corruption under heavy write load
- No ACID guarantees
- Limited query performance

**Current Code:**
```python
self._lock = threading.RLock()  # In-process lock only
self.db = TinyDB(str(path))
```

**Fix:** Migrate to SQLite for production:

```python
import sqlite3
import json
from contextlib import contextmanager

class RouteManager:
    def __init__(self, db_path='routes.db'):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS routes (
                    id TEXT PRIMARY KEY,
                    path TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    target_ip TEXT NOT NULL,
                    target_port INTEGER NOT NULL,
                    protocol TEXT NOT NULL,
                    enabled BOOLEAN NOT NULL DEFAULT 1,
                    config TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_path ON routes(path)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_enabled ON routes(enabled)')

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, isolation_level='IMMEDIATE')
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
```

---

### M2: Secrets in Environment Variables Logged
**File:** `setup-wizard.py:278-329`, `generate-secrets.py:100-104`
**Issue:** Generated secrets are printed to console and may be logged.

**Risk:**
- Secrets visible in terminal history
- Exposed in CI/CD logs
- Visible in process listings

**Current Code:**
```python
print("Generated Secrets:")
print("-" * 70)
print(f"OAUTH2_PROXY_COOKIE_SECRET={oauth_secret}")
print(f"SECRET_KEY={flask_secret}")
```

**Fix:** Don't print secrets, write directly to file:

```python
def generate_and_save_secrets():
    """Generate secrets and save directly to .env without printing"""
    oauth_secret = generate_oauth_cookie_secret()
    flask_secret = generate_flask_secret_key()

    # Don't print secrets
    logger.info("Generating secrets... (not displayed for security)")

    # Write directly to .env
    update_env_file(env_path, oauth_secret, flask_secret)

    logger.info("✓ Secrets generated and saved to .env")
    logger.info("⚠️  Keep .env file secure and never commit to git")
```

---

### M3: Rate Limit Too Permissive on Test Route Endpoint
**File:** `app/app.py:484-507`
**Issue:** Route testing endpoint is limited to 30 requests per hour, which is too high for an expensive health check and does not adequately prevent abuse.

**Risk:**
- Attacker can trigger expensive health checks
- Resource exhaustion on backend services
- DDoS amplification

**Current Code:**
```python
@app.route('/api/routes/<route_id>/test', methods=['POST'])
@limiter.limit("30 per hour")  # 30 is too high for expensive operations
def api_test_route(route_id):
```

**Fix:** Reduce rate limit and add per-route cooldown:

```python
from datetime import datetime, timedelta
from collections import defaultdict

# Track last test time per route
_last_test_times = defaultdict(lambda: datetime.min)
_test_cooldown = timedelta(seconds=30)  # 30 second cooldown per route

@app.route('/api/routes/<route_id>/test', methods=['POST'])
@limiter.limit("10 per hour")  # Reduce to 10/hour
def api_test_route(route_id):
    email = get_user_email()

    if not is_authorized():
        return jsonify({'error': 'Unauthorized'}), 403

    # Per-route cooldown
    last_test = _last_test_times[route_id]
    if datetime.now() - last_test < _test_cooldown:
        seconds_remaining = int((_test_cooldown - (datetime.now() - last_test)).total_seconds())
        return jsonify({
            'error': f'Please wait {seconds_remaining}s before testing this route again'
        }), 429

    _last_test_times[route_id] = datetime.now()

    # ... rest of function
```

---

### M4: Background Health Checks Can Overwhelm Backends
**File:** `app/app.py:861-890`
**Issue:** Health check worker tests all enabled routes sequentially without concurrency control or backoff.

**Risk:**
- Slow/failing backends can block all health checks
- No exponential backoff for persistently failing routes
- Resource exhaustion on backends

**Current Code:**
```python
def health_check_worker(stop_event: threading.Event, interval: int):
    while not stop_event.is_set():
        routes = route_manager.get_all_routes()
        for route in routes:
            if route.get('health_check', False) and route.get('enabled', True):
                result = caddy_mgr.test_connection(route)  # Blocks for each route
```

**Fix:** Add concurrency control and exponential backoff:

```python
import concurrent.futures
from datetime import datetime, timedelta

class HealthCheckManager:
    def __init__(self):
        self.failure_counts = defaultdict(int)
        self.last_check_times = {}

    def should_check_route(self, route_id: str) -> bool:
        """Implement exponential backoff for failing routes"""
        failure_count = self.failure_counts.get(route_id, 0)
        if failure_count == 0:
            return True

        # Exponential backoff: 1min, 2min, 4min, 8min, max 30min
        backoff_seconds = min(60 * (2 ** failure_count), 1800)
        last_check = self.last_check_times.get(route_id, datetime.min)

        return datetime.now() - last_check > timedelta(seconds=backoff_seconds)

    def record_result(self, route_id: str, success: bool):
        """Track success/failure for backoff"""
        self.last_check_times[route_id] = datetime.now()
        if success:
            self.failure_counts[route_id] = 0
        else:
            self.failure_counts[route_id] = self.failure_counts.get(route_id, 0) + 1

health_mgr = HealthCheckManager()

def health_check_worker(stop_event: threading.Event, interval: int):
    logger.info(f"HEALTH_CHECK - Worker started with {interval}s interval")

    while not stop_event.is_set():
        try:
            routes = route_manager.get_all_routes()
            routes_to_check = [
                r for r in routes
                if r.get('health_check') and r.get('enabled')
                and health_mgr.should_check_route(r['id'])
            ]

            if not routes_to_check:
                logger.debug("No routes need health checks this cycle")
            else:
                # Check routes concurrently with timeout
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    future_to_route = {
                        executor.submit(caddy_mgr.test_connection, route): route
                        for route in routes_to_check
                    }

                    for future in concurrent.futures.as_completed(
                        future_to_route, timeout=30
                    ):
                        route = future_to_route[future]
                        try:
                            result = future.result(timeout=10)
                            success = result.get('success', False)
                            health_mgr.record_result(route['id'], success)

                            route_manager.update_route_status(
                                route['id'],
                                status=result.get('status'),
                                state=result.get('state'),
                                reason=result.get('reason'),
                                http_status=result.get('status_code'),
                                duration_ms=result.get('response_time'),
                                last_error=result.get('error') or result.get('detail')
                            )
                        except Exception as e:
                            logger.error(f"Health check failed for {route['id']}: {e}")
                            health_mgr.record_result(route['id'], False)

                logger.info(f"HEALTH_CHECK - Checked {len(routes_to_check)} routes")

        except Exception as e:
            logger.error(f"HEALTH_CHECK_ERROR - {str(e)}")

        if stop_event.wait(interval):
            break
```

---

### M5: Caddy Sync Race Condition
**File:** `app/caddy_manager.py:56-87`
**Issue:** Multiple Flask workers can call `sync()` simultaneously, causing race condition in Caddy config updates.

**Risk:**
- Inconsistent routing configuration
- Lost route updates
- Service disruption during config conflicts

**Current Code:**
```python
def sync(self, routes: List[Dict[str, Any]]) -> dict:
    # No locking mechanism
    r = requests.patch(url, json=routes_array, headers=headers, timeout=10)
```

**Fix:** Add distributed locking:

```python
import threading
from contextlib import contextmanager
import time

_caddy_sync_lock = threading.Lock()
_last_sync_time = 0
_min_sync_interval = 1.0  # Minimum 1 second between syncs

@contextmanager
def caddy_sync_lock(timeout=30):
    """Prevent concurrent Caddy syncs"""
    if not _caddy_sync_lock.acquire(timeout=timeout):
        raise TimeoutError("Could not acquire Caddy sync lock")
    try:
        yield
    finally:
        _caddy_sync_lock.release()

def sync(self, routes: List[Dict[str, Any]]) -> dict:
    """Thread-safe Caddy config sync with debouncing"""
    global _last_sync_time

    # Debounce: prevent too-frequent syncs
    elapsed = time.time() - _last_sync_time
    if elapsed < _min_sync_interval:
        time.sleep(_min_sync_interval - elapsed)

    with caddy_sync_lock():
        try:
            cfg = self._build_config(routes)
            routes_array = cfg["apps"]["http"]["servers"]["srv0"]["routes"]
            url = f"{self.admin_url}/config/apps/http/servers/srv0/routes"

            log.info("CADDY_SYNC replacing %d routes", len(routes_array) - 1)

            r = requests.patch(url, json=routes_array, headers=headers, timeout=10)
            if not r.ok:
                # Fallback to DELETE+PUT
                log.warning("CADDY_SYNC PATCH failed, trying DELETE+PUT")
                requests.delete(url, timeout=10)
                r = requests.put(url, json=routes_array, headers=headers, timeout=10)

            r.raise_for_status()
            _last_sync_time = time.time()
            log.info("CADDY_SYNC completed successfully")
            return {"ok": True}

        except requests.exceptions.RequestException as e:
            log.error("CADDY_SYNC failed: %s", e)
            raise
```

---

### M6: Missing Input Validation on target_path
**File:** `app/routes_db.py:273`
**Issue:** `target_path` field is not validated, allowing potential path traversal or injection.

**Risk:**
- Path traversal attempts
- URL injection in upstream requests
- Unexpected backend behavior

**Current Code:**
```python
if 'target_path' in updates:
    sanitized['target_path'] = str(updates['target_path']).strip()  # No validation
```

**Fix:** Add path validation:

```python
@staticmethod
def validate_target_path(path: str) -> str:
    """Validate and sanitize target path"""
    if not isinstance(path, str):
        raise ValueError("Target path must be a string")

    path = path.strip()

    # Default to / if empty
    if not path:
        return '/'

    # Must start with /
    if not path.startswith('/'):
        path = '/' + path

    # Check for path traversal attempts
    if '..' in path or '//' in path:
        raise ValueError("Invalid target path: contains '..' or '//'")

    # Only allow safe characters
    if not re.match(r'^/[a-zA-Z0-9/_.-]*$', path):
        raise ValueError("Target path contains invalid characters")

    return path

# Use in _sanitize_updates
if 'target_path' in updates:
    sanitized['target_path'] = self.validate_target_path(updates['target_path'])
```

---

### M7: Insecure TLS Verification Disabled by Default
**File:** `app/caddy_manager.py:333`
**Issue:** Health checks use `verify=False`, disabling SSL certificate validation.

**Risk:**
- Man-in-the-middle attacks during health checks
- Cannot detect certificate issues
- False positive health status

**Current Code:**
```python
resp = requests.get(url, timeout=timeout_sec, allow_redirects=True, verify=False)
```

**Fix:** Make TLS verification configurable with secure default:

```python
def classify_service_status(
    self,
    url: str,
    timeout_sec: int = 3,
    slow_ms: int = 2000,
    verify_tls: bool = True  # Add parameter with secure default
) -> Tuple[str, str, Optional[str], Optional[int], Optional[int]]:
    # ... URL parsing ...

    # HTTP request with configurable TLS verification
    try:
        start = time.perf_counter()
        resp = requests.get(
            url,
            timeout=timeout_sec,
            allow_redirects=True,
            verify=verify_tls  # Use parameter
        )
        # ...
    except requests.exceptions.SSLError as e:
        return ("DOWN", "tls_error", f"TLS verification failed: {e}", None, None)

def test_connection(self, route: Dict[str, Any]) -> dict:
    # Get verify setting from route or config
    verify_tls = not bool(route.get('insecure_skip_verify', False))

    state, reason, detail, http_status, duration_ms = self.classify_service_status(
        target_url, timeout_sec, slow_ms, verify_tls=verify_tls
    )
```

---

### M8: Email Validation Regex Too Permissive
**File:** `app/app.py:85`
**Issue:** Email validation regex allows potentially dangerous patterns.

**Risk:**
- Bypass email validation with edge cases
- Potential injection if email used in commands

**Current Code:**
```python
pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
```

**Fix:** Use more strict validation:

```python
def is_valid_email(email: str) -> bool:
    """Validate email format using strict regex"""
    if not email or not isinstance(email, str):
        return False

    # More strict pattern
    # - Local part: alphanumeric, dots, hyphens, underscores (no consecutive dots)
    # - Domain part: alphanumeric and hyphens only
    # - TLD: 2-63 characters
    pattern = r'^[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}@[a-zA-Z0-9][a-zA-Z0-9-]{0,253}\.[a-zA-Z]{2,63}$'

    email = email.strip().lower()

    # Basic format check
    if not re.match(pattern, email):
        return False

    # Check for consecutive dots
    if '..' in email:
        return False

    # Check length constraints
    if len(email) > 254:  # RFC 5321
        return False

    local, domain = email.split('@')
    if len(local) > 64 or len(domain) > 253:
        return False

    return True
```

---

## LOW PRIORITY (Code Quality & Performance)

### L1: Missing Type Hints Throughout Codebase
**Files:** All Python files
**Issue:** Inconsistent or missing type hints reduce code maintainability.

**Fix:** Add comprehensive type hints:

```python
from typing import Dict, List, Optional, Any, Set, Tuple

def get_user_email() -> str:
    """Get user email from OAuth2 proxy headers"""
    # ...

def is_authorized() -> bool:
    """Check if user is authorized"""
    # ...

def api_get_routes() -> Tuple[Dict[str, Any], int]:
    """Get all routes"""
    # ...
```

Run mypy for type checking:
```bash
pip install mypy
mypy app/
```

---

### L2: Hardcoded Configuration Values
**Files:** Multiple
**Issue:** Magic numbers and strings scattered throughout code.

**Fix:** Extract to configuration class:

```python
# app/constants.py
class Limits:
    MAX_ROUTES = 100
    MAX_EMAIL_LENGTH = 254
    MAX_PATH_LENGTH = 255
    MAX_ROUTE_NAME_LENGTH = 100

class RateLimits:
    ROUTES_GET = "100 per hour"
    ROUTES_MODIFY = "50 per hour"
    ROUTE_TEST = "10 per hour"
    EMAIL_MODIFY = "20 per hour"
    LOGS_GET = "30 per minute"

class Defaults:
    HEALTH_CHECK_INTERVAL = 300
    HEALTH_CHECK_TIMEOUT = 30
    HTTP_TIMEOUT = 3
    SLOW_THRESHOLD_MS = 2000
    SESSION_LIFETIME = 604800  # 7 days
```

---

### L3: Inconsistent Error Handling
**Files:** Multiple
**Issue:** Mix of exception types, inconsistent error responses.

**Fix:** Standardize error handling:

```python
# app/errors.py
class AppError(Exception):
    """Base application error"""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class ValidationError(AppError):
    def __init__(self, message: str):
        super().__init__(message, 400)

class AuthorizationError(AppError):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, 403)

class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, 404)

# Use in routes
@app.errorhandler(AppError)
def handle_app_error(error):
    return jsonify({'error': error.message}), error.status_code
```

---

### L4: No Request ID Tracking
**Files:** All endpoints
**Issue:** Cannot trace requests through logs.

**Fix:** Add request ID middleware:

```python
import uuid

@app.before_request
def add_request_id():
    request.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
    g.request_id = request.request_id

@app.after_request
def add_request_id_header(response):
    response.headers['X-Request-ID'] = g.get('request_id', '')
    return response

# Update logging format
logging.basicConfig(
    format='%(asctime)s [%(request_id)s] %(name)s - %(levelname)s - %(message)s'
)
```

---

### L5: Inefficient Cache Implementation
**File:** `app/static/js/admin.js:39-46`
**Issue:** Client-side cache uses localStorage without expiration strategy.

**Fix:** Implement proper cache invalidation:

```javascript
// In utils.js
const CacheManager = {
    get(key, maxAge = 300000) {
        const item = localStorage.getItem(key);
        if (!item) return null;

        const { data, timestamp } = JSON.parse(item);
        const age = Date.now() - timestamp;

        if (age > maxAge) {
            localStorage.removeItem(key);
            return null;
        }

        return data;
    },

    set(key, data) {
        const item = {
            data,
            timestamp: Date.now()
        };
        localStorage.setItem(key, JSON.stringify(item));
    },

    invalidate(pattern) {
        // Invalidate keys matching pattern
        Object.keys(localStorage).forEach(key => {
            if (key.includes(pattern)) {
                localStorage.removeItem(key);
            }
        });
    }
};
```

---

### L6: Dead Code and Unused Variables
**File:** `app/routes_db.py:66`
**Issue:** `target_path` parameter has default value that's never used.

**Current:**
```python
def add_route(self, path: str, name: str, target_ip: str,
              target_port: int, protocol: str = 'http',
              enabled: bool = True, health_check: bool = True,
              timeout: int = 30, preserve_host: bool = False,
              websocket: bool = False, target_path: str = '') -> Dict:
```

**Fix:** Make default explicit:
```python
def add_route(
    self,
    path: str,
    name: str,
    target_ip: str,
    target_port: int,
    protocol: str = 'http',
    enabled: bool = True,
    health_check: bool = True,
    timeout: int = 30,
    preserve_host: bool = False,
    websocket: bool = False,
    target_path: str = '/'  # Changed from ''
) -> Dict:
    # ... later ...
    target_path = target_path or '/'  # Ensure non-empty
```

---

### L7: Setup Wizard Permission Fixing Fragile
**File:** `setup-wizard.py:27-95`
**Issue:** Permission fixing logic is complex and may fail on some systems.

**Fix:** Simplify and add better error handling:

```python
def fix_file_permissions(filepath, recursive=False):
    """
    Fix file/directory permissions when running as root/sudo.
    Simplified version with better error handling.
    """
    if IS_WINDOWS:
        return

    try:
        if os.geteuid() != 0:
            return

        # Get target UID/GID
        try:
            user_uid = int(os.environ.get('SUDO_UID', -1))
            user_gid = int(os.environ.get('SUDO_GID', -1))
        except ValueError:
            logger.warning("Could not parse SUDO_UID/SUDO_GID")
            return

        if user_uid == -1 or user_gid == -1:
            return

        path = Path(filepath)

        # Skip symlinks (security)
        if path.is_symlink():
            logger.debug(f"Skipping symlink: {filepath}")
            return

        # Change ownership
        os.chown(filepath, user_uid, user_gid, follow_symlinks=False)

        # Set permissions
        if path.is_dir():
            os.chmod(filepath, 0o755)
            if recursive:
                for child in path.iterdir():
                    fix_file_permissions(child, recursive=True)
        else:
            os.chmod(filepath, 0o644)

    except (OSError, PermissionError) as e:
        logger.warning(f"Could not fix permissions for {filepath}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error fixing permissions for {filepath}: {e}")
```

---

## DEPENDENCIES ANALYSIS

### Outdated or Risky Dependencies

**File:** `app/requirements.txt`

**Current Dependencies:**
```
Flask>=3.0.0          ✓ Recent (Jan 2024)
Werkzeug>=3.0.0       ✓ Recent
python-dotenv>=1.0.0  ✓ Recent
Flask-Limiter>=3.5.0  ✓ Recent
tinydb>=4.8.0         ⚠️  Not suitable for production (see M1)
validators>=0.22.0    ⚠️  Consider replacing with stricter validation
requests>=2.31.0      ✓ Recent
```

**Recommendations:**

1. **Add missing dependencies:**
```
Flask-WTF>=1.2.1        # CSRF protection
Flask-Talisman>=1.1.0   # Security headers
```

2. **Add testing dependencies:**
```
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-flask>=1.3.0
responses>=0.24.0       # Mock requests
```

3. **Add security scanning:**
```bash
pip install safety
safety check --json
```

4. **Add dependency pinning:**
```
# requirements.lock
Flask==3.0.3
Werkzeug==3.0.3
python-dotenv==1.0.1
Flask-Limiter==3.5.1
requests==2.31.0
```

---

## DOCKER COMPOSE SECURITY ISSUES

### D1: Container Runtime Users Not Explicitly Defined
**File:** `docker-compose.yml`
**Issue:** No `user:` directive is specified in Compose, so services rely on each image's default runtime user. The app image explicitly switches to a non-root user (`USER appuser`), but other services may still run as root if their images default to root. This should be confirmed and, where necessary, overridden.

**Fix:**
```yaml
services:
  app:
    # Optional: map container user to a specific host UID/GID if needed.
    # The app image already uses a non-root user (e.g., `appuser`).
    user: "${USER_ID:-1000}:${GROUP_ID:-1000}"
    # ...

  caddy:
    # Ensure Caddy does not run as root in the container; use a non-root UID/GID
    # that matches the image's configured user, or create a dedicated user.
    user: "1000:1000"
    # ...

  # Repeat for other services as needed after confirming their image defaults:
  #   - If an image already uses a non-root user, `user:` may be omitted or aligned.
  #   - If an image defaults to root, set an appropriate non-root UID/GID here.
```

### D2: Networks Not Properly Isolated
**Issue:** All services on default network, no separation between public/internal.

**Fix:**
```yaml
services:
  app:
    networks:
      - internal

  oauth2-proxy:
    networks:
      - public
      - internal

  caddy:
    networks:
      - internal

networks:
  internal:
    internal: true  # No external access
  public:
    driver: bridge
```

### D3: Health Checks Use Python Requests
**File:** `docker-compose.yml:23`
**Issue:** Health check requires Python and requests library, adds dependency.

**Fix:**
```yaml
healthcheck:
  test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:8000/health"]
  # or
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
```

---

## SUMMARY OF CRITICAL ACTIONS NEEDED

### Immediate (Before Production):
1. ✅ **Remove Caddy Admin API public exposure** (H1)
2. ✅ **Secure setup wizard or disable after initial setup** (H2)
3. ✅ **Implement OAuth2 header validation** (H3)
4. ✅ **Add DEV_MODE safety checks** (H4)
5. ✅ **Add CSRF protection** (H6)

### Short Term (Within Sprint):
1. ✅ **Migrate from TinyDB to SQLite** (M1)
2. ✅ **Fix email file race conditions** (H7)
3. ✅ **Improve health check concurrency** (M4)
4. ✅ **Add network isolation in Docker** (D2)
5. ✅ **Fix TLS verification in health checks** (M7)

### Long Term (Next Quarter):
1. ✅ **Add comprehensive type hints** (L1)
2. ✅ **Implement request ID tracking** (L4)
3. ✅ **Add integration tests**
4. ✅ **Set up automated security scanning**
5. ✅ **Implement secret rotation mechanism**

---

## Files Reviewed

✓ `app/app.py` (942 lines)
✓ `app/routes_db.py` (329 lines)
✓ `app/caddy_manager.py` (424 lines)
✓ `app/config.py` (102 lines)
✓ `docker-compose.yml` (109 lines)
✓ `setup-wizard.py` (841 lines)
✓ `generate-secrets.py` (146 lines)
✓ `.env.template` (131 lines)
✓ `caddy/Caddyfile` (20 lines)
✓ `caddy/base.json` (34 lines)
✓ `app/static/js/admin.js` (433 lines)
✓ `app/requirements.txt` (18 lines)

**Total Lines Reviewed:** ~3,529 lines of code

---

## Conclusion

The Shark-no-Ninsho-Mon project has a solid architecture but requires immediate attention to several **HIGH priority security vulnerabilities**, particularly around the Caddy Admin API exposure, setup wizard authentication, and OAuth2 header trust. The codebase demonstrates good practices in input validation and rate limiting, but needs improvements in concurrency control, error handling, and production readiness.

**Primary Focus Areas:**
1. **Network Isolation:** Prevent direct access to internal services
2. **Authentication Validation:** Don't trust forwarded headers blindly
3. **Concurrency Control:** Fix race conditions in file operations and health checks
4. **Production Readiness:** Migrate from TinyDB, add proper logging, implement monitoring

The fixes outlined above will significantly improve the security posture and reliability of the application.
