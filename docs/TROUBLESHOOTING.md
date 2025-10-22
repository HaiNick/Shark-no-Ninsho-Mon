<a id="troubleshooting-top"></a>

# Troubleshooting

> Common issues, diagnostic steps, and solutions for Shark-no-Ninsho-Mon.

[![Back to README](https://img.shields.io/badge/←_Back_to-README-blue?style=for-the-badge)](../README.md)

---

## Table of Contents

- [Quick diagnostics](#quick-diagnostics)
- [Docker & Compose issues](#docker--compose-issues)
- [File permission issues](#file-permission-issues)
- [Authentication issues](#authentication-issues)
- [Tailscale Funnel issues](#tailscale-funnel-issues)
- [Route & proxy issues](#route--proxy-issues)
- [Caddy Admin API issues](#caddy-admin-api-issues)
- [Performance issues](#performance-issues)
- [Port conflicts](#port-conflicts)

---

## Quick diagnostics

Run these commands to gather diagnostic information:

### Check service status

```powershell
# Windows PowerShell
docker compose ps
tailscale status
tailscale funnel status
```

```bash
# Linux / macOS
docker compose ps
tailscale status
tailscale funnel status
```

### Check logs

```powershell
# All services
docker compose logs --tail=50

# Specific service
docker compose logs --tail=50 app
docker compose logs --tail=50 caddy
docker compose logs --tail=50 oauth2-proxy
```

### Verify configuration

```powershell
# Check critical environment variables
Get-Content .env | Select-String "OAUTH2|FUNNEL|SECRET"
```

```bash
# Linux / macOS
grep -E "OAUTH2|FUNNEL|SECRET" .env
```

### Test Flask control plane

```powershell
curl http://localhost:8000/health
```

Expected: `{"status": "healthy", "timestamp": "..."}`

### Test Caddy Admin API

```powershell
curl http://localhost:2019/config/ | ConvertFrom-Json
```

Expected: Valid JSON configuration

<p align="right">(<a href="#troubleshooting-top">back to top</a>)</p>

---

## Docker & Compose issues

### "docker compose" command not found

**Symptom**: `docker compose` fails with "command not found"

**Cause**: Docker Compose plugin not installed

**Solution**:

Windows (Docker Desktop):
- Install Docker Desktop from [docker.com](https://www.docker.com/products/docker-desktop/)
- Ensure "Use Docker Compose V2" is enabled in settings

Linux:
```bash
# Install Docker Compose plugin
sudo apt-get update
sudo apt-get install docker-compose-plugin

# Verify installation
docker compose version
```

macOS:
```bash
# Via Homebrew
brew install docker-compose

# Or via Docker Desktop
# Download from docker.com
```

### Permission denied errors (Linux)

**Symptom**: "permission denied while trying to connect to Docker daemon"

**Cause**: User not in `docker` group

**Solution**:
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in, then verify
docker ps
```

### Container won't start

**Symptom**: Container exits immediately or shows "Exited (1)"

**Diagnostic**:
```powershell
# Check container logs
docker compose logs app

# Check exit code
docker compose ps
```

**Common causes**:
1. **Missing environment variables**: Check `.env` for required values
2. **Port conflicts**: See [Port conflicts](#port-conflicts)
3. **File permission issues**: See [File permission issues](#file-permission-issues)

**Solution**:
```powershell
# View detailed error
docker compose up app

# Rebuild and retry
docker compose down
docker compose up -d --build
```

### Out of disk space

**Symptom**: "no space left on device"

**Diagnostic**:
```powershell
# Windows (PowerShell)
docker system df

# Linux / macOS
docker system df
df -h
```

**Solution**:
```powershell
# Clean up unused containers, images, volumes
docker system prune -a

# Remove unused volumes (CAUTION: may delete data)
docker volume prune
```

<p align="right">(<a href="#troubleshooting-top">back to top</a>)</p>

---

## File permission issues

### Container cannot read/write files (Permission Denied)

**Symptom**: Flask container logs show "Permission denied" when accessing `emails.txt` or writing to `routes.json`

**Common scenario**: This happens when you run `setup-wizard.py` with `sudo`, which creates files owned by root, but the Docker container runs as `appuser`.

**Diagnostic**:
```bash
# Linux / macOS - Check file ownership
ls -la .env emails.txt

# Check inside container
docker compose exec app id
docker compose exec app ls -la /emails.txt
```

If files are owned by `root:root` but container user is `appuser` (UID 1000), there's a mismatch.

#### Solution 1: Automatic (Fresh Setup)

The setup wizard now automatically handles permissions when run with `sudo`:

```bash
sudo .venv/bin/python3 setup-wizard.py
```

The wizard will:
- Create `.env` and `emails.txt` files
- Automatically change ownership to your actual user (not root)
- Add `USER_ID` and `GROUP_ID` to `.env` for Docker user matching
- Set proper file permissions (644)

Then rebuild containers:
```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

#### Solution 2: Manual Fix (Existing Installation)

If you already have root-owned files, fix them manually:

```bash
# Fix file ownership
sudo chown $USER:$USER .env emails.txt

# Add user IDs to .env (if not present)
echo "USER_ID=$(id -u)" >> .env
echo "GROUP_ID=$(id -g)" >> .env

# Rebuild with matching user IDs
docker compose down
docker compose build --no-cache
docker compose up -d
```

#### How It Works

When you run the setup wizard with `sudo`:

1. The wizard detects the `SUDO_USER` environment variable (your actual username)
2. Looks up that user's UID and GID (e.g., 1000:1000)
3. Changes file ownership using `os.chown()` back to your user
4. Adds `USER_ID` and `GROUP_ID` to `.env`
5. Docker builds the container with matching UID/GID
6. The `appuser` inside the container has the same numeric ID as your host user
7. No permission conflicts on volume mounts

#### Verify It Works

```bash
# Check file ownership (should show your username, not root)
ls -la .env emails.txt

# Expected output:
# -rw-r--r-- 1 youruser youruser 1234 Oct 22 10:30 .env
# -rw-r--r-- 1 youruser youruser  144 Oct 22 10:30 emails.txt

# Check .env contains user IDs
grep -E "USER_ID|GROUP_ID" .env

# Expected output:
# USER_ID=1000
# GROUP_ID=1000

# Check container user matches
docker compose exec app id

# Expected output:
# uid=1000(appuser) gid=1000(appuser) groups=1000(appuser)

# Test file access in container
docker compose exec app cat /emails.txt
```

#### Named Volume Permissions

If the named volume (`routes_data`) has wrong permissions:

```bash
# Option 1: Remove and recreate (WARNING: deletes data)
docker compose down -v
docker compose up -d --build

# Option 2: Fix existing volume permissions (advanced)
# First, find the volume name
docker volume ls | grep routes_data

# Then fix permissions (replace 1000:1000 with your USER_ID:GROUP_ID)
docker run --rm -v shark-no-ninsho-mon_routes_data:/data alpine chown -R 1000:1000 /data
```

#### Platform Notes

- **Linux**: Full support, automatically detects and fixes permissions
- **macOS**: Full support (though `sudo` less commonly needed for Docker)
- **Windows**: Not applicable (Docker Desktop handles permissions differently)

### routes.json or emails.txt created as directories

**Symptom**: Flask fails to start with "Is a directory" error

**Cause**: Docker created bind mounts as directories before files existed

**Diagnostic**:
```powershell
# Windows PowerShell
Get-Item app\routes.json, app\emails.txt | Select-Object Mode, Name

# Linux / macOS
ls -la app/routes.json app/emails.txt
```

If output shows directories (`d` flag or `Directory` mode), they need to be fixed.

**Solution (automatic)**:
```powershell
python fix-files.py
```

**Solution (manual)**:
```powershell
# Windows PowerShell
# Stop containers first
docker compose down

# Remove directories
Remove-Item -Recurse -Force app\routes.json
Remove-Item -Recurse -Force app\emails.txt

# Create proper files
'{"_default": {}}' | Out-File -Encoding utf8 app\routes.json
'# Add authorized emails here' | Out-File -Encoding utf8 app\emails.txt

# Restart
docker compose up -d --build
```

```bash
# Linux / macOS
docker compose down
rm -rf app/routes.json app/emails.txt
echo '{"_default": {}}' > app/routes.json
echo '# Add authorized emails here' > app/emails.txt
docker compose up -d --build
```

### Read-only file system

**Symptom**: "Read-only file system" errors when writing routes

**Cause**: Volume mounted read-only

**Solution**: Check `docker-compose.yml` volumes don't have `:ro` flag:
```yaml
volumes:
  - ./app/routes.json:/app/routes.json  # Correct
  # NOT: - ./app/routes.json:/app/routes.json:ro
```

<p align="right">(<a href="#troubleshooting-top">back to top</a>)</p>

---

## Authentication issues

### "403 Forbidden" on all requests

**Symptom**: Cannot access dashboard, all requests return 403

**Cause 1**: Email not in allow list

**Solution**:
```powershell
# Check emails.txt
Get-Content app\emails.txt
```

Add your email (one per line):
```
your-email@gmail.com
```

Restart OAuth2 Proxy:
```powershell
docker compose restart oauth2-proxy
```

**Cause 2**: OAuth2 Proxy not configured correctly

**Diagnostic**:
```powershell
docker compose logs oauth2-proxy | Select-String -Pattern "error|ERROR"
```

**Solution**: Verify environment variables in `.env`:
```bash
OAUTH2_PROXY_CLIENT_ID=your-client-id
OAUTH2_PROXY_CLIENT_SECRET=your-client-secret
OAUTH2_PROXY_COOKIE_SECRET=your-32-byte-base64-secret
```

### OAuth2 callback error

**Symptom**: Redirect to Google works, but callback fails with error

**Cause**: Redirect URI mismatch

**Diagnostic**: Check Google Cloud Console OAuth2 credentials

**Solution**: Ensure authorized redirect URI matches exactly:
```
https://your-hostname.your-tailnet.ts.net/oauth2/callback
```

**In Google Cloud Console**:
1. Navigate to APIs & Services → Credentials
2. Edit OAuth 2.0 Client ID
3. Add redirect URI (must match EXACTLY)
4. Save changes

**Verify in environment**:
```powershell
$env:FUNNEL_HOSTNAME  # Should match Google Console
```

### Session expires immediately

**Symptom**: Successfully authenticate but immediately logged out

**Cause**: Cookie configuration issue

**Solution**: Check `.env` cookie settings:
```bash
OAUTH2_PROXY_COOKIE_SECURE=true   # Must be true for HTTPS
OAUTH2_PROXY_COOKIE_SAMESITE=lax  # Or 'strict'
```

For development with HTTP:
```bash
OAUTH2_PROXY_COOKIE_SECURE=false  # Only for local dev
DEV_MODE=true  # Bypass OAuth entirely
```

### "Invalid email domain" error

**Symptom**: Authentication succeeds but access denied due to domain

**Cause**: `OAUTH2_PROXY_EMAIL_DOMAINS` restricts allowed domains

**Solution**: Update `.env`:
```bash
# Allow all domains
OAUTH2_PROXY_EMAIL_DOMAINS=*

# Or specific domains only
OAUTH2_PROXY_EMAIL_DOMAINS=example.com,company.org
```

Restart OAuth2 Proxy:
```powershell
docker compose restart oauth2-proxy
```

<p align="right">(<a href="#troubleshooting-top">back to top</a>)</p>

---

## Tailscale Funnel issues

### Funnel command fails

**Symptom**: `tailscale funnel` returns error

**Diagnostic**:
```powershell
tailscale status
```

**Cause 1**: Not authenticated

**Solution**:
```powershell
tailscale up
```

**Cause 2**: Funnel not enabled on account

**Solution**: 
- Visit [Tailscale Admin Console](https://login.tailscale.com/admin/settings/general)
- Enable "Funnel" in settings
- Funnel is available on all plans (including free)

**Cause 3**: Port already in use

**Solution**: Check port 4180 is available:
```powershell
# Windows
netstat -ano | Select-String "4180"

# Linux / macOS
lsof -i :4180
```

Stop conflicting process or change port in `docker-compose.yml`

### Funnel works but site unreachable

**Symptom**: `tailscale funnel status` shows active, but site times out

**Diagnostic**:
```powershell
# Check OAuth2 Proxy is listening
docker compose ps oauth2-proxy

# Check logs
docker compose logs oauth2-proxy
```

**Solution**: Ensure OAuth2 Proxy is running and listening on port 4180:
```powershell
docker compose restart oauth2-proxy
tailscale funnel off
tailscale funnel --bg 4180
```

### Certificate errors

**Symptom**: Browser shows TLS/SSL errors

**Cause**: Tailscale Funnel provides automatic HTTPS with valid certificate

**Solution**: This shouldn't happen with Funnel. Verify:
```powershell
tailscale funnel status
```

Should show HTTPS URL. If showing HTTP, Funnel may not be active.

<p align="right">(<a href="#troubleshooting-top">back to top</a>)</p>

---

## Route & proxy issues

### Route not accessible (404)

**Symptom**: Route returns 404 Not Found

**Diagnostic**:
```powershell
# Check route exists in database
curl -Headers @{"X-Forwarded-Email"="admin@example.com"} `
     http://localhost:8000/api/routes | ConvertFrom-Json
```

**Solution 1**: Route not created

Create via dashboard at `https://your-hostname.ts.net/dashboard` or via API

**Solution 2**: Route disabled

Enable via dashboard or API:
```powershell
curl -Method POST `
     -Headers @{"X-Forwarded-Email"="admin@example.com"} `
     "http://localhost:8000/api/routes/<route-id>/toggle"
```

**Solution 3**: Route not synced to Caddy

Check Caddy configuration:
```powershell
curl http://localhost:2019/config/apps/http/servers/srv0/routes | ConvertFrom-Json
```

Manually trigger sync:
```powershell
docker compose restart app
```

### Backend unreachable (502 Bad Gateway)

**Symptom**: Route exists but returns 502

**Diagnostic**:
```powershell
# Check Caddy logs
docker compose logs caddy | Select-String "502|error"

# Test backend connectivity
curl http://192.168.1.100:8096  # Replace with your backend
```

**Common causes**:

1. **Backend not running**: Start backend service
2. **Wrong IP/port**: Verify in route configuration
3. **Firewall blocking**: Check host firewall allows connection
4. **Backend only listens on localhost**: Backend must listen on 0.0.0.0 or specific IP

**Solution**: Update route with correct target:
```powershell
# Via dashboard or API
# Ensure target_ip and target_port are correct
```

### SSL/TLS errors with HTTPS backends

**Symptom**: 502 error when proxying to HTTPS backend

**Cause**: TLS verification enabled but backend has self-signed certificate

**Solution 1**: Disable TLS verification for this route (not recommended for production):

In route configuration, set:
```json
{
  "insecure_skip_verify": true
}
```

**Solution 2**: Add valid certificate to backend

**Solution 3**: Set custom SNI:
```json
{
  "sni": "backend.local"
}
```

### Route health check fails

**Symptom**: Dashboard shows route as "unhealthy"

**Diagnostic**:
```powershell
# Check Flask logs for health check errors
docker compose logs app | Select-String "health"

# Manually test backend
curl -Method HEAD http://192.168.1.100:8096
```

**Solution**: 
- Verify backend is running
- Ensure backend responds to HEAD requests
- Disable health checks if not needed:
  ```bash
  HEALTH_CHECK_ENABLED=false
  ```

<p align="right">(<a href="#troubleshooting-top">back to top</a>)</p>

---

## Caddy Admin API issues

### Admin API not accessible

**Symptom**: `curl http://localhost:2019/config/` fails

**Diagnostic**:
```powershell
# Check Caddy is running
docker compose ps caddy

# Check Caddy logs
docker compose logs caddy
```

**Solution**:
```powershell
# Restart Caddy
docker compose restart caddy

# Verify port 2019 is listening
netstat -ano | Select-String "2019"  # Windows
lsof -i :2019  # Linux/macOS
```

### Routes not syncing

**Symptom**: Add route in dashboard but Caddy doesn't proxy it

**Diagnostic**:
```powershell
# Check Flask logs for sync errors
docker compose logs app | Select-String "CADDY_SYNC|error"

# Verify route in Caddy config
curl http://localhost:2019/config/apps/http/servers/srv0/routes
```

**Cause**: Flask can't reach Caddy Admin API

**Solution**: Ensure Caddy Admin API is accessible from Flask container:
```powershell
# Test from within Flask container
docker compose exec app curl http://caddy:2019/config/
```

If fails, check `docker-compose.yml` network configuration.

### "Config unchanged" errors

**Symptom**: Caddy logs show "config unchanged" when syncing

**Cause**: Not an error - Caddy detected no changes needed

**Solution**: No action required - this is normal behavior

<p align="right">(<a href="#troubleshooting-top">back to top</a>)</p>

---

## Performance issues

### Slow response times

**Symptom**: Routes respond slowly

**Diagnostic**:
```powershell
# Check container resource usage
docker stats

# Check backend response time
Measure-Command { curl http://192.168.1.100:8096 }
```

**Solutions**:

1. **High CPU usage**: Increase resource limits in `docker-compose.yml`
2. **Slow backend**: Optimize backend service
3. **Network latency**: Check network between proxy and backend
4. **Too many health checks**: Increase `HEALTH_CHECK_INTERVAL` or disable

### Memory issues

**Symptom**: Containers crash or become unresponsive

**Diagnostic**:
```powershell
docker stats
docker compose logs app | Select-String "memory|OOM"
```

**Solution**: Add memory limits to `docker-compose.yml`:
```yaml
services:
  app:
    deploy:
      resources:
        limits:
          memory: 512M
```

### High disk I/O

**Symptom**: Slow performance, high disk usage

**Cause**: TinyDB writes frequently

**Solution**:
- Reduce health check frequency
- Move `routes.json` to faster storage (SSD)
- Consider migrating to SQLite for > 1000 routes

<p align="right">(<a href="#troubleshooting-top">back to top</a>)</p>

---

## Port conflicts

### Port already in use

**Symptom**: Container fails to start with "address already in use"

**Diagnostic**:
```powershell
# Windows PowerShell
netstat -ano | Select-String "8000|8080|4180|2019"
```

```bash
# Linux / macOS
lsof -iTCP -sTCP:LISTEN -nP | grep -E '8000|8080|4180|2019'
```

**Solution**: Change conflicting port in `.env`:
```bash
APP_PORT=8001
CADDY_HTTP_PORT=8081
OAUTH2_PROXY_PORT=4181
CADDY_ADMIN_PORT=2020
```

Then restart:
```powershell
docker compose down
docker compose up -d
```

### Finding what's using a port

```powershell
# Windows PowerShell (find PID)
$port = 8000
netstat -ano | Select-String ":$port "

# Get process name from PID
Get-Process -Id <PID>

# Stop process
Stop-Process -Id <PID>
```

```bash
# Linux / macOS
lsof -i :8000
# Kill process
kill <PID>
```

<p align="right">(<a href="#troubleshooting-top">back to top</a>)</p>

---

## Getting help

If these troubleshooting steps don't resolve your issue:

1. **Gather diagnostics**:
   ```powershell
   # Create diagnostic report
   docker compose ps > diagnostics.txt
   docker compose logs >> diagnostics.txt
   tailscale status >> diagnostics.txt
   tailscale funnel status >> diagnostics.txt
   Get-Content .env | Select-String "OAUTH2|FUNNEL" >> diagnostics.txt
   ```

2. **Open an issue**:
   - Visit [GitHub Issues](https://github.com/HaiNick/Shark-no-Ninsho-Mon/issues)
   - Include diagnostics report
   - Describe expected vs actual behavior
   - Include steps to reproduce

3. **Start a discussion**:
   - For questions: [GitHub Discussions](https://github.com/HaiNick/Shark-no-Ninsho-Mon/discussions)

<div align="center">

[![Back to README](https://img.shields.io/badge/←_Back_to-README-blue?style=for-the-badge)](../README.md)

**Made with <3 for secure self-hosting**

</div>

<p align="right">(<a href="#troubleshooting-top">back to top</a>)</p>
