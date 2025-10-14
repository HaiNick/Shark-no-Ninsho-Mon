# Service Status Classification Guide

This document describes the enhanced service status classification system implemented in Shark-no-Ninsho-Mon.

## Overview

The system uses a two-layer classification hierarchy for clearer service health monitoring:

### Layer 1: State (Coarse-grained)
- **UP** - Service is operational
- **DEGRADED** - Service is functional but experiencing issues (e.g., slow responses)
- **DOWN** - Service is not accessible or experiencing critical failures
- **UNKNOWN** - Status cannot be determined

### Layer 2: Reason (Fine-grained)
- **online** - Service responding normally
- **slow** - Service responding but exceeding latency threshold
- **error_5xx** - Service returned 5xx HTTP error
- **timeout** - HTTP request timed out
- **offline_conn** - TCP connection failed
- **offline_dns** - DNS resolution failed
- **misconfig** - Invalid URL or configuration
- **error_exc** - Unexpected exception occurred
- **unknown** - Status not yet determined

## Decision Tree

The classification follows this deterministic order:

1. **Input Sanity Check**
   - If URL is invalid → `DOWN/misconfig`

2. **DNS Resolution**
   - If DNS fails → `DOWN/offline_dns`

3. **TCP Connection**
   - If connection refused/timeout → `DOWN/offline_conn`

4. **HTTP Request**
   - If HTTP timeout → `DOWN/timeout`
   - If status >= 500 → `DOWN/error_5xx`
   - If duration > SLOW_MS → `DEGRADED/slow`
   - Otherwise → `UP/online`

## Configuration

The following settings can be configured via environment variables:

- `HTTP_TIMEOUT_SEC` - HTTP request timeout (default: 3 seconds, max: 10)
- `SLOW_THRESHOLD_MS` - Threshold for slow responses (default: 2000 ms)

## Database Fields

Routes now track the following enhanced status fields:

- `state` - Current state (UP/DEGRADED/DOWN/UNKNOWN)
- `reason` - Detailed reason for the state
- `http_status` - HTTP status code if available
- `duration_ms` - Response time in milliseconds
- `last_error` - Last error message
- `retries_used` - Number of retries attempted
- `status` - Legacy field (maintained for backward compatibility)

## UI Display

### Admin Dashboard
Status badges show state and reason:
- `OK — 200` (UP/online with HTTP 200)
- `SLOW — 2.8s` (DEGRADED/slow with duration)
- `DOWN — DNS` (DOWN/offline_dns)
- `DOWN — Connect` (DOWN/offline_conn)
- `DOWN — Timeout` (DOWN/timeout)
- `DOWN — 5xx` or `DOWN — 503` (DOWN/error_5xx with status)
- `DOWN — Error` (DOWN/error_exc)
- `DOWN — Config` (DOWN/misconfig)

### User Dashboard
Similar display with more user-friendly language showing service availability.

## Backward Compatibility

The system maintains backward compatibility with the legacy `status` field:
- UP → `online`
- DEGRADED → `slow`
- DOWN/error_5xx or DOWN/error_exc → `error`
- DOWN/timeout → `timeout`
- DOWN/offline_* → `offline`
- UNKNOWN → `unknown`

## Example Usage

### Python API
```python
from caddy_manager import CaddyManager

mgr = CaddyManager()

# Direct classification
state, reason, detail, http_status, duration_ms = mgr.classify_service_status(
    url="http://192.168.1.100:8080/",
    timeout_sec=3,
    slow_ms=2000
)

# Test connection (integrated)
route = {
    "target_ip": "192.168.1.100",
    "target_port": 8080,
    "protocol": "http",
    "timeout": 30
}
result = mgr.test_connection(route)
print(f"State: {result['state']}, Reason: {result['reason']}")
```

### Database Update
```python
from routes_db import RouteManager

route_mgr = RouteManager()

# Update with enhanced status
route_mgr.update_route_status(
    route_id="abc-123",
    state="DOWN",
    reason="offline_dns",
    http_status=None,
    duration_ms=None,
    last_error="DNS error: Name or service not known"
)
```

## Benefits

1. **Clarity** - Clear distinction between availability states
2. **Actionability** - Detailed reasons help debug issues faster
3. **Consistency** - Deterministic classification order
4. **Monitoring** - Better metrics for SLO tracking
5. **Debugging** - Rich error details for troubleshooting

## Testing

The implementation includes comprehensive tests:
- 20 tests for classification logic
- 6 updated tests for backward compatibility
- All tests verify both new and legacy behavior

Run tests:
```bash
cd app
python -m pytest test_classification.py -v
python -m pytest test_caddy_manager.py -v
```

## Migration Notes

Existing routes will automatically receive the new fields on their next health check. The legacy `status` field continues to work for backward compatibility.

No database migration is required - new fields are added automatically when routes are updated.
