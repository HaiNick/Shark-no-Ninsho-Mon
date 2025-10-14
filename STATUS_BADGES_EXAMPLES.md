# Status Badge Examples

This document shows the visual representation of status badges in the UI.

## Status Badge Color Scheme

### 🟢 Green (UP State)
**CSS Class:** `.status-badge.up` or `.status-badge.online`
- Background: `rgba(72, 187, 120, 0.1)` - Light green
- Color: `var(--status-online)` - Green text
- **Meaning:** Service is operational and responding normally

### 🟡 Amber (DEGRADED State)
**CSS Class:** `.status-badge.degraded` or `.status-badge.slow`
- Background: `rgba(237, 137, 54, 0.1)` - Light amber
- Color: `var(--status-slow)` - Amber text
- **Meaning:** Service is functional but experiencing performance issues

### 🔴 Red (DOWN State)
**CSS Class:** `.status-badge.down` or `.status-badge.offline`
- Background: `rgba(245, 101, 101, 0.1)` - Light red
- Color: `var(--status-offline)` - Red text
- **Meaning:** Service is not accessible or experiencing critical failures

### ⚪ Gray (UNKNOWN State)
**CSS Class:** `.status-badge.unknown`
- Background: `rgba(160, 174, 192, 0.1)` - Light gray
- Color: `var(--status-unknown)` - Gray text
- **Meaning:** Status has not been determined yet

## Admin Dashboard Examples

### UP State Badges

```
🟢 OK — 200
   Service responding with HTTP 200 OK
   State: UP, Reason: online
   
🟢 OK — 302
   Service redirecting (healthy)
   State: UP, Reason: online
   
🟢 OK — 401
   Service up but requires authentication
   State: UP, Reason: online
   
🟢 OK — 404
   Service up but path not found (config issue, not service issue)
   State: UP, Reason: online
```

### DEGRADED State Badges

```
🟡 SLOW — 2.1s
   Service responding but exceeding 2s threshold
   State: DEGRADED, Reason: slow
   
🟡 SLOW — 3.5s
   Service responding slowly
   State: DEGRADED, Reason: slow
```

### DOWN State Badges

```
🔴 DOWN — DNS
   Cannot resolve hostname
   State: DOWN, Reason: offline_dns
   Error: "DNS error: [Errno -5] No address associated with hostname"
   
🔴 DOWN — Connect
   Cannot establish TCP connection
   State: DOWN, Reason: offline_conn
   Error: "TCP connect failed: [Errno 111] Connection refused"
   
🔴 DOWN — Timeout
   HTTP request timed out
   State: DOWN, Reason: timeout
   Error: "HTTP timeout after 3s"
   
🔴 DOWN — 500
   Server returned 500 Internal Server Error
   State: DOWN, Reason: error_5xx
   
🔴 DOWN — 503
   Service unavailable
   State: DOWN, Reason: error_5xx
   
🔴 DOWN — Error
   Unexpected exception occurred
   State: DOWN, Reason: error_exc
   Error: "Unexpected error: SSLError(...)"
   
🔴 DOWN — Config
   Invalid URL or configuration
   State: DOWN, Reason: misconfig
   Error: "Invalid URL components: missing scheme or hostname"
```

### UNKNOWN State Badge

```
⚪ UNKNOWN
   Status not yet checked
   State: UNKNOWN, Reason: unknown
```

## User Dashboard Examples

The user dashboard shows similar information but with more user-friendly language:

### UP State
```
🟢 Online (200)
🟢 Online
```

### DEGRADED State
```
🟡 Slow (2.8s)
```

### DOWN State
```
🔴 DOWN — DNS
🔴 DOWN — Connect
🔴 DOWN — Timeout
🔴 DOWN — 5xx (503)
🔴 DOWN — Error
🔴 DOWN — Config
🔴 Offline (fallback for unknown reason)
```

### UNKNOWN State
```
⚪ Unknown
```

## Badge with Tooltip (Admin Dashboard)

Badges in the admin dashboard include a tooltip showing the last error message:

```html
<span class="status-badge down" title="DNS error: Name or service not known">
    <span class="status-dot"></span>
    DOWN — DNS
</span>
```

Hovering over the badge reveals the detailed error message.

## Decision Matrix

| HTTP Status | Duration | State | Reason | Badge |
|-------------|----------|-------|--------|-------|
| 200 | < 2s | UP | online | 🟢 OK — 200 |
| 200 | > 2s | DEGRADED | slow | 🟡 SLOW — 2.5s |
| 302 | < 2s | UP | online | 🟢 OK — 302 |
| 401 | < 2s | UP | online | 🟢 OK — 401 |
| 404 | < 2s | UP | online | 🟢 OK — 404 |
| 500 | any | DOWN | error_5xx | 🔴 DOWN — 500 |
| 503 | any | DOWN | error_5xx | 🔴 DOWN — 503 |
| (timeout) | n/a | DOWN | timeout | 🔴 DOWN — Timeout |
| (conn fail) | n/a | DOWN | offline_conn | 🔴 DOWN — Connect |
| (dns fail) | n/a | DOWN | offline_dns | 🔴 DOWN — DNS |
| (bad url) | n/a | DOWN | misconfig | 🔴 DOWN — Config |
| (exception) | n/a | DOWN | error_exc | 🔴 DOWN — Error |
| (not tested) | n/a | UNKNOWN | unknown | ⚪ UNKNOWN |

## CSS Implementation

```css
/* Status badge base */
.status-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.25rem 0.75rem;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
}

/* UP state - green */
.status-badge.up {
    background: rgba(72, 187, 120, 0.1);
    color: var(--status-online);
}

/* DEGRADED state - amber */
.status-badge.degraded {
    background: rgba(237, 137, 54, 0.1);
    color: var(--status-slow);
}

/* DOWN state - red */
.status-badge.down {
    background: rgba(245, 101, 101, 0.1);
    color: var(--status-offline);
}

/* UNKNOWN state - gray */
.status-badge.unknown {
    background: rgba(160, 174, 192, 0.1);
    color: var(--status-unknown);
}

/* Status dot indicator */
.status-badge .status-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: currentColor;
}
```

## JavaScript Rendering (Admin Dashboard)

```javascript
// Determine status badge class and text
let badgeClass = route.status || 'unknown';
let badgeText = 'Unknown';

if (route.state) {
    badgeClass = route.state.toLowerCase();
    
    if (route.state === 'UP') {
        badgeText = route.http_status ? `OK — ${route.http_status}` : 'OK';
    } else if (route.state === 'DEGRADED') {
        badgeText = route.duration_ms ? 
            `SLOW — ${(route.duration_ms / 1000).toFixed(1)}s` : 'SLOW';
    } else if (route.state === 'DOWN') {
        if (route.reason === 'offline_dns') badgeText = 'DOWN — DNS';
        else if (route.reason === 'offline_conn') badgeText = 'DOWN — Connect';
        else if (route.reason === 'timeout') badgeText = 'DOWN — Timeout';
        else if (route.reason === 'error_5xx') 
            badgeText = route.http_status ? `DOWN — ${route.http_status}` : 'DOWN — 5xx';
        else if (route.reason === 'error_exc') badgeText = 'DOWN — Error';
        else if (route.reason === 'misconfig') badgeText = 'DOWN — Config';
        else badgeText = 'DOWN';
    }
}

// Render badge
<span class="status-badge ${badgeClass}" title="${route.last_error || ''}">
    <span class="status-dot"></span>
    ${badgeText}
</span>
```

## Benefits of Visual Design

1. **Color Coding**: Immediate visual recognition of service health
2. **Detailed Text**: Specific reason for status (e.g., "DOWN — DNS")
3. **Timing Information**: Shows actual response time for slow services
4. **HTTP Status**: Shows HTTP code for additional context
5. **Tooltip**: Hover reveals detailed error message
6. **Consistent**: Same visual language across admin and user dashboards

## Accessibility

- Color is not the only indicator (text labels included)
- Tooltips provide additional context
- Status dot provides redundant visual indicator
- Semantic HTML classes for screen readers

## Migration Notes

The UI automatically adapts based on available data:
- If `state` field exists, uses new badge format
- Falls back to `status` field for legacy compatibility
- Gracefully handles missing data (shows "Unknown")
