<a id="operations-top"></a>

# Day-2 Operations

> Production deployment, monitoring, maintenance, and operational best practices.

[![Back to README](https://img.shields.io/badge/←_Back_to-README-blue?style=for-the-badge)](../README.md)

---

## Table of Contents

- [Starting the stack](#starting-the-stack)
- [Monitoring & verification](#monitoring--verification)
- [Health checks](#health-checks)
- [Logging](#logging)
- [Backup & restore](#backup--restore)
- [Updates & maintenance](#updates--maintenance)
- [Stopping safely](#stopping-safely)
- [Performance tuning](#performance-tuning)

---

## Starting the stack

### Initial deployment

1. Ensure prerequisites are met (Docker, Docker Compose, Tailscale)
2. Configure environment variables in `.env`
3. Build and start services:

```powershell
# Windows PowerShell
docker compose up -d --build
```

```bash
# Linux / macOS
docker compose up -d --build
```

4. Enable Tailscale Funnel:

```powershell
tailscale funnel --bg 4180
```

5. Verify all services are running:

```powershell
docker compose ps
```

Expected output:
```
NAME                          STATUS   PORTS
shark-no-ninsho-mon-app-1     Up       8000/tcp
shark-no-ninsho-mon-caddy-1   Up       8080/tcp, 2019/tcp
shark-no-ninsho-mon-oauth2-1  Up       4180/tcp
```

### Updating the stack

Pull latest changes and rebuild:

```powershell
git pull origin main
docker compose down
docker compose up -d --build
```

### Restarting individual services

```powershell
# Restart Flask control plane
docker compose restart app

# Restart Caddy edge proxy
docker compose restart caddy

# Restart OAuth2 Proxy
docker compose restart oauth2-proxy
```

<p align="right">(<a href="#operations-top">back to top</a>)</p>

---

## Monitoring & verification

### Service health

Check all containers are running:

```powershell
docker compose ps
```

Verify Flask control plane health endpoint:

```powershell
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "healthy", "timestamp": "2025-10-17T10:30:00"}
```

### Tailscale Funnel status

```powershell
tailscale funnel status
```

Expected output:
```
https://your-hostname.your-tailnet.ts.net (Funnel on)
|-- tcp://localhost:4180
```

### Caddy Admin API

Query current configuration:

```powershell
curl http://localhost:2019/config/ | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

List active routes:

```powershell
curl http://localhost:2019/config/apps/http/servers/srv0/routes | ConvertFrom-Json
```

### Port availability

Check if required ports are available:

```powershell
# Windows PowerShell
netstat -ano | Select-String "8000|8080|4180|2019"
```

```bash
# Linux / macOS
lsof -iTCP -sTCP:LISTEN -nP | grep -E '8000|8080|4180|2019'
```

<p align="right">(<a href="#operations-top">back to top</a>)</p>

---

## Health checks

### Background health monitoring

The Flask app includes a background worker that periodically checks backend connectivity.

**Configuration** (in `.env`):
```bash
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=300  # seconds (5 minutes)
```

**Disable health checks**:
```bash
HEALTH_CHECK_ENABLED=false
# OR
HEALTH_CHECK_INTERVAL=0
```

### Manual health check

Test a specific backend:

```powershell
$body = @{
    target_ip = "192.168.1.100"
    target_port = 8096
    protocol = "http"
} | ConvertTo-Json

curl -Method POST `
     -Uri "http://localhost:8000/api/routes/test" `
     -Headers @{"Content-Type"="application/json"; "X-Forwarded-Email"="admin@example.com"} `
     -Body $body
```

### View route status

Check the dashboard at `https://your-hostname.ts.net/dashboard` or query the API:

```powershell
curl -Headers @{"X-Forwarded-Email"="admin@example.com"} `
     http://localhost:8000/api/routes | ConvertFrom-Json
```

Routes include `status` and `last_checked` fields showing health status.

<p align="right">(<a href="#operations-top">back to top</a>)</p>

---

## Logging

### View logs in real-time

```powershell
# All services
docker compose logs -f

# Specific service
docker compose logs -f app
docker compose logs -f caddy
docker compose logs -f oauth2-proxy
```

### Export logs to file

```powershell
# Windows PowerShell
docker compose logs --no-color > logs_$(Get-Date -Format "yyyyMMdd_HHmmss").txt
```

```bash
# Linux / macOS
docker compose logs --no-color > logs_$(date +%Y%m%d_%H%M%S).txt
```

### Log levels

**Flask app** (configured in `app/app.py`):
```python
import logging
logging.basicConfig(level=logging.INFO)
```

Set to `DEBUG` for verbose output during troubleshooting.

**Caddy** (configured in `caddy/base.json`):
```json
{
  "logging": {
    "logs": {
      "default": {
        "level": "INFO"
      }
    }
  }
}
```

**OAuth2 Proxy** (in `docker-compose.yml`):
```yaml
command:
  - --errors-to-info=true  # Log errors as info
  - --standard-logging=true  # Enable standard logging
```

### Structured logging

Flask logs include:
- Timestamp
- Log level
- Request path
- User email (from `X-Forwarded-Email`)
- Response status

Example:
```
2025-10-17 10:30:00 INFO [app] GET /api/routes - user@example.com - 200
2025-10-17 10:30:15 ERROR [caddy_manager] Failed to sync route /jellyfin - Connection refused
```

<p align="right">(<a href="#operations-top">back to top</a>)</p>

---

## Backup & restore

### What to backup

Critical files for disaster recovery:

1. **Environment configuration**: `.env`
2. **Route database**: `app/routes.json`
3. **Email allow list**: `app/emails.txt`
4. **Caddy configuration**: `caddy/base.json` (if customized)

### Backup script (PowerShell)

```powershell
# Create backup directory with timestamp
$backupDir = "backups\backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
New-Item -ItemType Directory -Force -Path $backupDir

# Copy critical files
Copy-Item .env "$backupDir\.env"
Copy-Item app\routes.json "$backupDir\routes.json"
Copy-Item app\emails.txt "$backupDir\emails.txt"
Copy-Item caddy\base.json "$backupDir\base.json"

Write-Host "Backup created: $backupDir"
```

### Backup script (Bash)

```bash
#!/bin/bash
# Create backup directory with timestamp
BACKUP_DIR="backups/backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Copy critical files
cp .env "$BACKUP_DIR/.env"
cp app/routes.json "$BACKUP_DIR/routes.json"
cp app/emails.txt "$BACKUP_DIR/emails.txt"
cp caddy/base.json "$BACKUP_DIR/base.json"

echo "Backup created: $BACKUP_DIR"
```

### Automated backups

**Windows Task Scheduler**:
1. Create task to run backup script daily
2. Set trigger: Daily at 2:00 AM
3. Action: Run PowerShell script

**Linux cron**:
```bash
# Add to crontab (run daily at 2 AM)
0 2 * * * /path/to/backup.sh
```

### Restore from backup

```powershell
# Windows PowerShell
$backupDir = "backups\backup_20251017_020000"
Copy-Item "$backupDir\.env" .env
Copy-Item "$backupDir\routes.json" app\routes.json
Copy-Item "$backupDir\emails.txt" app\emails.txt
Copy-Item "$backupDir\base.json" caddy\base.json

# Restart services
docker compose down
docker compose up -d --build
```

### Export routes via API

Programmatically backup routes:

```powershell
# Export all routes to JSON
curl -Headers @{"X-Forwarded-Email"="admin@example.com"} `
     http://localhost:8000/api/routes | `
     Out-File -Encoding utf8 routes_backup.json
```

<p align="right">(<a href="#operations-top">back to top</a>)</p>

---

## Updates & maintenance

### Update Docker images

```powershell
# Pull latest base images
docker compose pull

# Rebuild and restart
docker compose up -d --build
```

### Update Python dependencies

```powershell
# Update requirements.txt
# Then rebuild Flask container
docker compose build app
docker compose up -d app
```

### Database maintenance

**TinyDB compaction** (reduces file size):

```powershell
# Windows PowerShell
docker compose exec app python -c "from tinydb import TinyDB; db = TinyDB('/app/routes.json'); db.storage._handle.close()"
```

**Check database integrity**:

```powershell
docker compose exec app python -c "
from app.routes_db import RouteManager
rm = RouteManager('/app/routes.json')
routes = rm.get_all_routes()
print(f'Total routes: {len(routes)}')
print(f'Enabled routes: {sum(1 for r in routes if r.get(\"enabled\"))}')
"
```

### Rotate secrets

1. Generate new secrets:
   ```powershell
   python generate-secrets.py
   ```

2. Update `.env` with new values (especially `OAUTH2_PROXY_COOKIE_SECRET`)

3. Optional: Configure automatic cookie refresh for enhanced security:
   ```bash
   # Refresh authentication daily
   OAUTH2_PROXY_COOKIE_REFRESH=24h
   
   # Or weekly (recommended balance)
   OAUTH2_PROXY_COOKIE_REFRESH=168h
   ```

4. Restart services:
   ```powershell
   docker compose down
   docker compose up -d
   ```

5. Users will need to re-authenticate after restart. With cookie refresh enabled, they'll automatically re-authenticate at the configured interval.

<p align="right">(<a href="#operations-top">back to top</a>)</p>

---

## Stopping safely

### Graceful shutdown

```powershell
# Disable public access first
tailscale funnel off

# Stop containers gracefully (preserves volumes)
docker compose stop

# Verify all containers stopped
docker compose ps
```

### Complete teardown

```powershell
# Stop and remove containers, networks
docker compose down

# Remove volumes (CAUTION: deletes routes.json and emails.txt)
docker compose down -v
```

### Emergency stop

```powershell
# Immediate stop (sends SIGKILL)
docker compose kill

# Clean up
docker compose down
```

### Maintenance mode

Temporarily disable all routes:

```powershell
# Via API (disables all routes)
$routes = curl -Headers @{"X-Forwarded-Email"="admin@example.com"} `
               http://localhost:8000/api/routes | ConvertFrom-Json

foreach ($route in $routes) {
    curl -Method POST `
         -Headers @{"X-Forwarded-Email"="admin@example.com"} `
         "http://localhost:8000/api/routes/$($route.id)/toggle"
}
```

<p align="right">(<a href="#operations-top">back to top</a>)</p>

---

## Performance tuning

### Resource limits (Docker Compose)

Add resource constraints to `docker-compose.yml`:

```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          memory: 256M

  caddy:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 1G
```

### Caddy tuning

Edit `caddy/base.json` for high-traffic scenarios:

```json
{
  "admin": {
    "listen": "127.0.0.1:2019"
  },
  "apps": {
    "http": {
      "servers": {
        "srv0": {
          "max_header_bytes": 1048576,
          "read_timeout": "30s",
          "write_timeout": "30s",
          "idle_timeout": "120s"
        }
      }
    }
  }
}
```

### Health check optimization

For many routes, increase interval to reduce overhead:

```bash
HEALTH_CHECK_INTERVAL=600  # 10 minutes
```

Or disable if backends are stable:

```bash
HEALTH_CHECK_ENABLED=false
```

### TinyDB performance

For high write volume, consider:
- Increase backup frequency (TinyDB uses file writes)
- Monitor disk I/O
- Consider migration to SQLite or PostgreSQL for > 1000 routes

### Monitoring metrics

Key metrics to track:

- **Docker stats**: `docker stats`
- **Caddy Admin API metrics**: `curl http://localhost:2019/metrics`
- **Flask response times**: Check logs for slow endpoints
- **Disk usage**: Monitor `routes.json` growth

<p align="right">(<a href="#operations-top">back to top</a>)</p>

---

<div align="center">

[![Back to README](https://img.shields.io/badge/←_Back_to-README-blue?style=for-the-badge)](../README.md)

**Made with <3 for secure self-hosting**

</div>

<p align="right">(<a href="#operations-top">back to top</a>)</p>
