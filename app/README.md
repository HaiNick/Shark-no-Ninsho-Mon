# App Development Guide

## Quick Start (Development Mode)

### 1. Setup Environment

```bash
# From project root (one level up)
cd ..
cp .env.template .env

# Edit .env and add:
# DEV_MODE=true

# Return to app directory
cd app
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the App

```bash
python app.py
```

The app will start at **http://localhost:8000** with authentication **bypassed** (DEV_MODE=true).

---

## Environment Variables (.env)

The `.env` file is located in the **project root** (one level up from app/).

See `../.env.template` for all configuration options.

**Key settings for development:**

```env
# Development Mode - bypasses OAuth2 authentication
DEV_MODE=true          # Set to false for production

# Flask Configuration
FLASK_ENV=development  # development or production
DEBUG=true             # Enable debug mode

# Server
PORT=8000
HOST=0.0.0.0

# Security
SECRET_KEY=your-secret-key

# File Paths
EMAILS_FILE_PATH=/app/emails.txt
LOG_FILE_PATH=/app/access.log
```

For full configuration reference, see `ENV.md` or `../.env.template`.

### Development vs Production

**Development (.env):**
```env
DEV_MODE=true
FLASK_ENV=development
DEBUG=true
```
- ✅ No OAuth2 required
- ✅ Auto-reloads on code changes
- ✅ Detailed error messages
- ✅ Uses local files

**Production (Docker):**
```env
DEV_MODE=false
FLASK_ENV=production
DEBUG=false
```
- ✅ OAuth2 authentication required
- ✅ Optimized performance
- ✅ Generic error messages
- ✅ Uses Docker volumes

---

## Running the App

### Method 1: Using .env file (Recommended)

```bash
# Just run - it reads .env automatically
python app.py
```

### Method 2: Using dev.py (Alternative)

```bash
python dev.py
```

### Method 3: Docker (Production)

```bash
# From project root
cd ..
docker-compose up app
```

---

## Testing

```bash
# Run all tests
pytest -v

# Run specific test file
pytest test_routes_db.py -v

# Run with coverage
pytest --cov=. --cov-report=html
```

---

## File Structure

```
app/
├── app.py              # Main Flask application
├── routes_db.py        # TinyDB route manager
├── proxy_handler.py    # Request proxy handler
├── dev.py              # Development runner (alternative)
├── .env                # Environment variables (not in git)
├── .env.example        # Example environment file
├── requirements.txt    # Production dependencies
├── requirements-dev.txt # Development dependencies
├── Dockerfile          # Docker build config
├── static/             # CSS and JavaScript
│   ├── css/
│   │   ├── style.css   # Main stylesheet
│   │   └── admin.css   # Admin page styles
│   └── js/
│       ├── app.js      # Main JavaScript
│       └── admin.js    # Admin page logic
├── templates/          # HTML templates
│   ├── base.html
│   ├── index.html      # Dashboard
│   ├── admin.html      # Route manager
│   └── ...
└── test_*.py           # Test files
```

---

## API Endpoints

All endpoints require authentication (bypassed in DEV_MODE).

### Route Management
```
GET    /api/routes              # Get all routes
POST   /api/routes              # Create route
GET    /api/routes/:id          # Get single route
PUT    /api/routes/:id          # Update route
DELETE /api/routes/:id          # Delete route
POST   /api/routes/:id/test     # Test connectivity
POST   /api/routes/:id/toggle   # Toggle enabled
```

### Standard Endpoints
```
GET    /                        # Dashboard
GET    /admin                   # Route manager
GET    /health                  # Health check
GET    /whoami                  # User info
GET    /headers                 # Request headers
GET    /<route_path>/*          # Dynamic proxy
```

---

## Troubleshooting

### "Module not found" error
```bash
pip install -r requirements.txt
```

### Can't access the app
- Check if .env has `DEV_MODE=true`
- Verify port 8000 is not in use
- Check firewall settings

### Routes not saving
- Ensure routes.json is writable
- Check file permissions
- Look for errors in logs

### Import errors
```bash
# Make sure you're in the app directory
cd app
python app.py
```

---

## Security Notes

⚠️ **Never commit `.env` to git!** It's already in `.gitignore`.

🔒 **For production:**
- Set `DEV_MODE=false`
- Use a strong `SECRET_KEY`
- Enable OAuth2 authentication
- Use HTTPS only
- Review security settings

---

## Next Steps

1. ✅ Run the app: `python app.py`
2. ✅ Open browser: http://localhost:8000
3. ✅ Add a route at: http://localhost:8000/admin
4. ✅ Test proxy functionality
5. ✅ Deploy to production with Docker

---

For full project documentation, see the main README.md in the project root.
