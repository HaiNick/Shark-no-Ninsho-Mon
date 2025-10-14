# Status Classification Changes Summary

## What Changed

This PR implements an enhanced service status classification system with a two-layer hierarchy for clearer monitoring and debugging.

## Before vs After

### Before (Legacy System)
```
Status Values: online, offline, slow, error, timeout, unknown
```

Single-level status that mixed availability and performance concerns.

### After (Enhanced System)
```
State:  UP, DEGRADED, DOWN, UNKNOWN
Reason: online, slow, error_5xx, timeout, offline_conn, offline_dns, misconfig, error_exc, unknown
```

Two-level hierarchy with clear states and detailed reasons.

## Status Badge Examples

### Admin Dashboard - Old vs New

**Old Display:**
```
[🟢 Online]      → Service up
[🟡 Slow]        → Service slow
[🔴 Offline]     → Service down (unclear why)
[🔴 Error]       → Service error (unclear why)
[🔴 Timeout]     → Request timeout
```

**New Display:**
```
[🟢 OK — 200]              → UP/online with HTTP 200
[🟢 OK — 401]              → UP/online (Protected endpoint)
[🟡 SLOW — 2.8s]           → DEGRADED/slow with timing
[🔴 DOWN — DNS]            → DOWN/offline_dns (DNS failed)
[🔴 DOWN — Connect]        → DOWN/offline_conn (TCP failed)
[🔴 DOWN — Timeout]        → DOWN/timeout (HTTP timeout)
[🔴 DOWN — 503]            → DOWN/error_5xx with status
[🔴 DOWN — Error]          → DOWN/error_exc (Unexpected)
[🔴 DOWN — Config]         → DOWN/misconfig (Invalid URL)
```

## Classification Flow

```
┌─────────────────────────────────────┐
│ 1. Input Validation                 │
│    Invalid URL?                     │
│    → DOWN/misconfig                 │
└─────────────┬───────────────────────┘
              │
┌─────────────▼───────────────────────┐
│ 2. DNS Resolution                   │
│    Can resolve hostname?            │
│    → NO: DOWN/offline_dns           │
└─────────────┬───────────────────────┘
              │
┌─────────────▼───────────────────────┐
│ 3. TCP Connection                   │
│    Can connect to port?             │
│    → NO: DOWN/offline_conn          │
└─────────────┬───────────────────────┘
              │
┌─────────────▼───────────────────────┐
│ 4. HTTP Request                     │
│    Timeout? → DOWN/timeout          │
│    Status >= 500? → DOWN/error_5xx  │
│    Duration > 2s? → DEGRADED/slow   │
│    Otherwise → UP/online            │
└─────────────────────────────────────┘
```

## Database Schema Changes

### New Fields Added to Routes
```python
{
    # Legacy (preserved for compatibility)
    "status": "online",              # Old field
    
    # New Enhanced Fields
    "state": "UP",                   # UP, DEGRADED, DOWN, UNKNOWN
    "reason": "online",              # Detailed reason
    "http_status": 200,              # HTTP status code (nullable)
    "duration_ms": 150,              # Response time in ms (nullable)
    "last_error": None,              # Error message (nullable)
    "retries_used": 0,               # Number of retries
    "last_check": "2025-01-15T10:30:00"
}
```

## Configuration Options

### New Environment Variables
```bash
# HTTP request timeout (default: 3s, max: 10s)
HTTP_TIMEOUT_SEC=3

# Threshold for slow responses (default: 2000ms)
SLOW_THRESHOLD_MS=2000
```

### Why These Defaults?
- **3s timeout**: Balances between catching slow services and avoiding false positives
- **2s slow threshold**: Industry standard for user-perceivable delays
- Both are configurable per environment needs

## API Response Changes

### test_connection() Response - Before
```json
{
    "success": true,
    "status": "online",
    "status_code": 200,
    "response_time": 150
}
```

### test_connection() Response - After
```json
{
    "success": true,
    "status": "online",           // Legacy field (maintained)
    "state": "UP",                // New field
    "reason": "online",           // New field
    "detail": "HTTP 200 in 150 ms", // New field
    "status_code": 200,
    "response_time": 150
}
```

## Benefits

### 1. Clearer Monitoring
- Instant understanding of service health with state
- Detailed troubleshooting with reason

### 2. Better Alerting
```python
# Simple alert rule:
if state == "DOWN":
    send_alert(f"Service down: {reason}")
```

### 3. Improved Debugging
```python
# Each DOWN state has specific reason:
- offline_dns     → Check DNS configuration
- offline_conn    → Check firewall/network
- timeout         → Check service load/performance
- error_5xx       → Check service logs
- misconfig       → Fix URL configuration
```

### 4. SLO Tracking
```python
# Treat DEGRADED as SLO violation:
if state == "DEGRADED":
    track_slo_violation(duration_ms)
```

### 5. Enhanced UX
Users see exactly what's wrong:
- "DOWN — DNS" is clearer than "Offline"
- "SLOW — 2.8s" shows actual impact
- "OK — 401" indicates protected but healthy

## Testing

### Test Coverage
- ✅ 20 new classification logic tests
- ✅ 6 updated backward compatibility tests
- ✅ 14 existing routes_db tests (all pass)
- ✅ Manual verification of classification flow

### Run Tests
```bash
cd app
python -m pytest test_classification.py -v
python -m pytest test_caddy_manager.py -v
python -m pytest test_routes_db.py -v
```

## Migration Path

### Automatic Migration
- No manual database migration needed
- New fields added automatically on next health check
- Legacy `status` field continues to work
- Backward compatible with existing code

### For Developers
```python
# Old code still works:
if route["status"] == "online":
    print("Service is up")

# New code has more detail:
if route["state"] == "UP" and route["reason"] == "online":
    print(f"Service healthy: {route['http_status']} in {route['duration_ms']}ms")
```

## Real-World Examples

### Scenario 1: DNS Misconfiguration
**Before:** Status shows "Offline" - unclear why  
**After:** Shows "DOWN — DNS" with error "DNS error: [Errno -5] No address associated with hostname"

### Scenario 2: Slow Backend
**Before:** Status shows "Online" or "Slow" inconsistently  
**After:** Shows "SLOW — 2.3s" with consistent 2-second threshold

### Scenario 3: Service Overload
**Before:** Status shows "Error" or "Timeout"  
**After:** Shows "DOWN — 503" for server errors or "DOWN — Timeout" for timeouts

### Scenario 4: Protected Endpoint
**Before:** Status shows "Online" for 401  
**After:** Shows "OK — 401" indicating healthy but protected

## Files Changed

### Core Implementation
- `app/config.py` - Added HTTP_TIMEOUT_SEC and SLOW_THRESHOLD_MS settings
- `app/caddy_manager.py` - Implemented classify_service_status() and enhanced test_connection()
- `app/routes_db.py` - Added new status fields and enhanced update_route_status()
- `app/app.py` - Updated health check worker to use new fields

### UI/Frontend
- `app/static/css/shared.css` - Added new state-based CSS classes
- `app/static/js/admin.js` - Enhanced status badge rendering
- `app/templates/index.html` - Updated service status display

### Testing
- `app/test_classification.py` - New comprehensive test suite (20 tests)
- `app/test_caddy_manager.py` - Updated for backward compatibility

### Documentation
- `CLASSIFICATION_GUIDE.md` - Complete usage guide
- `STATUS_CLASSIFICATION_CHANGES.md` - This file
- `.env.template` - Added new configuration options

## Summary

This enhancement provides:
- ✅ Clear two-level status hierarchy (state + reason)
- ✅ Deterministic classification logic
- ✅ Better debugging with detailed error messages
- ✅ Improved UI with actionable status badges
- ✅ Full backward compatibility
- ✅ Comprehensive test coverage
- ✅ Configurable thresholds
- ✅ Zero-downtime migration

The system is production-ready and provides immediate value for service monitoring and troubleshooting.
