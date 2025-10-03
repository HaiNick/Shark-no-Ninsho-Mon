# 🦈 Setup Wizard - Quick Start

## Run on Your Linux Instance

```bash
# 1. Install Flask (if not already installed)
pip3 install flask

# 2. Run the setup wizard with sudo (recommended)
sudo python3 setup-wizard.py

# 3. Open browser to:
http://localhost:8080
```

## What It Does

✅ **Checks system requirements:**
- Admin/sudo privileges
- Docker installation & status
- Docker Compose availability
- Tailscale installation & status
- Python version

✅ **Provides web GUI for:**
- OAuth2 credentials input
- Tailscale hostname configuration
- Auto-generated secure secrets
- DEV_MODE toggle
- .env file creation

✅ **Docker management:**
- Start containers directly from UI
- Stop containers with one click

## Benefits Over Shell Scripts

| Feature | Shell Scripts | Setup Wizard |
|---------|--------------|--------------|
| Cross-platform | Separate .ps1/.sh | Single Python file |
| UI | Terminal prompts | Beautiful web interface |
| Validation | Basic | Real-time with helpful errors |
| System checks | Limited | Comprehensive |
| Secret generation | Manual/automated | Always secure |
| Docker control | Separate commands | Integrated UI buttons |
| Config loading | Manual editing | One-click load existing |

## Files Created

- `setup-wizard.py` - Main Python application (500+ lines)
- `setup_templates/setup_wizard.html` - Web interface
- `.env` - Configuration file (auto-generated)

## Usage Notes

- **Recommended:** Run with `sudo` for full functionality
- **Port:** Runs on `localhost:8080` by default
- **Security:** Only accessible from localhost (127.0.0.1)
- **Secrets:** Auto-generated using Python's `secrets` module
- **Compatible:** Works with existing `.env` files (load & update)

## After Setup

Once `.env` is created, you can:

```bash
# Start Docker containers from terminal
docker compose up -d

# Or use the web UI buttons
# Click "Start Docker Containers" in the wizard
```

## Traditional Methods Still Available

The original setup scripts still work:

```bash
# Linux/Mac
./setup.sh

# Windows
.\setup.ps1
```

Choose whichever method you prefer! 🎯
