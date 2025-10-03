# Reverse Proxy Route Management - Brainstorm

> **Feature Idea**: Add a web UI for managing reverse proxy routes to self-hosted services

## 📋 Overview

Transform Shark-no-Ninsho-Mon from a simple authentication gateway into a **full-featured reverse proxy manager** with a web UI for route configuration.

### Current Setup

- Base URL: `https://sharky.snowy-burbot.ts.net` (Tailscale Funnel)
- Authentication: Google OAuth2 via oauth2-proxy
- Backend: Flask app (port 8000)

### Proposed Enhancement

- **Dynamic Routes**: Users can add custom paths that proxy to internal services
- **What this means**: Route web traffic from your public URL to private services on your network
- **Examples**:
  - `https://sharky.snowy-burbot.ts.net/jellyfin` → `http://192.168.1.100:8096` (Jellyfin media server)
  - `https://sharky.snowy-burbot.ts.net/plex` → `http://192.168.1.101:32400` (Plex media server)
  - `https://sharky.snowy-burbot.ts.net/homelab` → `http://192.168.1.50:3000` (Home Assistant dashboard)
  - `https://sharky.snowy-burbot.ts.net/portainer` → `http://192.168.1.10:9000` (Docker management)

**Use Cases**: Any self-hosted service with a web interface - media servers, home automation, Docker management, monitoring tools, etc.

---

## 🎯 Core Features

### 1. Route Management UI (`/admin` or `/routes`)

**Table View**:

```
┌─────────────┬──────────────────────┬────────────┬──────────────┐
│ Path        │ Target               │ Status     │ Actions      │
├─────────────┼──────────────────────┼────────────┼──────────────┤
│ /jellyfin   │ 192.168.1.100:8096  │ ✅ Online  │ Edit Delete  │
│ /plex       │ 192.168.1.101:32400 │ ✅ Online  │ Edit Delete  │
│ /homelab    │ 192.168.1.50:3000   │ ⚠️ Slow    │ Edit Delete  │
│ /portainer  │ 192.168.1.10:9000   │ ❌ Offline │ Edit Delete  │
└─────────────┴──────────────────────┴────────────┴──────────────┘
```

**Features**:

- ➕ Add New Route button
- 🔄 Refresh Status button
- 📊 Statistics (total routes, online/offline count)
- 🔍 Search/filter routes
- 📥 Export/Import configuration

### 2. Add/Edit Route Form

**Form Fields**:

```
┌──────────────────────────────────────────────────────────┐
│  Add New Route                                           │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Route Path: *                                           │
│  ┌────────────────────────────────────────────────────┐  │
│  │ /jellyfin                                          │  │
│  └────────────────────────────────────────────────────┘  │
│  ℹ️ Must start with /. Only lowercase, numbers, -, _     │
│                                                          │
│  Service Name: *                                         │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Jellyfin Media Server                              │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  Target IP Address: *                                    │
│  ┌────────────────────────────────────────────────────┐  │
│  │ 192.168.1.100                                      │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  Target Port: *                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │ 8096                                               │  │
│  └────────────────────────────────────────────────────┘  │
│  ℹ️ Port range: 1-65535                                  │
│                                                          │
│  Protocol:                                               │
│  ⦿ HTTP    ○ HTTPS                                      │
│                                                          │
│  Advanced Settings (Optional) ▼                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │ [ ] Enable Health Check                            │  │
│  │ [ ] Preserve Host Header                           │  │
│  │ [ ] WebSocket Support                              │  │
│  │ Timeout: [30] seconds                              │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  [Test Connection]  [Cancel]  [Save Route]               │
└──────────────────────────────────────────────────────────┘
```

### 3. Dynamic Proxy Handler

**Flow**:

1. User requests: `https://sharky.snowy-burbot.ts.net/jellyfin/dashboard`
2. Flask catches the request
3. Looks up `/jellyfin` in routes config
4. Proxies to `http://192.168.1.100:8096/dashboard`
5. Returns response to user

**Implementation Options**:

- Option A: Flask with `requests` library (simple)
- Option B: Flask with `werkzeug.middleware.proxy_fix` (better headers)
- Option C: Integrate nginx config generation (most powerful)
- Option D: Use Traefik labels in Docker (dynamic)

---

## 💾 Data Storage - TinyDB

We're using **TinyDB** - the perfect balance between simplicity and power! 🎯

### Why TinyDB?

```python
from tinydb import TinyDB, Query

# Initialize
db = TinyDB('routes.json')
routes_table = db.table('routes')

# Insert
routes_table.insert({
    'path': '/jellyfin',
    'name': 'Jellyfin Media Server',
    'target_ip': '192.168.1.100',
    'target_port': 8096,
    'protocol': 'http',
    'enabled': True,
    'health_check': True,
    'timeout': 30
})

# Query
Route = Query()
jellyfin = routes_table.search(Route.path == '/jellyfin')

# Update
routes_table.update({'enabled': False}, Route.path == '/jellyfin')

# Delete
routes_table.remove(Route.path == '/jellyfin')
```

### Advantages

- ✅ **Simple like JSON** - Human-readable storage format
- ✅ **Powerful like a database** - Query, filter, update capabilities
- ✅ **No SQL required** - Pythonic API that's easy to learn
- ✅ **Thread-safe** - Automatic file locking, handles concurrent access
- ✅ **Zero configuration** - No external services or setup needed
- ✅ **Docker-friendly** - Just mount the JSON file as a volume
- ✅ **Lightweight** - Only ~50KB, minimal overhead
- ✅ **Perfect for this use case** - Great for <10,000 routes

### Trade-offs

- ⚠️ Not suitable for huge datasets (>10,000 records)
- ⚠️ No complex joins or relationships (but we don't need them!)
- ⚠️ Slower than Redis for high-traffic scenarios (but fine for route management)

### TinyDB Implementation Example

**File Structure**:

```
app/
├── app.py
├── routes_db.py          # TinyDB wrapper class
├── routes.json           # Auto-generated by TinyDB
└── requirements.txt
```

**Code Example** (`routes_db.py`):

```python
from tinydb import TinyDB, Query
from typing import List, Dict, Optional
import uuid
from datetime import datetime

class RouteManager:
    def __init__(self, db_path='routes.json'):
        self.db = TinyDB(db_path)
        self.routes = self.db.table('routes')
        self.Route = Query()

    def add_route(self, path: str, name: str, target_ip: str,
                  target_port: int, protocol: str = 'http',
                  health_check: bool = True, timeout: int = 30) -> Dict:
        """Add a new route"""
        # Check if path already exists
        if self.get_route_by_path(path):
            raise ValueError(f"Route {path} already exists")

        route = {
            'id': str(uuid.uuid4()),
            'path': path,
            'name': name,
            'target_ip': target_ip,
            'target_port': target_port,
            'protocol': protocol,
            'enabled': True,
            'health_check': health_check,
            'timeout': timeout,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }

        self.routes.insert(route)
        return route

    def get_all_routes(self, enabled_only: bool = False) -> List[Dict]:
        """Get all routes"""
        if enabled_only:
            return self.routes.search(self.Route.enabled == True)
        return self.routes.all()

    def get_route_by_path(self, path: str) -> Optional[Dict]:
        """Get route by path"""
        result = self.routes.search(self.Route.path == path)
        return result[0] if result else None

    def get_route_by_id(self, route_id: str) -> Optional[Dict]:
        """Get route by ID"""
        result = self.routes.search(self.Route.id == route_id)
        return result[0] if result else None

    def update_route(self, route_id: str, updates: Dict) -> bool:
        """Update a route"""
        updates['updated_at'] = datetime.now().isoformat()
        result = self.routes.update(updates, self.Route.id == route_id)
        return len(result) > 0

    def delete_route(self, route_id: str) -> bool:
        """Delete a route"""
        result = self.routes.remove(self.Route.id == route_id)
        return len(result) > 0

    def toggle_route(self, route_id: str) -> bool:
        """Enable/disable a route"""
        route = self.get_route_by_id(route_id)
        if route:
            new_status = not route['enabled']
            return self.update_route(route_id, {'enabled': new_status})
        return False

    def search_routes(self, query: str) -> List[Dict]:
        """Search routes by name or path"""
        return self.routes.search(
            (self.Route.name.search(query, flags=0)) |
            (self.Route.path.search(query, flags=0))
        )
```

**Usage in Flask** (`app.py`):

```python
from flask import Flask, jsonify, request
from routes_db import RouteManager

app = Flask(__name__)
route_manager = RouteManager('/app/routes.json')

@app.route('/api/routes', methods=['GET'])
def get_routes():
    """Get all routes"""
    routes = route_manager.get_all_routes()
    return jsonify(routes)

@app.route('/api/routes', methods=['POST'])
def create_route():
    """Create new route"""
    data = request.json
    try:
        route = route_manager.add_route(
            path=data['path'],
            name=data['name'],
            target_ip=data['target_ip'],
            target_port=data['target_port'],
            protocol=data.get('protocol', 'http'),
            health_check=data.get('health_check', True),
            timeout=data.get('timeout', 30)
        )
        return jsonify(route), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/routes/<route_id>', methods=['PUT'])
def update_route(route_id):
    """Update route"""
    data = request.json
    if route_manager.update_route(route_id, data):
        return jsonify({'success': True})
    return jsonify({'error': 'Route not found'}), 404

@app.route('/api/routes/<route_id>', methods=['DELETE'])
def delete_route(route_id):
    """Delete route"""
    if route_manager.delete_route(route_id):
        return jsonify({'success': True})
    return jsonify({'error': 'Route not found'}), 404
```

**Generated JSON File** (`routes.json`):

```json
{
  "routes": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "path": "/jellyfin",
      "name": "Jellyfin Media Server",
      "target_ip": "192.168.1.100",
      "target_port": 8096,
      "protocol": "http",
      "enabled": true,
      "health_check": true,
      "timeout": 30,
      "created_at": "2025-10-03T14:30:00",
      "updated_at": "2025-10-03T14:30:00"
    }
  ],
  "_default": {}
}
```

**Why This Works Great**:

- 🔒 Thread-safe out of the box
- 📝 Human-readable JSON format
- 🔍 Powerful querying without SQL
- 🚀 Easy to backup (just copy the JSON file)
- 🐳 Docker-friendly (mount as volume)
- 💾 Small footprint (~50KB for TinyDB library)

---

## 🏗️ Architecture

### Current Architecture

```
Internet → Tailscale Funnel → oauth2-proxy (port 4180) → Flask App (port 8000)
```

### Proposed Architecture

```
Internet → Tailscale Funnel → oauth2-proxy (port 4180) → Flask Proxy Manager (port 8000)
                                                               ├─ /           → Main Dashboard
                                                               ├─ /admin      → Route Management UI
                                                               ├─ /jellyfin/* → Jellyfin (192.168.1.100:8096)
                                                               ├─ /plex/*     → Plex (192.168.1.101:32400)
                                                               └─ /homelab/*  → Homelab (192.168.1.50:3000)
```

### Components to Build

#### Backend (`app.py`)

- [ ] `RouteManager` class - CRUD operations for routes
- [ ] `ProxyHandler` class - Handle proxy requests
- [ ] `/admin` - Route management page
- [ ] `/api/routes` - GET all routes (JSON)
- [ ] `/api/routes` - POST create route
- [ ] `/api/routes/<id>` - PUT update route
- [ ] `/api/routes/<id>` - DELETE remove route
- [ ] `/api/routes/<id>/test` - Test route connectivity
- [ ] `/<proxy_path>/*` - Dynamic proxy catch-all

#### Frontend (Templates)

- [ ] `admin.html` - Route management interface
- [ ] `route_form.html` - Add/edit route modal
- [ ] Update `index.html` - Show available routes to user

#### Storage (TinyDB Approach)

- [ ] `routes_db.py` - TinyDB wrapper class for route management
- [ ] `routes.json` - TinyDB storage file (auto-generated)
- [ ] Add `routes.json` to Docker volumes in `docker-compose.yml`

#### Static Assets

- [ ] `css/admin.css` - Styling for admin interface
- [ ] `js/admin.js` - JavaScript for form handling, AJAX requests

---

## 🎨 UI/UX Design Ideas

### Dashboard Enhancement

Show available services to authenticated users:

```
┌─────────────────────────────────────────────────────────┐
│  Welcome back, user@example.com                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Your Available Services:                               │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │ 🎬       │  │ 🎭      │  │ 🏠       │               │
│  │ Jellyfin │  │ Plex     │  │ Homelab  │               │
│  │ Media    │  │ Media    │  │ Dashboard│               │
│  └──────────┘  └──────────┘  └──────────┘               │
│                                                         │
│  [🔧 Manage Routes] (Admin only)                        │
└─────────────────────────────────────────────────────────┘
```

### Color Coding

- 🟢 Green: Service online and responding
- 🟡 Yellow: Service slow (>2s response)
- 🔴 Red: Service offline or unreachable
- ⚫ Gray: Health check disabled

### UI Design Inspiration (from example_web_ui)

**Visual Style**:

```
🎨 Glassmorphism Design
├── Backdrop blur effects on cards
├── Gradient backgrounds with animations
├── Smooth transitions and hover effects
├── Card-based layouts with shadows
└── Modern, clean aesthetic
```

**Key Elements to Incorporate**:

1. **Animated Background**

   - Floating particles/clouds
   - Subtle gradient overlays
   - Creates depth and visual interest

2. **Card-Based Layout**

   - Rounded corners (border-radius: 12px)
   - Subtle shadows (box-shadow)
   - Backdrop blur for glass effect
   - Clean white/dark mode support

3. **Modern Forms**

   - Clean input fields with focus states
   - Gradient buttons with hover animations
   - Icon integration (Font Awesome)
   - Smooth transitions

4. **Color Palette**

   - Primary: Purple gradients (#667eea → #764ba2)
   - Status indicators: Green/Yellow/Red
   - Light mode: White cards, subtle borders
   - Dark mode: Dark cards, lighter text

5. **Interactive Elements**
   - Smooth hover effects (transform, shadow)
   - Dropdown menus with animations
   - Button press feedback
   - Loading states

**CSS Variables to Use**:

```css
:root {
  --card-bg: rgba(255, 255, 255, 0.9);
  --card-border: rgba(0, 0, 0, 0.1);
  --text-primary: #1a202c;
  --text-secondary: #4a5568;
  --gradient-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

[data-theme="dark"] {
  --card-bg: rgba(30, 30, 40, 0.9);
  --card-border: rgba(255, 255, 255, 0.1);
  --text-primary: #f7fafc;
  --text-secondary: #cbd5e0;
}
```

---

## 🔒 Security Considerations

### 1. Authorization ✅ DECIDED

**Route Management Access**: **All authenticated users** from `emails.txt` can manage routes

- ✅ Simpler setup - no separate admin list needed
- ✅ Trust-based model - all authorized users are trusted
- ✅ Easier for small teams/personal use
- ⚠️ Note: All users have equal permissions (no separate admin role)

### 2. Input Validation

- ✅ Path must start with `/`
- ✅ Path must be unique
- ✅ IP must be valid (regex validation)
- ✅ Port must be 1-65535
- ✅ Prevent SSRF attacks (block localhost, 127.0.0.1, metadata IPs)
- ✅ No path traversal (sanitize paths)

### 3. Private Network Access

- ⚠️ Should we allow proxying to public IPs?
- ✅ Whitelist private IP ranges (10.x, 192.168.x, 172.16-31.x)
- ✅ Block cloud metadata endpoints (169.254.169.254)

### 4. Rate Limiting

- Apply rate limits to admin endpoints
- Prevent brute force on proxy routes

---

## 🧪 Testing Strategy

### Unit Tests

- Route CRUD operations
- Input validation
- Proxy request handling
- Health check system

### Integration Tests

- End-to-end route creation
- Proxy request flow
- Error handling

### Manual Testing Checklist

- [ ] Add valid route
- [ ] Add invalid route (should fail)
- [ ] Edit existing route
- [ ] Delete route
- [ ] Proxy request through route
- [ ] Handle offline service gracefully
- [ ] Test with different HTTP methods (GET, POST, PUT, DELETE)
- [ ] Test with WebSocket connections
- [ ] Test with large file uploads/downloads

---

## 🚀 Implementation Phases

### Phase 1: MVP (Minimum Viable Product)

**Goal**: Basic route management with simple proxying

- [ ] JSON storage for routes
- [ ] Simple admin UI (table + form)
- [ ] Basic proxy handler
- [ ] Manual route testing
- **Estimated Time**: 4-6 hours

### Phase 2: Enhanced Features

**Goal**: Better UX and reliability

- [ ] Health check system
- [ ] Status indicators
- [ ] Better error handling
- [ ] Route statistics (request count, latency)
- **Estimated Time**: 3-4 hours

### Phase 3: Advanced Features

**Goal**: Production-ready

- [ ] Request/response logging per route
- [ ] Import/export config
- [ ] Backup/restore functionality
- [ ] Route analytics (hits, bandwidth)
- **Estimated Time**: 3-4 hours

### Phase 4: Polish & UI

**Goal**: Beautiful, production-ready interface

- [ ] Glassmorphism UI (inspired by example_web_ui)
- [ ] Animated gradient backgrounds
- [ ] Dark mode toggle
- [ ] Mobile responsive design
- [ ] Smooth animations and transitions
- [ ] Loading states and feedback
- [ ] Keyboard shortcuts
- [ ] Documentation
- **Estimated Time**: 4-6 hours

---

## 🤔 Open Questions

1. **Admin Authentication**:

   - Separate admin list or reuse existing `emails.txt`?
   - How to designate first admin?

2. **Route Conflicts**:

   - What if two routes have overlapping paths?
   - Should we support route priority/ordering?

3. **Service Discovery**:

   - Auto-discover services on local network?
   - Import from Docker labels?
   - Integration with Portainer/other tools?

4. **Backup Strategy**:

   - Auto-backup routes.json before changes?
   - Version history of changes?
   - Who made what changes (audit log)?

5. **Multi-User Scenarios**:

   - Different users see different services?
   - Per-route access control?
   - Team/group support?

6. **Headers**:

   - Should we pass authentication headers to proxied services?
   - Custom header injection per route?
   - Header transformation rules?

7. **Performance**:

   - Cache DNS lookups?
   - Connection pooling?
   - Request timeout defaults?

8. **Monitoring**:
   - Prometheus metrics?
   - Alerting on service down?
   - Integration with existing monitoring?

---

## 📦 Dependencies to Add

### Python Packages (Core)

```txt
requests>=2.31.0          # For making proxy requests
validators>=0.22.0        # IP and URL validation
tinydb>=4.8.0            # Database for route storage (RECOMMENDED)
```

### Optional Enhancements (Future)

```txt
aiohttp>=3.9.0           # For async proxy (performance improvement)
prometheus-client>=0.19.0 # For metrics and monitoring
websockets>=12.0         # For WebSocket support (if needed later)
```

---

## 📚 Reference Implementation

### Similar Projects

1. **Nginx Proxy Manager** - Web UI for nginx reverse proxy
2. **Traefik** - Modern reverse proxy with dynamic configuration
3. **Caddy** - Automatic HTTPS reverse proxy
4. **Cloudflare Tunnel** - Similar concept to Tailscale Funnel

### Learning from Others

- **NPM**: Great UI for route management
- **Traefik**: Dynamic configuration via labels
- **Caddy**: Simple config syntax

---

## 🎯 Success Criteria

### Functional Requirements

- ✅ Users can add routes via web UI
- ✅ Routes persist across restarts
- ✅ Proxy requests work correctly
- ✅ Authentication is preserved
- ✅ Errors are handled gracefully

### Non-Functional Requirements

- ✅ UI is intuitive and easy to use
- ✅ Performance: <100ms overhead per request
- ✅ Reliable: 99.9% uptime
- ✅ Secure: No unauthorized access to admin
- ✅ Documented: Clear README and help text

---

## 💡 Future Ideas (v2.0+)

- 🔄 **Load Balancing**: Multiple targets per route
- 🌐 **DNS Management**: Custom subdomain routing
- 📊 **Analytics Dashboard**: Request stats, popular services
- 🔐 **Per-Route Auth**: Different auth requirements per service
- 🎨 **Custom Themes**: User-selectable UI themes
- 📱 **Mobile App**: Manage routes on the go
- 🔔 **Notifications**: Alert on service downtime
- 🤖 **Auto-Healing**: Restart services automatically
- 🐳 **Docker Integration**: Auto-configure from docker-compose
- 🏃 **Service Presets**: One-click setup for popular apps

---

## 📝 Notes & Thoughts

### Design Philosophy

- **Simple First**: Start with basic features, add complexity later
- **User-Friendly**: Non-technical users should be able to add routes
- **Secure by Default**: Better to block than allow by mistake
- **Observable**: Easy to debug when things go wrong

### Development Notes

- Keep backwards compatibility with existing setup
- Don't break current auth flow
- Make it optional (can run without route management)
- Good error messages are critical

### Deployment Considerations

- Routes should survive container restarts
- Need volume mount for `routes.json`
- Consider migration path from simple gateway to proxy manager

---

## 🤝 Collaboration & Feedback

### ✅ Key Decisions Summary

| Decision            | Choice            | Rationale                                                          |
| ------------------- | ----------------- | ------------------------------------------------------------------ |
| **Storage**         | TinyDB            | Perfect balance: simple like JSON, powerful like DB, thread-safe   |
| **Access Control**  | All users         | Simpler setup, trust-based model for authorized users              |
| **Scope**           | HTTP/HTTPS only   | Web UI routing only, no network traffic (WebSocket optional later) |
| **UI Style**        | Glassmorphism     | Modern, clean design inspired by example_web_ui                    |
| **Theme**           | Light + Dark mode | User preference with toggle                                        |
| **Target Services** | Any web interface | Jellyfin, Plex, Portainer, Home Assistant, etc.                    |

### Decisions Made in Detail

1. ✅ **Storage**: **TinyDB**
   - Perfect balance of simplicity and power
   - Human-readable JSON format
   - Built-in querying and thread-safety
2. ✅ **Access Control**: **All authenticated users** can manage routes
   - No separate admin role needed
   - Everyone in `emails.txt` is trusted equally
   - Simpler for small teams/personal use
3. ✅ **Use Case**: General-purpose reverse proxy for self-hosted services
   - Routes web UI traffic to internal services
   - Examples: Jellyfin, Plex, Portainer, Home Assistant
   - Works with any service that has a web interface
4. ✅ **UI Design**: Modern glassmorphism design inspired by `example_web_ui`
   - Animated gradient backgrounds with particles
   - Card-based layout with backdrop blur effects
   - Clean, modern forms with smooth animations
   - Font Awesome icons throughout
   - Light/dark mode support with theme toggle
5. ✅ **WebSocket Support**: **Not initially**
   - Focus on HTTP/HTTPS routing only
   - Routes web UI, not all network traffic
   - Can be added in Phase 3+ if needed

### Next Steps

1. Review this brainstorm document
2. Decide on MVP features
3. Choose implementation approach
4. Start building! 🚀

---

## 📄 License & Credits

This feature would be added to **Shark-no-Ninsho-Mon** under the existing license.

**Inspired by**: Nginx Proxy Manager, Traefik, Cloudflare Tunnel

---

_Last Updated: October 3, 2025_
_Status: 🧠 Brainstorming Phase_
