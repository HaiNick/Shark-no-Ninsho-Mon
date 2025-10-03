# Implementation Roadmap - Reverse Proxy Route Manager

> **Step-by-step guide to implement the reverse proxy route management feature**

**Status**: 📋 Planning Phase  
**Last Updated**: October 3, 2025  
**Estimated Total Time**: 15-20 hours

---

## 📊 Overview

Transform Shark-no-Ninsho-Mon into a full reverse proxy manager with dynamic route configuration through a beautiful web UI.

### What We're Building

```
┌─────────────────────────────────────────────────────────────┐
│  Before: Simple auth gateway                                │
│  After:  Auth gateway + Route Manager (Enhanced!)           │
└─────────────────────────────────────────────────────────────┘

⚠️ IMPORTANT: We're REBUILDING the `app/` directory from scratch!
   - Complete fresh rebuild with route manager built-in
   - Old app backed up and can be restored if needed
   - All existing features re-implemented in new architecture
   - Cleaner codebase, better structure
```

**User Flow** (All features work the same, just better implementation):
1. Login via Google OAuth ✅ (re-implemented)
2. See dashboard with available services ✨ (new - shows managed routes)
3. Click "Manage Routes" to add new services ✨ (new feature)
4. Add route: /jellyfin → 192.168.1.100:8096 ✨ (new feature)
5. Access https://sharky.snowy-burbot.ts.net/jellyfin ✨ (new feature)
6. Get proxied to Jellyfin server ✨ (new feature)

**Rebuild Strategy**: Fresh start with better architecture!
- 🗑️ Remove old `app/` directory completely
- 💾 Backup saved in `app_backup_*` folder + git history
- ✨ Build new app from scratch with modern architecture
- ✅ Re-implement all existing features (auth, logging, health)
- ✅ Add route management features built-in
- 🔄 Can restore old app anytime from backup or git

### Deployment Options

The Route Manager is integrated into the existing Flask app, so it runs as part of the same Docker container:

**Option 1: Docker (Recommended - Production)**
```
docker-compose.yml
├── oauth2-proxy service (existing)
└── app service (Flask + Route Manager)
    ├── Authentication gateway (existing)
    ├── Route management UI (new)
    └── Dynamic proxy handler (new)
```

**Option 2: Standalone (Development/Testing)**
```powershell
# Run Flask app directly without Docker
cd app
python app.py
# Access at http://localhost:8000
```

**Both options use the same codebase** - Docker is preferred for production as it includes:
- OAuth2 proxy for Google authentication
- Tailscale Funnel for public access
- Automatic restarts and health checks
- Volume persistence for routes.json

### Architecture Details

```
Production (Docker):
┌─────────────────────────────────────────────────────────┐
│ Docker Compose Stack                                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────┐        ┌──────────────────────┐  │
│  │ oauth2-proxy    │───────▶│ app (Flask)          │  │
│  │ Port: 4180      │        │ Port: 8000           │  │
│  │                 │        │                      │  │
│  │ - Google OAuth  │        │ - Auth Gateway       │  │
│  │ - Cookie mgmt   │        │ - Route Manager ✨   │  │
│  └─────────────────┘        │ - Proxy Handler ✨   │  │
│         ▲                   └──────────────────────┘  │
│         │                            │                 │
│         │                            ▼                 │
│   Tailscale Funnel            routes.json (volume)    │
│   (Public access)                                      │
└─────────────────────────────────────────────────────────┘

Development (Standalone):
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  ┌──────────────────────┐                              │
│  │ app (Flask)          │                              │
│  │ localhost:8000       │                              │
│  │                      │                              │
│  │ - Route Manager ✨   │───▶ routes.json (local)      │
│  │ - Proxy Handler ✨   │                              │
│  │ (Dev auth bypass)    │                              │
│  └──────────────────────┘                              │
│                                                         │
│  Note: No OAuth2 proxy in standalone mode              │
└─────────────────────────────────────────────────────────┘
```

**Key Points**:
- ✅ Route Manager is **integrated into the Flask app** - not a separate container
- ✅ Same Python code runs in both Docker and standalone modes
- ✅ No new Dockerfile needed - uses existing `app/Dockerfile`
- ✅ Only `docker-compose.yml` needs a volume mount for `routes.json`

---

## 🎯 Phase 1: Backend Foundation (4-6 hours)

### Step 1.0: Backup & Remove Existing App
**Time**: 10 minutes

**Tasks**:
- [ ] Backup existing `app/` directory
- [ ] Commit current state to git
- [ ] Remove old app directory
- [ ] Create fresh app directory structure

**Commands**:
```powershell
# 1. Backup current state to git
git status
git add .
git commit -m "chore: Backup before rebuilding app with route manager"

# 2. Create feature branch (recommended)
git checkout -b feature/route-manager

# 3. Create backup of existing app folder
Copy-Item -Path "app" -Destination "app_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')" -Recurse

# 4. Remove existing app directory
Remove-Item -Path "app" -Recurse -Force

# 5. Create fresh app directory structure
New-Item -Path "app" -ItemType Directory
New-Item -Path "app/static" -ItemType Directory
New-Item -Path "app/static/css" -ItemType Directory
New-Item -Path "app/static/js" -ItemType Directory
New-Item -Path "app/templates" -ItemType Directory
```

**Important Notes**:
- ⚠️ **We ARE removing the existing `app/` directory** - Complete fresh rebuild!
- ✅ The old app is safely backed up (in `app_backup_*` folder AND in git)
- ✅ We're rebuilding from scratch with route manager built-in from the start
- ✅ All existing functionality will be re-implemented in the new app
- ✅ If something goes wrong, restore from `app_backup_*` folder or `git checkout main`
- 🎯 **Clean slate approach** - Better architecture, no legacy code

**What We're Building**:
```
Existing Features (Re-implemented from scratch):
✅ Google OAuth authentication integration
✅ Email authorization system
✅ Comprehensive access logging
✅ Health check endpoints
✅ Rate limiting
✅ All standard routes (/health, /whoami, /headers, /logs)
✅ Unauthorized & 404 error pages
✅ Error handling & monitoring

New Features (Built-in from the start):
✨ Route management UI (/admin)
✨ Route API endpoints (/api/routes/*)
✨ Dynamic proxy handler (/<custom_path>)
✨ TinyDB storage (routes.json)
✨ Health monitoring for routes
✨ Glassmorphism UI design
```

**Files Impact**:
```
�️ Removed (Old app directory deleted):
   app/                        - Entire directory removed

💾 Backed Up:
   app_backup_YYYYMMDD_HHMMSS/ - Complete backup of old app
   git history                 - Can restore with 'git checkout main'

✨ Created (All brand new files):
   app/
   ├── app.py                  - Main Flask app (rebuilt with routes)
   ├── routes_db.py            - TinyDB route manager
   ├── proxy_handler.py        - Proxy request handler
   ├── requirements.txt        - All dependencies
   ├── requirements-dev.txt    - Dev/test dependencies
   ├── Dockerfile              - Same as before
   ├── test_app.py             - Unit tests
   ├── test_routes_db.py       - Route manager tests
   ├── test_proxy_handler.py   - Proxy handler tests
   ├── static/
   │   ├── css/
   │   │   ├── style.css       - Main styles (re-created)
   │   │   └── admin.css       - Admin UI styles (new)
   │   └── js/
   │       ├── app.js          - Main JS (re-created)
   │       └── admin.js        - Admin UI logic (new)
   └── templates/
       ├── base.html           - Base template (re-created)
       ├── index.html          - Dashboard (rebuilt with routes)
       ├── admin.html          - Route management UI (new)
       ├── headers.html        - Headers debug (re-created)
       ├── logs.html           - Logs viewer (re-created)
       ├── health_page.html    - Health page (re-created)
       ├── unauthorized.html   - 403 page (re-created)
       └── 404.html            - 404 page (re-created)

🔒 Unchanged (Outside app directory):
   docker-compose.yml          - Will be updated to add routes.json volume
   .env                        - No changes
   emails.txt                  - No changes
   All other project files     - No changes
```

---

### Step 1.1: Create Dependencies Files
**Time**: 15 minutes

**Tasks**:
- [ ] Create `app/requirements.txt` - All runtime dependencies
- [ ] Create `app/requirements-dev.txt` - Development/testing dependencies
- [ ] Copy `app/Dockerfile` from backup (unchanged)

**Files to Create**:
- `app/requirements.txt`
- `app/requirements-dev.txt`
- `app/Dockerfile` (copy from backup)

**Content for `requirements.txt`**:
```txt
# Core Flask dependencies
Flask>=3.0.0
Werkzeug>=3.0.0

# Rate limiting and security
Flask-Limiter>=3.5.0

# Route management
tinydb>=4.8.0           # Database for route storage
validators>=0.22.0      # IP and URL validation
requests>=2.31.0        # For proxy requests

# Utilities
python-dateutil>=2.8.2
```

**Content for `requirements-dev.txt`**:
```txt
-r requirements.txt     # Include all production dependencies

# Testing
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-flask>=1.2.0

# Code quality
flake8>=6.1.0
black>=23.7.0
```

**Commands to Run**:
```powershell
# Copy Dockerfile from backup (it doesn't need changes)
Copy-Item -Path "app_backup_*/Dockerfile" -Destination "app/Dockerfile"

# Create requirements files (create the files with content above)
# Then install dependencies for local testing
cd app
pip install -r requirements-dev.txt
```

---

### Step 1.2: Create TinyDB Route Manager
**Time**: 2-3 hours

**Tasks**:
- [ ] Create `app/routes_db.py` - TinyDB wrapper class
- [ ] Implement CRUD operations (Create, Read, Update, Delete)
- [ ] Add validation logic (IP validation, path sanitization)
- [ ] Add security checks (SSRF protection, private IP validation)

**Files to Create**:
- `app/routes_db.py`

**What to Implement**:
```python
class RouteManager:
    - __init__(db_path)
    - add_route(path, name, target_ip, target_port, protocol, ...)
    - get_all_routes(enabled_only)
    - get_route_by_path(path)
    - get_route_by_id(route_id)
    - update_route(route_id, updates)
    - delete_route(route_id)
    - toggle_route(route_id)
    - search_routes(query)
    - validate_ip(ip) - SSRF protection
    - validate_path(path) - Sanitization
```

**Key Features**:
- ✅ IP validation (only private IPs: 192.168.x, 10.x, 172.16-31.x)
- ✅ Block metadata endpoints (169.254.169.254)
- ✅ Path sanitization (start with /, alphanumeric + dash/underscore)
- ✅ Port range validation (1-65535)
- ✅ Unique path enforcement

---

### Step 1.3: Create Proxy Handler
**Time**: 1-2 hours

**Tasks**:
- [ ] Create `app/proxy_handler.py` - Handle proxy requests
- [ ] Implement request forwarding logic
- [ ] Preserve headers (X-Forwarded-For, etc.)
- [ ] Handle errors gracefully (503 if service down)

**Files to Create**:
- `app/proxy_handler.py`

**What to Implement**:
```python
class ProxyHandler:
    - __init__(route_manager)
    - proxy_request(path, request) - Main proxy logic
    - forward_request(target_url, method, headers, data)
    - build_target_url(route, request_path)
    - handle_proxy_error(error, route)
    - preserve_headers(original_headers)
```

**Key Features**:
- ✅ Forward GET, POST, PUT, DELETE, PATCH requests
- ✅ Stream large responses
- ✅ Preserve authentication headers from OAuth2 proxy
- ✅ Add X-Forwarded-* headers
- ✅ Timeout handling (configurable per route)

---

### Step 1.4: Add API Endpoints to Flask App
**Time**: 1-2 hours

**Tasks**:
- [ ] Modify `app/app.py` - Add route management API
- [ ] Add REST API endpoints for CRUD operations
- [ ] Add dynamic proxy catch-all route
- [ ] Update authorization checks

**Files to Modify**:
- `app/app.py`

**Endpoints to Add**:
```python
# Route Management API
GET    /api/routes              # Get all routes
POST   /api/routes              # Create new route
GET    /api/routes/<id>         # Get single route
PUT    /api/routes/<id>         # Update route
DELETE /api/routes/<id>         # Delete route
POST   /api/routes/<id>/test    # Test route connectivity
POST   /api/routes/<id>/toggle  # Enable/disable route

# Admin UI
GET    /admin                   # Route management page

# Dynamic Proxy (catch-all)
@app.route('/<path:proxy_path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def dynamic_proxy(proxy_path):
    # Look up route and proxy request
```

**Integration Points**:
- ✅ Initialize RouteManager on app startup
- ✅ Initialize ProxyHandler with RouteManager
- ✅ Skip auth check for proxy routes (already authed by OAuth2)
- ✅ Log proxy requests for monitoring

---

### Step 1.5: Update Docker Configuration
**Time**: 30 minutes

**Tasks**:
- [ ] Update `docker-compose.yml` - Add volume for routes.json
- [ ] Test Docker build and volume mounting
- [ ] Verify routes persist across container restarts

**Files to Modify**:
- `docker-compose.yml`

**What to Add**:
```yaml
services:
  app:
    volumes:
      - ./emails.txt:/app/emails.txt:ro
      - ./routes.json:/app/routes.json      # Add this line
    environment:
      - ROUTES_DB_PATH=/app/routes.json     # Add this line
```

**Important Notes**:
- ⚠️ **No changes needed to `app/Dockerfile`** - The route manager runs as part of the existing Flask app
- ✅ The existing Dockerfile already installs Python dependencies from `requirements.txt`
- ✅ Only `docker-compose.yml` needs updating (to add the routes.json volume)
- ✅ Same Docker container, just enhanced functionality

**Testing**:
```powershell
# Build and start (Docker mode)
docker-compose up -d --build

# Check routes.json is created
docker-compose exec app ls -la /app/routes.json

# Add a test route via API
# Restart container
docker-compose restart app

# Verify route still exists

# Test standalone mode (optional)
docker-compose down
cd app
python app.py
# Access at http://localhost:8000
```

---

## 🎨 Phase 2: Frontend - Admin UI (4-6 hours)

### Step 2.1: Create Admin Page HTML
**Time**: 2 hours

**Tasks**:
- [ ] Create `app/templates/admin.html` - Route management page
- [ ] Add route table with status indicators
- [ ] Add "Add Route" button and modal
- [ ] Add edit/delete actions per route

**Files to Create**:
- `app/templates/admin.html`

**Structure**:
```html
<!DOCTYPE html>
<html>
<head>
    <!-- Font Awesome for icons -->
    <!-- Link to admin.css -->
</head>
<body>
    <!-- Animated background (like example_web_ui) -->
    <div class="background-container">
        <div class="particles">...</div>
    </div>
    
    <!-- Navigation bar -->
    <nav class="navbar">
        <h1>Route Manager</h1>
        <div class="nav-actions">
            <button id="theme-toggle">🌙</button>
            <a href="/">Dashboard</a>
        </div>
    </nav>
    
    <!-- Main content -->
    <div class="container">
        <!-- Statistics cards -->
        <div class="stats-cards">
            <div class="stat-card">
                <h3 id="total-routes">0</h3>
                <p>Total Routes</p>
            </div>
            <div class="stat-card">
                <h3 id="online-routes">0</h3>
                <p>Online</p>
            </div>
            <div class="stat-card">
                <h3 id="offline-routes">0</h3>
                <p>Offline</p>
            </div>
        </div>
        
        <!-- Actions bar -->
        <div class="actions-bar">
            <button id="add-route-btn" class="btn-primary">
                <i class="fas fa-plus"></i> Add Route
            </button>
            <button id="refresh-btn" class="btn-secondary">
                <i class="fas fa-sync"></i> Refresh
            </button>
            <input type="text" id="search-input" placeholder="Search routes...">
        </div>
        
        <!-- Routes table -->
        <div class="routes-table-container">
            <table class="routes-table" id="routes-table">
                <thead>
                    <tr>
                        <th>Status</th>
                        <th>Path</th>
                        <th>Name</th>
                        <th>Target</th>
                        <th>Protocol</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="routes-tbody">
                    <!-- Populated by JavaScript -->
                </tbody>
            </table>
        </div>
    </div>
    
    <!-- Add/Edit Route Modal -->
    <div id="route-modal" class="modal">
        <div class="modal-content">
            <h2 id="modal-title">Add New Route</h2>
            <form id="route-form">
                <div class="form-group">
                    <label>Route Path *</label>
                    <input type="text" id="route-path" placeholder="/jellyfin">
                    <small>Must start with /. Use lowercase, numbers, -, _</small>
                </div>
                
                <div class="form-group">
                    <label>Service Name *</label>
                    <input type="text" id="route-name" placeholder="Jellyfin Media Server">
                </div>
                
                <div class="form-row">
                    <div class="form-group">
                        <label>Target IP *</label>
                        <input type="text" id="target-ip" placeholder="192.168.1.100">
                    </div>
                    <div class="form-group">
                        <label>Port *</label>
                        <input type="number" id="target-port" placeholder="8096" min="1" max="65535">
                    </div>
                </div>
                
                <div class="form-group">
                    <label>Protocol</label>
                    <div class="radio-group">
                        <label><input type="radio" name="protocol" value="http" checked> HTTP</label>
                        <label><input type="radio" name="protocol" value="https"> HTTPS</label>
                    </div>
                </div>
                
                <details class="advanced-settings">
                    <summary>Advanced Settings</summary>
                    <div class="form-group">
                        <label><input type="checkbox" id="health-check" checked> Enable Health Check</label>
                    </div>
                    <div class="form-group">
                        <label>Timeout (seconds)</label>
                        <input type="number" id="timeout" value="30" min="5" max="300">
                    </div>
                </details>
                
                <div class="modal-actions">
                    <button type="button" id="test-connection" class="btn-secondary">Test Connection</button>
                    <button type="button" id="cancel-btn" class="btn-secondary">Cancel</button>
                    <button type="submit" class="btn-primary">Save Route</button>
                </div>
            </form>
        </div>
    </div>
    
    <!-- Delete Confirmation Modal -->
    <div id="delete-modal" class="modal">
        <div class="modal-content">
            <h2>Delete Route?</h2>
            <p>Are you sure you want to delete <strong id="delete-route-name"></strong>?</p>
            <div class="modal-actions">
                <button id="cancel-delete" class="btn-secondary">Cancel</button>
                <button id="confirm-delete" class="btn-danger">Delete</button>
            </div>
        </div>
    </div>
    
    <script src="/static/js/admin.js"></script>
</body>
</html>
```

---

### Step 2.2: Create Admin CSS
**Time**: 2-3 hours

**Tasks**:
- [ ] Create `app/static/css/admin.css` - Glassmorphism styling
- [ ] Implement gradient backgrounds with animations
- [ ] Add card-based layouts with blur effects
- [ ] Create smooth transitions and hover effects
- [ ] Implement light/dark mode with CSS variables

**Files to Create**:
- `app/static/css/admin.css`

**Key Styles**:
```css
/* Base styles with CSS variables */
:root {
    --gradient-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    --card-bg: rgba(255, 255, 255, 0.9);
    --card-border: rgba(0, 0, 0, 0.1);
    --text-primary: #1a202c;
    --text-secondary: #4a5568;
    --status-online: #48bb78;
    --status-offline: #f56565;
    --status-slow: #ecc94b;
}

[data-theme="dark"] {
    --card-bg: rgba(30, 30, 40, 0.9);
    --card-border: rgba(255, 255, 255, 0.1);
    --text-primary: #f7fafc;
    --text-secondary: #cbd5e0;
}

/* Animated background with particles */
.background-container { ... }
.particles { ... }
.particle { ... }

/* Glassmorphism cards */
.card {
    background: var(--card-bg);
    backdrop-filter: blur(10px);
    border: 1px solid var(--card-border);
    border-radius: 12px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

/* Gradient buttons */
.btn-primary {
    background: var(--gradient-primary);
    color: white;
    transition: all 0.3s ease;
}

.btn-primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
}

/* Status indicators */
.status-online { color: var(--status-online); }
.status-offline { color: var(--status-offline); }
.status-slow { color: var(--status-slow); }

/* Modal with backdrop blur */
.modal {
    backdrop-filter: blur(5px);
    background: rgba(0, 0, 0, 0.5);
}

/* Smooth animations */
@keyframes fadeIn { ... }
@keyframes slideUp { ... }
@keyframes float { ... }
```

**Design Elements**:
- ✅ Floating particle animations
- ✅ Gradient backgrounds
- ✅ Glass morphism cards
- ✅ Smooth hover effects
- ✅ Loading spinners
- ✅ Toast notifications

---

### Step 2.3: Create Admin JavaScript
**Time**: 2-3 hours

**Tasks**:
- [ ] Create `app/static/js/admin.js` - Frontend logic
- [ ] Implement API calls (fetch routes, add, edit, delete)
- [ ] Handle form validation
- [ ] Update UI dynamically
- [ ] Add toast notifications for feedback

**Files to Create**:
- `app/static/js/admin.js`

**Key Functions**:
```javascript
// State management
let routes = [];
let currentEditRoute = null;

// API calls
async function fetchRoutes() { ... }
async function createRoute(routeData) { ... }
async function updateRoute(id, routeData) { ... }
async function deleteRoute(id) { ... }
async function testRoute(id) { ... }
async function toggleRoute(id) { ... }

// UI updates
function renderRoutes(routes) { ... }
function renderStatsCards(routes) { ... }
function showModal(route = null) { ... }
function hideModal() { ... }
function showToast(message, type) { ... }

// Form handling
function validateForm() { ... }
function getFormData() { ... }
function populateForm(route) { ... }
function resetForm() { ... }

// Theme toggle
function toggleTheme() { ... }
function loadTheme() { ... }

// Search/filter
function filterRoutes(query) { ... }

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
    loadTheme();
    fetchRoutes();
    setupEventListeners();
});
```

**Features**:
- ✅ Real-time route updates
- ✅ Client-side form validation
- ✅ Toast notifications (success/error)
- ✅ Search and filter
- ✅ Confirmation dialogs
- ✅ Loading states

---

### Step 2.4: Update Main Dashboard
**Time**: 1 hour

**Tasks**:
- [ ] Update `app/templates/index.html` - Show available routes
- [ ] Add service cards for each enabled route
- [ ] Add "Manage Routes" button for authenticated users
- [ ] Style to match glassmorphism design

**Files to Modify**:
- `app/templates/index.html`
- `app/static/css/style.css`

**What to Add**:
```html
<!-- Services Section -->
<div class="services-section">
    <h2>Your Available Services</h2>
    <div class="services-grid" id="services-grid">
        <!-- Populated by JavaScript -->
    </div>
    <a href="/admin" class="btn-primary">
        <i class="fas fa-cog"></i> Manage Routes
    </a>
</div>

<script>
// Fetch and display enabled routes
fetch('/api/routes')
    .then(res => res.json())
    .then(routes => {
        const enabledRoutes = routes.filter(r => r.enabled);
        renderServiceCards(enabledRoutes);
    });
</script>
```

---

## 🧪 Phase 3: Testing & Validation (2-3 hours)

### Step 3.1: Write Unit Tests
**Time**: 1-2 hours

**Tasks**:
- [ ] Create `app/test_routes_db.py` - Test RouteManager
- [ ] Create `app/test_proxy_handler.py` - Test ProxyHandler
- [ ] Create `app/test_api.py` - Test Flask endpoints

**Files to Create**:
- `app/test_routes_db.py`
- `app/test_proxy_handler.py`
- `app/test_api.py`

**Tests to Write**:
```python
# test_routes_db.py
- test_add_route_success()
- test_add_duplicate_route_fails()
- test_validate_ip_private_only()
- test_validate_ip_blocks_metadata()
- test_validate_path_sanitization()
- test_update_route()
- test_delete_route()
- test_search_routes()

# test_proxy_handler.py
- test_proxy_request_success()
- test_proxy_request_service_down()
- test_proxy_preserves_headers()
- test_proxy_timeout_handling()

# test_api.py
- test_get_routes()
- test_create_route_valid()
- test_create_route_invalid_ip()
- test_update_route()
- test_delete_route()
- test_proxy_route_forwards_correctly()
```

**Run Tests**:
```powershell
cd app
pytest test_routes_db.py -v
pytest test_proxy_handler.py -v
pytest test_api.py -v
pytest --cov=. --cov-report=html
```

---

### Step 3.2: Manual Testing Checklist
**Time**: 1 hour

**Tasks**:
- [ ] Test all CRUD operations via UI
- [ ] Test proxy functionality with real service
- [ ] Test error handling (invalid IPs, offline services)
- [ ] Test persistence (routes survive restart)
- [ ] Test theme toggle and responsive design

**Manual Test Cases**:

```
✅ Route Management
- [ ] Add valid route via UI
- [ ] Try to add duplicate route (should fail with error)
- [ ] Try to add invalid IP (should fail)
- [ ] Edit existing route
- [ ] Delete route with confirmation
- [ ] Toggle route enabled/disabled
- [ ] Search/filter routes

✅ Proxy Functionality
- [ ] Access route via browser (e.g., /jellyfin)
- [ ] Verify request reaches target service
- [ ] Check headers are preserved
- [ ] Test with different HTTP methods (GET, POST)
- [ ] Test with offline service (should show 503)

✅ UI/UX
- [ ] Theme toggle works (light/dark)
- [ ] Animations are smooth
- [ ] Responsive on mobile
- [ ] Toast notifications appear
- [ ] Loading states display correctly
- [ ] Forms validate before submit

✅ Persistence
- [ ] Add route
- [ ] Restart Docker container
- [ ] Verify route still exists
- [ ] Verify proxy still works

✅ Security
- [ ] Try to add localhost (should fail)
- [ ] Try to add 127.0.0.1 (should fail)
- [ ] Try to add metadata IP (should fail)
- [ ] Try to add public IP (should fail)
- [ ] Verify only authenticated users can access /admin
```

---

## 🚀 Phase 4: Polish & Production Ready (3-4 hours)

### Step 4.1: Health Check System
**Time**: 1 hour

**Tasks**:
- [ ] Add background health check worker
- [ ] Update route status in database
- [ ] Display real-time status in UI
- [ ] Add status refresh endpoint

**Files to Modify**:
- `app/routes_db.py` - Add status field
- `app/app.py` - Add health check scheduler
- `app/static/js/admin.js` - Auto-refresh status

**Implementation**:
```python
# Background health check (every 5 minutes)
import threading
import time
import requests

def health_check_worker(route_manager):
    while True:
        routes = route_manager.get_all_routes(enabled_only=True)
        for route in routes:
            try:
                url = f"{route['protocol']}://{route['target_ip']}:{route['target_port']}"
                response = requests.get(url, timeout=5)
                status = 'online' if response.status_code < 500 else 'degraded'
            except:
                status = 'offline'
            
            route_manager.update_route(route['id'], {'status': status})
        
        time.sleep(300)  # 5 minutes

# Start worker thread
health_thread = threading.Thread(target=health_check_worker, args=(route_manager,), daemon=True)
health_thread.start()
```

---

### Step 4.2: Error Handling & Logging
**Time**: 1 hour

**Tasks**:
- [ ] Add comprehensive error messages
- [ ] Log all proxy requests
- [ ] Log route modifications (who added/changed what)
- [ ] Add error page for failed proxies

**Files to Modify**:
- `app/proxy_handler.py` - Enhanced logging
- `app/templates/proxy_error.html` - Error page

**Logging Format**:
```python
logger.info(f"ROUTE_ADD - User: {email} | Path: {path} | Target: {ip}:{port}")
logger.info(f"ROUTE_UPDATE - User: {email} | Route: {route_id} | Changes: {updates}")
logger.info(f"ROUTE_DELETE - User: {email} | Route: {route_id}")
logger.info(f"PROXY_REQUEST - Path: {path} | Target: {target} | Status: {status} | Duration: {duration}ms")
logger.error(f"PROXY_ERROR - Path: {path} | Error: {error} | Target: {target}")
```

---

### Step 4.3: Documentation
**Time**: 1-2 hours

**Tasks**:
- [ ] Update main README.md with route management docs
- [ ] Create USER-GUIDE.md for non-technical users
- [ ] Add screenshots to documentation
- [ ] Document API endpoints

**Files to Create/Modify**:
- `README.md` - Update features section
- `USER-GUIDE.md` - Step-by-step guide
- `API-DOCUMENTATION.md` - API reference
- `docs/screenshots/` - Add UI screenshots

**Documentation Structure**:
```markdown
# USER-GUIDE.md

## Quick Start
1. Login to your dashboard
2. Click "Manage Routes"
3. Click "Add Route"
4. Fill in service details
5. Save and test

## Adding Your First Route
- Step-by-step with screenshots
- Example: Adding Jellyfin
- Example: Adding Plex

## Troubleshooting
- Service shows offline
- Can't access route
- Invalid IP error
```

---

### Step 4.4: Performance Optimization
**Time**: 1 hour

**Tasks**:
- [ ] Add route caching (reduce DB lookups)
- [ ] Optimize TinyDB queries
- [ ] Add compression for proxy responses
- [ ] Minify CSS/JS for production

**Optimizations**:
```python
# Route cache
from functools import lru_cache
from threading import Lock

class RouteCache:
    def __init__(self, route_manager):
        self.route_manager = route_manager
        self.cache = {}
        self.lock = Lock()
    
    def get_route(self, path):
        with self.lock:
            if path not in self.cache:
                route = self.route_manager.get_route_by_path(path)
                self.cache[path] = route
            return self.cache[path]
    
    def invalidate(self):
        with self.lock:
            self.cache.clear()

# Use cache in proxy handler
route_cache = RouteCache(route_manager)
```

---

## 📦 Phase 5: Deployment & Final Touches (1-2 hours)

### Step 5.1: Docker Build & Test
**Time**: 30 minutes

**Tasks**:
- [ ] Build Docker image with route manager
- [ ] Test all functionality in Docker
- [ ] Verify volumes work correctly
- [ ] Test container restart persistence
- [ ] Test standalone mode (optional)

**Docker Deployment (Production)**:
```powershell
# Rebuild and start with docker-compose
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Check logs
docker-compose logs -f app

# Test routes persist
docker-compose exec app cat /app/routes.json

# Restart and verify persistence
docker-compose restart app
docker-compose exec app cat /app/routes.json

# Access the app
# https://your-tailscale-url.ts.net
```

**Standalone Deployment (Development/Testing)**:
```powershell
# Install dependencies
cd app
pip install -r requirements.txt

# Set environment variables
$env:FLASK_ENV="development"
$env:EMAILS_FILE_PATH="../emails.txt"
$env:ROUTES_DB_PATH="./routes.json"
$env:LOG_FILE_PATH="./access.log"

# Run Flask app
python app.py

# Access at http://localhost:8000
# Note: OAuth2 proxy won't be available in standalone mode
# You'll need to test with development auth bypass
```

**Testing Both Modes**:
```powershell
# 1. Test Docker mode (full production setup)
docker-compose up -d
# Access via Tailscale URL with OAuth

# 2. Test standalone mode (development)
docker-compose down
cd app
python app.py
# Access via localhost:8000
```

---

### Step 5.2: Update CHANGELOG
**Time**: 15 minutes

**Tasks**:
- [ ] Update CHANGELOG.md with new features
- [ ] Document breaking changes (if any)
- [ ] Add migration notes

**Files to Modify**:
- `CHANGELOG.md`

**Entry**:
```markdown
## [2.1.0] - 2025-10-03

### Added
- 🎉 **Reverse Proxy Route Manager** - Dynamic route configuration
- ✨ Beautiful glassmorphism admin UI with animations
- 🗃️ TinyDB-based route storage with persistence
- 🔄 Real-time health checks and status indicators
- 🌓 Light/dark mode toggle
- 📊 Route statistics and monitoring
- 🔍 Search and filter routes
- 🔐 IP validation and SSRF protection

### Changed
- Updated Flask app to handle dynamic proxy routes
- Enhanced logging for proxy requests

### Security
- Added private IP validation
- Blocked access to metadata endpoints
- Sanitized path inputs
```

---

### Step 5.3: Git Commit & Push
**Time**: 15 minutes

**Tasks**:
- [ ] Stage all changes
- [ ] Commit with descriptive message
- [ ] Push to GitHub
- [ ] Create release tag (optional)

**Commands**:
```powershell
git status
git add .
git commit -m "feat: Add reverse proxy route manager with glassmorphism UI

- Implement TinyDB route storage
- Add route management UI with CRUD operations
- Implement dynamic proxy handler
- Add health checks and status monitoring
- Create beautiful glassmorphism design
- Add comprehensive tests
- Update documentation"

git push origin main

# Optional: Create release
git tag -a v2.1.0 -m "Release v2.1.0 - Route Manager"
git push origin v2.1.0
```

---

## ✅ Completion Checklist

### Backend ✓
- [ ] TinyDB RouteManager implemented
- [ ] ProxyHandler implemented
- [ ] API endpoints added to Flask
- [ ] Docker configuration updated
- [ ] Volume persistence tested

### Frontend ✓
- [ ] Admin HTML page created
- [ ] Glassmorphism CSS implemented
- [ ] JavaScript API integration complete
- [ ] Main dashboard updated
- [ ] Theme toggle working

### Testing ✓
- [ ] Unit tests written and passing
- [ ] Manual testing completed
- [ ] Docker testing verified
- [ ] Security validation done

### Polish ✓
- [ ] Health checks implemented
- [ ] Error handling comprehensive
- [ ] Documentation updated
- [ ] Performance optimized

### Deployment ✓
- [ ] Docker build successful
- [ ] All features tested in production
- [ ] CHANGELOG updated
- [ ] Git committed and pushed

---

## 🎯 Success Criteria

Before marking as complete, verify:

1. ✅ **Functionality**
   - Users can add/edit/delete routes via UI
   - Proxy requests work correctly
   - Routes persist across restarts
   - Health checks display accurate status

2. ✅ **Security**
   - Only private IPs accepted
   - SSRF protection working
   - Authentication required for admin panel
   - Path sanitization prevents exploits

3. ✅ **User Experience**
   - UI is beautiful and intuitive
   - Animations are smooth
   - Theme toggle works
   - Responsive on mobile
   - Error messages are clear

4. ✅ **Performance**
   - Proxy overhead < 100ms
   - UI loads quickly
   - No memory leaks
   - Routes cache efficiently

5. ✅ **Maintainability**
   - Code is well-documented
   - Tests provide good coverage
   - Logs are informative
   - Documentation is clear

---

## 📚 Additional Resources

### Helpful Links
- TinyDB Documentation: https://tinydb.readthedocs.io/
- Flask Proxy Tutorial: https://flask.palletsprojects.com/
- Glassmorphism CSS Guide: https://css-tricks.com/glassmorphism/
- Font Awesome Icons: https://fontawesome.com/icons

### Reference Files
- `REVERSE-PROXY-ROUTES.md` - Original brainstorm document
- `example_web_ui/` - UI design inspiration
- Current `app/app.py` - Existing Flask structure

---

## 🆘 Troubleshooting

### Common Issues

**Issue**: Routes not persisting after restart
- **Solution**: Check Docker volume mount in `docker-compose.yml`
- **Verify**: `docker-compose exec app ls -la /app/routes.json`

**Issue**: Proxy returns 502 Bad Gateway
- **Solution**: Verify target service is running and accessible
- **Check**: Test URL directly from container: `docker-compose exec app curl http://target-ip:port`

**Issue**: Can't add route - "Invalid IP"
- **Solution**: Only private IPs allowed (192.168.x, 10.x, 172.16-31.x)
- **Fix**: Use private network IP, not public or localhost

**Issue**: UI not loading styles
- **Solution**: Check Flask static file serving
- **Verify**: Browser console for 404 errors

**Issue**: Theme toggle not working
- **Solution**: Check localStorage permissions
- **Fix**: Clear browser cache and cookies

---

## 📝 Notes

- **Estimated Total Time**: 15-20 hours (spread over 2-3 days)
- **Complexity**: Medium - Requires backend + frontend + Docker knowledge
- **Prerequisites**: Basic understanding of Flask, JavaScript, Docker
- **Testing**: Allocate extra time for thorough testing
- **Polish**: UI polish can be ongoing after MVP is functional

---

**Last Updated**: October 3, 2025  
**Status**: 📋 Ready to Implement  
**Next Action**: Start with Phase 1, Step 1.1 - Install Dependencies

🦈 **Let's build this!**
