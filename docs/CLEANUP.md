# Optional Cleanup Guide

After successfully migrating to Caddy edge proxy, you can optionally clean up files that are no longer needed in the data path.

## Files That Can Be Removed

### Deprecated Proxy Handler
These files are no longer used for proxying (Caddy handles that), but are currently kept for health check functionality:

```
app/proxy_handler.py          # 457 lines - only test_connection() is used now
app/test_proxy_handler.py     # Tests for proxy_handler
```

### Why Keep Them?
- `proxy_handler.py` is still used for:
  - `test_connection()` - Tests backend connectivity from Flask
  - Health check worker - Monitors backend status

### Why Remove Them?
- **Simplify codebase**: Remove 500+ lines of complex proxy logic
- **Single responsibility**: Flask only manages routes, Caddy does all proxying
- **Reduce dependencies**: Less code to maintain and test

## Option 1: Remove Immediately (Recommended)

If you don't need Flask-based health checks, remove these files now:

### Step 1: Remove health check functionality from app.py

```python
# In app/app.py, remove:
# - The entire health_check_worker() function
# - The start_health_check_worker() function
# - The health check worker thread startup code
# - The /api/routes/<route_id>/test endpoint (or move to caddy_manager.py)
```

### Step 2: Remove imports

```python
# In app/app.py, remove:
from proxy_handler import ProxyHandler

# Remove initialization:
proxy_handler = ProxyHandler(route_manager, verify_ssl=settings.upstream_ssl_verify)
```

### Step 3: Delete files

```bash
rm app/proxy_handler.py
rm app/test_proxy_handler.py
```

### Step 4: Update test endpoint (optional)

If you want to keep the connection test functionality, move it to `caddy_manager.py`:

```python
# In app/caddy_manager.py, add:
def test_connection(self, target_ip: str, target_port: int, protocol: str = 'http', timeout: int = 10) -> dict:
    """Test connectivity to a backend service"""
    import time
    target_url = f"{protocol}://{target_ip}:{target_port}/"
    
    try:
        start = time.time()
        resp = requests.get(target_url, timeout=timeout, verify=False)
        duration = int((time.time() - start) * 1000)  # ms
        
        if resp.status_code < 500:
            status = 'online' if duration <= 2000 else 'slow'
        else:
            status = 'error'
        
        return {
            'success': True,
            'status': status,
            'status_code': resp.status_code,
            'response_time': duration
        }
    except requests.exceptions.Timeout:
        return {'success': False, 'error': 'Connection timeout', 'status': 'timeout'}
    except requests.exceptions.ConnectionError:
        return {'success': False, 'error': 'Connection refused', 'status': 'offline'}
    except Exception as e:
        return {'success': False, 'error': str(e), 'status': 'error'}
```

Then update the test endpoint in `app/app.py`:

```python
@app.route('/api/routes/<route_id>/test', methods=['POST'])
@limiter.limit("30 per hour")
def api_test_route(route_id):
    """Test route connectivity"""
    email = get_user_email()
    
    if not is_authorized():
        return jsonify({'error': 'Unauthorized'}), 403
    
    route = route_manager.get_route_by_id(route_id)
    if not route:
        return jsonify({'error': 'Route not found'}), 404
    
    result = caddy_mgr.test_connection(
        route['target_ip'],
        route['target_port'],
        route.get('protocol', 'http'),
        route.get('timeout', 30)
    )
    
    # Update route status
    if result.get('success'):
        route_manager.update_route_status(route_id, result['status'])
    
    logger.info(f"ROUTE_TEST - User: {email} | Route: {route_id} | Result: {result.get('status', 'error')}")
    
    return jsonify(result)
```

## Option 2: Use Caddy's Built-in Health Checking

Caddy has native health checking. You can configure it in the route config:

```python
# In app/caddy_manager.py, update _subdir_reverse_proxy_route():
handler = {
    "handler": "reverse_proxy",
    "upstreams": [ { "dial": f"{hostport}" } ],
    "health_checks": {
        "active": {
            "path": "/health",  # or whatever health endpoint the backend has
            "interval": "30s",
            "timeout": "5s"
        }
    },
    "headers": { "request": { "set": set_headers } }
}
```

With this approach:
1. Caddy monitors backend health automatically
2. Unhealthy backends are removed from rotation
3. No need for Flask-based health checks
4. Remove the entire health check worker from `app/app.py`

## Option 3: Keep As-Is (Conservative)

If you're unsure or want to keep monitoring from Flask:
- Keep `proxy_handler.py` for now
- Keep health check worker running
- Evaluate after a few weeks of production use
- Clean up later when confident

## Recommendation

**Start with Option 3 (keep as-is)**, then move to **Option 2 (Caddy health checks)** after validating the migration works well.

This gives you:
- Safe migration path
- Time to observe behavior
- Caddy's native health checking (more efficient)
- Eventual removal of 500+ lines of proxy code

## Testing After Cleanup

If you remove files, test:
1. Routes still sync to Caddy
2. Connection test endpoint works (if kept)
3. Health checks work (if migrated to Caddy)
4. No import errors on startup

```bash
docker compose down
docker compose build app
docker compose up -d
docker compose logs app
```

## Rollback Cleanup

If something breaks after cleanup, restore files from git:

```bash
git checkout HEAD -- app/proxy_handler.py app/test_proxy_handler.py
git checkout HEAD -- app/app.py  # if you modified it
```

## Summary

| Option | Complexity | Risk | Benefit |
|--------|-----------|------|---------|
| Keep as-is | Low | None | Safe migration |
| Caddy health checks | Medium | Low | Native health checking |
| Remove immediately | High | Medium | Simplified codebase |

**Recommended path**: Keep → Validate → Migrate health checks to Caddy → Remove

---

Questions? See `docs/MIGRATION.md` for more help.
