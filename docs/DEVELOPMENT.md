<a id="development-top"></a>

# Local Development

> Guide for developing and testing Shark-no-Ninsho-Mon locally.

[![Back to README](https://img.shields.io/badge/←_Back_to-README-blue?style=for-the-badge)](../README.md)

---

## Table of Contents

- [Development environment setup](#development-environment-setup)
- [Running locally](#running-locally)
- [Development mode](#development-mode)
- [Testing](#testing)
- [Code structure](#code-structure)
- [Adding features](#adding-features)
- [Debugging](#debugging)
- [Contributing](#contributing)

---

## Development environment setup

### Prerequisites

- Python 3.11+ (tested on 3.11.x)
- Docker Engine 24+ and Docker Compose v2.20+ (for testing full stack)
- Git
- Code editor (VS Code recommended)

### Clone repository

```powershell
# Windows PowerShell
git clone https://github.com/HaiNick/Shark-no-Ninsho-Mon
cd Shark-no-Ninsho-Mon
```

```bash
# Linux / macOS
git clone https://github.com/HaiNick/Shark-no-Ninsho-Mon
cd Shark-no-Ninsho-Mon
```

### Create virtual environment

```powershell
# Windows PowerShell
python -m venv .venv
.venv\Scripts\Activate.ps1

# Upgrade pip
python -m pip install --upgrade pip
```

```bash
# Linux / macOS
python -m venv .venv
source .venv/bin/activate

# Upgrade pip
python -m pip install --upgrade pip
```

### Install dependencies

```powershell
pip install -r app\requirements.txt
```

```bash
# Linux / macOS
pip install -r app/requirements.txt
```

### Configure environment

```powershell
# Copy template
Copy-Item .env.template .env

# Set development mode
(Get-Content .env) -replace 'DEV_MODE=false', 'DEV_MODE=true' | Set-Content .env
```

```bash
# Linux / macOS
cp .env.template .env
sed -i 's/DEV_MODE=false/DEV_MODE=true/' .env
```

<p align="right">(<a href="#development-top">back to top</a>)</p>

---

## Running locally

### Flask development server

The development server runs Flask without Docker, OAuth2 Proxy, or Caddy:

```powershell
# Windows PowerShell
cd app
python dev.py
```

```bash
# Linux / macOS
cd app
python dev.py
```

**What happens**:
- Flask runs on http://localhost:8000
- DEV_MODE automatically adds `dev@localhost` to email allow list
- No OAuth authentication required
- Direct access to all routes and API endpoints
- Auto-reload on file changes (via Flask debug mode)

**Access**:
- Dashboard: http://localhost:8000/dashboard
- API: http://localhost:8000/api/routes
- Health: http://localhost:8000/health

### Full stack (Docker)

For testing complete integration with OAuth2 Proxy and Caddy:

```powershell
# Ensure DEV_MODE=false in .env
docker compose up -d --build

# View logs
docker compose logs -f
```

**Access** (requires OAuth):
- Via Tailscale Funnel: https://your-hostname.ts.net

<p align="right">(<a href="#development-top">back to top</a>)</p>

---

## Development mode

### What is DEV_MODE?

Development mode bypasses OAuth2 authentication for local testing:

```bash
# In .env
DEV_MODE=true
```

**When enabled**:
- All requests treated as authenticated
- Default user: `dev@localhost`
- `X-Forwarded-Email` header automatically injected
- No Google OAuth required
- Health checks disabled by default (can be overridden)

**Security warning**: ⚠️ **NEVER enable DEV_MODE in production**

### Starting dev server with DEV_MODE

```powershell
# app/dev.py automatically:
# 1. Sets DEV_MODE=true
# 2. Adds dev@localhost to emails.txt
# 3. Disables health checks (unless HEALTH_CHECK_ENABLED=true in .env)
# 4. Runs Flask with debug=True and auto-reload

python app/dev.py
```

### Testing authenticated requests

In DEV_MODE, the `X-Forwarded-Email` header is automatically set to `dev@localhost`:

```powershell
# All these work without authentication
curl http://localhost:8000/dashboard
curl http://localhost:8000/api/routes
curl -Method POST http://localhost:8000/api/routes -ContentType "application/json" `
     -Body '{"path":"/test","target_ip":"localhost","target_port":8080,"protocol":"http"}'
```

### Simulating different users

Override the email header for testing:

```powershell
curl -Headers @{"X-Forwarded-Email"="testuser@example.com"} `
     http://localhost:8000/api/routes
```

Note: In DEV_MODE, any email is accepted (allow list is bypassed).

<p align="right">(<a href="#development-top">back to top</a>)</p>

---

## Testing

### Running tests

Tests are located in `app/test/`:

```powershell
# Windows PowerShell (from project root)
cd app
python -m pytest -q
```

```bash
# Linux / macOS
cd app
pytest -q
```

### Test files

- `test_app.py` - Flask application and API endpoints
- `test_routes_db.py` - TinyDB route manager
- `test_caddy_manager.py` - Caddy Admin API integration
- `test_classification.py` - Route classification logic

### Running specific tests

```powershell
# Single test file
pytest -q test/test_routes_db.py

# Single test function
pytest -q test/test_routes_db.py::test_add_route

# Verbose output
pytest -v test/
```

### Test coverage

```powershell
# Install pytest-cov if not already installed
pip install pytest-cov

# Run with coverage
pytest --cov=./ test/

# Generate HTML report
pytest --cov=./ --cov-report=html test/
# Open htmlcov/index.html
```

### Writing tests

Example test structure:

```python
# test/test_my_feature.py
import pytest
from routes_db import RouteManager

def test_my_feature():
    """Test description"""
    # Arrange
    rm = RouteManager(':memory:')  # In-memory DB
    
    # Act
    route_id = rm.add_route(
        path='/test',
        target_ip='localhost',
        target_port=8080,
        protocol='http'
    )
    
    # Assert
    assert route_id is not None
    route = rm.get_route(route_id)
    assert route['path'] == '/test'
```

<p align="right">(<a href="#development-top">back to top</a>)</p>

---

## Code structure

### Application architecture

```
app/
├── app.py                    # Flask application & routes
├── dev.py                    # Development server entry point
├── config.py                 # Configuration loader
├── routes_db.py              # TinyDB route manager
├── caddy_manager.py          # Caddy Admin API client
├── requirements.txt          # Python dependencies
├── Dockerfile                # Production container
├── test/                     # Unit tests
│   ├── test_app.py
│   ├── test_routes_db.py
│   ├── test_caddy_manager.py
│   └── test_classification.py
├── templates/                # Jinja2 HTML templates
│   ├── base.html
│   ├── index.html
│   ├── admin.html
│   ├── emails.html
│   └── ...
└── static/                   # CSS/JS assets
    ├── css/
    │   ├── shared.css
    │   ├── admin.css
    │   └── ...
    └── js/
        ├── admin.js
        ├── utils.js
        └── config.js
```

### Key modules

#### `app.py` - Flask Application

Main application with routes:

- `/` - Dashboard (requires auth)
- `/dashboard` - Route management UI
- `/api/routes` - REST API for routes
- `/health` - Health check endpoint
- `/emails` - Email allowlist management

#### `routes_db.py` - Route Manager

TinyDB wrapper for route CRUD operations:

```python
class RouteManager:
    def add_route(path, target_ip, target_port, protocol, **options)
    def get_route(route_id)
    def get_all_routes()
    def update_route(route_id, **fields)
    def delete_route(route_id)
    def toggle_route(route_id)
```

#### `caddy_manager.py` - Caddy Integration

Caddy Admin API client:

```python
class CaddyManager:
    def sync(routes)          # Sync routes to Caddy
    def get_config()          # Retrieve current config
    def reload()              # Reload Caddy config
```

#### `config.py` - Configuration

Centralized configuration loader:

```python
class Config:
    ROUTES_DB_PATH          # Route database location
    EMAILS_FILE             # Allowlist location
    HEALTH_CHECK_ENABLED    # Enable health checks
    HEALTH_CHECK_INTERVAL   # Health check interval
    UPSTREAM_SSL_VERIFY     # Verify upstream TLS
    DEV_MODE                # Development mode
    SECRET_KEY              # Flask session secret
```

<p align="right">(<a href="#development-top">back to top</a>)</p>

---

## Adding features

### Adding a new API endpoint

1. **Define route in `app.py`**:

```python
@app.route('/api/my-feature', methods=['POST'])
def my_feature():
    """My feature description"""
    # Get user email from OAuth2 Proxy
    user_email = request.headers.get('X-Forwarded-Email', 'dev@localhost')
    
    # Validate input
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400
    
    # Process request
    result = do_something(data)
    
    return jsonify({'success': True, 'result': result})
```

2. **Add frontend integration** (`static/js/admin.js`):

```javascript
async function myFeature(data) {
    const response = await fetch('/api/my-feature', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });
    return await response.json();
}
```

3. **Write tests** (`test/test_app.py`):

```python
def test_my_feature(client):
    """Test my feature endpoint"""
    response = client.post('/api/my-feature',
        json={'key': 'value'},
        headers={'X-Forwarded-Email': 'test@example.com'}
    )
    assert response.status_code == 200
    assert response.json['success'] is True
```

### Adding route configuration options

1. **Update route schema** in `routes_db.py`:

```python
def add_route(self, path, target_ip, target_port, protocol, my_option=None, **kwargs):
    route = {
        'path': path,
        'target_ip': target_ip,
        'target_port': target_port,
        'protocol': protocol,
        'my_option': my_option,  # New option
        'enabled': True,
        # ... other fields
    }
    return self.db.insert(route)
```

2. **Update Caddy sync logic** in `caddy_manager.py`:

```python
def _build_route_handler(self, route):
    handler = {
        # ... existing config
    }
    
    # Apply new option
    if route.get('my_option'):
        handler['my_option'] = route['my_option']
    
    return handler
```

3. **Update UI** in `templates/admin.html` and `static/js/admin.js`

### Adding a new page

1. **Create template** `templates/my_page.html`:

```html
{% extends "base.html" %}

{% block title %}My Page{% endblock %}

{% block content %}
<div class="container">
    <h1>My Page</h1>
    <!-- Your content -->
</div>
{% endblock %}
```

2. **Add route** in `app.py`:

```python
@app.route('/my-page')
def my_page():
    user_email = request.headers.get('X-Forwarded-Email')
    return render_template('my_page.html', user_email=user_email)
```

3. **Add navigation** in `templates/base.html`

<p align="right">(<a href="#development-top">back to top</a>)</p>

---

## Debugging

### Flask debugging

Enable debug mode in development:

```python
# app/dev.py already sets debug=True
app.run(host='0.0.0.0', port=8000, debug=True)
```

**Features**:
- Auto-reload on file changes
- Interactive debugger in browser
- Detailed error pages

### VS Code debugging

Create `.vscode/launch.json`:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Flask",
            "type": "python",
            "request": "launch",
            "module": "flask",
            "env": {
                "FLASK_APP": "app/app.py",
                "FLASK_ENV": "development",
                "DEV_MODE": "true"
            },
            "args": [
                "run",
                "--host=0.0.0.0",
                "--port=8000"
            ],
            "jinja": true
        }
    ]
}
```

### Logging

Add debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# In your code
app.logger.debug('Debug message')
app.logger.info('Info message')
app.logger.error('Error message')
```

### Docker debugging

```powershell
# View container logs
docker compose logs -f app

# Execute commands in container
docker compose exec app bash

# Inspect container
docker compose exec app python -c "from config import Config; print(Config.ROUTES_DB_PATH)"
```

### Database debugging

```powershell
# View routes.json content
Get-Content app\routes.json | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

```bash
# Linux / macOS
cat app/routes.json | jq
```

### Network debugging

```powershell
# Test Flask from container
docker compose exec caddy wget -O- http://app:8000/health

# Test Caddy Admin API from container
docker compose exec app curl http://caddy:2019/config/
```

<p align="right">(<a href="#development-top">back to top</a>)</p>

---

## Contributing

### Before you start

1. **Fork the repository** on GitHub
2. **Clone your fork**:
   ```powershell
   git clone https://github.com/YOUR-USERNAME/Shark-no-Ninsho-Mon
   cd Shark-no-Ninsho-Mon
   ```
3. **Create a branch**:
   ```powershell
   git checkout -b feature/my-feature
   ```

### Development workflow

1. **Make changes** in your branch
2. **Run tests**:
   ```powershell
   cd app
   pytest -q
   ```
3. **Test manually** with dev server:
   ```powershell
   python dev.py
   ```
4. **Test full stack**:
   ```powershell
   docker compose up -d --build
   docker compose logs -f
   ```

### Code style

- **Python**: Follow PEP 8 (use `black` or `autopep8`)
- **JavaScript**: Use consistent spacing and semicolons
- **HTML/CSS**: Indent with 2 spaces

**Recommended tools**:
```powershell
pip install black pylint mypy
black app/
pylint app/*.py
mypy app/
```

### Commit guidelines

- Use clear, descriptive commit messages
- Reference issue numbers: "Fix #123: Description"
- Keep commits atomic (one logical change per commit)

**Example**:
```powershell
git add app/routes_db.py test/test_routes_db.py
git commit -m "Add support for custom SNI in routes (#123)"
```

### Pull request checklist

- [ ] Code follows project style
- [ ] Tests added/updated and passing
- [ ] Documentation updated (if needed)
- [ ] Tested locally with dev server
- [ ] Tested with full Docker stack
- [ ] No merge conflicts with main branch

### Opening a pull request

1. **Push to your fork**:
   ```powershell
   git push origin feature/my-feature
   ```
2. **Open PR** on GitHub
3. **Describe changes**:
   - What problem does this solve?
   - How did you test it?
   - Any breaking changes?

<p align="right">(<a href="#development-top">back to top</a>)</p>

---

<div align="center">

[![Back to README](https://img.shields.io/badge/←_Back_to-README-blue?style=for-the-badge)](../README.md)

**Made with <3 for secure self-hosting**

</div>

<p align="right">(<a href="#development-top">back to top</a>)</p>
