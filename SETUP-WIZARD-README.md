# 🦈 Setup Wizard

Cross-platform Python setup wizard with web interface for configuring the Shark Route Manager.

## Features

✅ **System Checks**
- Automatically detects admin/sudo privileges
- Validates Docker installation and status
- Checks Docker Compose availability
- Verifies Tailscale installation and status
- Python version compatibility check

✅ **Web Interface**
- Beautiful, modern UI
- Real-time validation
- Auto-generated secure secrets
- Load existing configuration
- Form validation with helpful error messages

✅ **Configuration Management**
- Google OAuth2 Client credentials
- Tailscale Funnel hostname
- Development mode toggle
- Secure secret generation
- Creates `.env` file automatically

✅ **Docker Integration**
- Start/stop Docker containers from the UI
- Real-time status feedback
- Works with both `docker compose` (v2) and `docker-compose` (v1)

## Requirements

- Python 3.8 or higher
- Flask (will be installed automatically)
- Docker (optional, for container management)
- Tailscale (optional, for funnel setup)

## Installation

1. **Install Python dependencies:**

```bash
pip install flask
```

Or install all project dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Running the Setup Wizard

**On Windows (PowerShell):**
```powershell
python setup-wizard.py
```

**On Linux/Mac:**
```bash
python3 setup-wizard.py
```

**With admin/sudo privileges (recommended):**

Windows (PowerShell as Administrator):
```powershell
python setup-wizard.py
```

Linux/Mac:
```bash
sudo python3 setup-wizard.py
```

### Access the Web Interface

1. Run the setup wizard
2. Open your browser and navigate to: **http://localhost:8080**
3. Follow the on-screen instructions

## Setup Steps

1. **System Requirements Check**
   - The wizard will automatically check your system
   - Review any warnings or missing dependencies

2. **Generate Secrets**
   - Click "Generate Secrets" to create secure random values
   - Secrets are generated using Python's `secrets` module

3. **Enter OAuth2 Credentials**
   - Provide your Google OAuth2 Client ID
   - Provide your Google OAuth2 Client Secret
   - Get these from [Google Cloud Console](https://console.cloud.google.com/apis/credentials)

4. **Configure Tailscale**
   - Enter your Tailscale Funnel hostname
   - Format: `hostname.tailnet.ts.net`
   - Example: `sharky.snowy-burbot.ts.net`

5. **Development Mode** (Optional)
   - Check "Enable Development Mode" to bypass OAuth2
   - Only for local testing - NOT for production!

6. **Save Configuration**
   - Click "Save Configuration" to create `.env` file
   - Configuration is saved to project root

7. **Start Docker** (Optional)
   - Use "Start Docker Containers" to launch services
   - Requires Docker to be installed and running

## Configuration File

The wizard creates a `.env` file with the following structure:

```env
# Google OAuth2 Client Credentials
OAUTH2_PROXY_CLIENT_ID=your-client-id.apps.googleusercontent.com
OAUTH2_PROXY_CLIENT_SECRET=your-client-secret

# Cookie Secret (32 random bytes, base64 encoded)
OAUTH2_PROXY_COOKIE_SECRET=auto-generated-secret

# Tailscale Funnel Configuration
FUNNEL_HOST=https://hostname.tailnet.ts.net
FUNNEL_HOSTNAME=hostname.tailnet.ts.net

# Flask App Configuration
FLASK_ENV=development
DEV_MODE=true
DEBUG=true
PORT=5001
HOST=0.0.0.0

# Flask Secret Key (for session management)
SECRET_KEY=auto-generated-hex-key
```

## System Check Details

### Admin/Sudo Privileges

**Why needed:**
- Docker commands often require elevated privileges
- Tailscale configuration may need admin rights
- Port binding (especially ports < 1024)

**Without admin/sudo:**
- Setup wizard will still work
- Some Docker/Tailscale commands may fail
- Manual permission adjustments may be needed

### Docker

**Checked:**
- Installation status
- Docker daemon running
- Version information

**If not installed:**
- Download from [https://docker.com](https://docker.com)
- Install Docker Desktop (Windows/Mac) or Docker Engine (Linux)

### Docker Compose

**Checked:**
- Both v2 (`docker compose`) and v1 (`docker-compose`)
- Version information

**If not installed:**
- Included with Docker Desktop
- Linux: Install separately with `sudo apt-get install docker-compose`

### Tailscale

**Checked:**
- Installation status
- Service running status
- Version information

**If not installed:**
- Download from [https://tailscale.com](https://tailscale.com)
- Follow installation instructions for your platform

## Troubleshooting

### "Permission Denied" errors

**Solution:** Run the wizard with admin/sudo privileges

Windows:
```powershell
# Right-click PowerShell → "Run as Administrator"
python setup-wizard.py
```

Linux/Mac:
```bash
sudo python3 setup-wizard.py
```

### Docker not running

**Solution:** Start Docker Desktop (Windows/Mac) or Docker daemon (Linux)

Windows/Mac:
- Launch Docker Desktop application
- Wait for "Docker Desktop is running" status

Linux:
```bash
sudo systemctl start docker
```

### Tailscale not running

**Solution:** Start Tailscale service

Windows:
- Launch Tailscale from Start Menu
- Sign in if prompted

Mac:
- Launch Tailscale from Applications
- Sign in if prompted

Linux:
```bash
sudo tailscale up
```

### Port 8080 already in use

**Solution:** Stop other services using port 8080, or modify the port in `setup-wizard.py`:

```python
# Change this line at the bottom of setup-wizard.py
app.run(host='127.0.0.1', port=8080, debug=False)
# To:
app.run(host='127.0.0.1', port=8081, debug=False)  # or any other port
```

## Security Notes

- ⚠️ **DO NOT commit `.env` file to version control**
- ⚠️ Secrets are auto-generated using cryptographically secure methods
- ⚠️ DEV_MODE should ONLY be used for local development
- ⚠️ Keep your OAuth2 credentials secure
- ⚠️ The setup wizard runs on localhost only (127.0.0.1)

## Alternative Setup Methods

If you prefer traditional shell scripts:

**Windows:**
```powershell
.\setup.ps1
```

**Linux/Mac:**
```bash
./setup.sh
```

Both methods achieve the same result, but the Python wizard provides:
- Better cross-platform compatibility
- Visual interface
- Real-time validation
- System checks

## Support

For issues or questions:
1. Check system requirements are met
2. Review troubleshooting section above
3. Ensure all dependencies are installed
4. Check Docker and Tailscale are running

## License

Same license as the main Shark Route Manager project.
