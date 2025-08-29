# Extra Features & Advanced Configuration

This document covers advanced customization options for Shark-no-Ninsho-Mon, including multiple applications, custom routing, and integration examples.

## Table of Contents

- [Adding Multiple Applications](#adding-multiple-applications)
  - [Method 1: Path-Based Routing (Single Domain)](#method-1-path-based-routing-single-domain)
  - [Method 1.1: File-Based Upstream Configuration](#method-11-file-based-upstream-configuration)
  - [Method 2: Protecting External Applications (Non-Docker)](#method-2-protecting-external-applications-non-docker)
  - [Method 3: Using NGINX for Advanced Routing](#method-3-using-nginx-for-advanced-routing)
  - [Method 4: Different Authentication for Different Apps](#method-4-different-authentication-for-different-apps)
- [Integration Examples](#integration-examples)
  - [Example 1: Protecting a Grafana Instance](#example-1-protecting-a-grafana-instance)
  - [Example 2: Protecting a Jupyter Notebook](#example-2-protecting-a-jupyter-notebook)
  - [Example 3: Protecting Multiple Services (Home Lab Setup)](#example-3-protecting-multiple-services-home-lab-setup)
- [Advanced Security](#advanced-security)
- [Configuration Tips](#configuration-tips)
- [Common Patterns](#common-patterns)

---

## Adding Multiple Applications

You can protect multiple applications behind the same OAuth2 proxy using path-based routing or subdomain routing.

### Method 1: Path-Based Routing (Single Domain)

Add additional services to `docker-compose.yml`:

```yaml
services:
  # Existing app service
  app:
    build: ./app
    expose:
      - "8000"
    volumes:
      - ./emails.txt:/app/emails.txt:ro
    restart: unless-stopped

  # Add your second application
  admin-app:
    image: your-admin-app:latest  # or build: ./admin-app
    expose:
      - "3000"
    restart: unless-stopped

  # Add a third application
  api-app:
    image: your-api-app:latest  # or build: ./api-app
    expose:
      - "5000"
    restart: unless-stopped

  # Enhanced OAuth2 proxy with multiple upstreams
  oauth2-proxy:
    image: quay.io/oauth2-proxy/oauth2-proxy:v7.6.0
    ports:
      - "127.0.0.1:4180:4180"
    env_file:
      - ./.env
    environment:
      OAUTH2_PROXY_PROVIDER: google
      OAUTH2_PROXY_SCOPE: "openid email profile"
      OAUTH2_PROXY_REDIRECT_URL: "${FUNNEL_HOST}/oauth2/callback"
      OAUTH2_PROXY_WHITELIST_DOMAINS: "${FUNNEL_HOSTNAME}"
      # Multiple upstream configuration
      OAUTH2_PROXY_UPSTREAMS: |
        http://app:8000/,
        http://admin-app:3000/admin/,
        http://api-app:5000/api/
      OAUTH2_PROXY_HTTP_ADDRESS: "0.0.0.0:4180"
      OAUTH2_PROXY_REVERSE_PROXY: "true"
      OAUTH2_PROXY_PASS_USER_HEADERS: "true"
      OAUTH2_PROXY_PREFER_EMAIL_TO_USER: "true"
      OAUTH2_PROXY_SET_XAUTHREQUEST: "true"
      OAUTH2_PROXY_AUTHENTICATED_EMAILS_FILE: "/etc/oauth2-proxy/emails.txt"
      OAUTH2_PROXY_SKIP_PROVIDER_BUTTON: "true"
      OAUTH2_PROXY_COOKIE_SECURE: "true"
      OAUTH2_PROXY_COOKIE_SAMESITE: "lax"
    volumes:
      - ./emails.txt:/etc/oauth2-proxy/emails.txt:ro
    depends_on:
      - app
      - admin-app
      - api-app
    restart: unless-stopped
```

**Access your apps:**
- Main app: `https://your-host.your-tailnet.ts.net/`
- Admin app: `https://your-host.your-tailnet.ts.net/admin/`
- API app: `https://your-host.your-tailnet.ts.net/api/`

### Method 1.1: File-Based Upstream Configuration

Instead of hardcoding upstreams in `docker-compose.yml`, you can manage them in a separate file for easier maintenance.

**Step 1:** Create an `upstreams.txt` file:

```txt
# Upstream configuration for OAuth2 Proxy
# Format: http://service:port/path/
# Lines starting with # are ignored

# Main application (default route)
http://app:8000/

# Admin panel (accessible via /admin/ path)
http://admin-app:3000/admin/

# API service (accessible via /api/ path)
http://api-app:5000/api/

# External service on host
http://host.docker.internal:8080/monitoring/

# External service on network
http://192.168.1.100:3000/dashboard/
```

**Step 2:** Update `docker-compose.yml` to use the file:

```yaml
services:
  app:
    build: ./app
    expose:
      - "8000"
    volumes:
      - ./emails.txt:/app/emails.txt:ro
    restart: unless-stopped

  admin-app:
    image: your-admin-app:latest
    expose:
      - "3000"
    restart: unless-stopped

  api-app:
    image: your-api-app:latest
    expose:
      - "5000"
    restart: unless-stopped

  oauth2-proxy:
    image: quay.io/oauth2-proxy/oauth2-proxy:v7.6.0
    ports:
      - "127.0.0.1:4180:4180"
    env_file:
      - ./.env
    environment:
      OAUTH2_PROXY_PROVIDER: google
      OAUTH2_PROXY_SCOPE: "openid email profile"
      OAUTH2_PROXY_REDIRECT_URL: "${FUNNEL_HOST}/oauth2/callback"
      OAUTH2_PROXY_WHITELIST_DOMAINS: "${FUNNEL_HOSTNAME}"
      # Use file-based upstream configuration
      OAUTH2_PROXY_UPSTREAMS_FILE: "/etc/oauth2-proxy/upstreams.txt"
      OAUTH2_PROXY_HTTP_ADDRESS: "0.0.0.0:4180"
      OAUTH2_PROXY_REVERSE_PROXY: "true"
      OAUTH2_PROXY_PASS_USER_HEADERS: "true"
      OAUTH2_PROXY_PREFER_EMAIL_TO_USER: "true"
      OAUTH2_PROXY_SET_XAUTHREQUEST: "true"
      OAUTH2_PROXY_AUTHENTICATED_EMAILS_FILE: "/etc/oauth2-proxy/emails.txt"
      OAUTH2_PROXY_SKIP_PROVIDER_BUTTON: "true"
      OAUTH2_PROXY_COOKIE_SECURE: "true"
      OAUTH2_PROXY_COOKIE_SAMESITE: "lax"
    volumes:
      - ./emails.txt:/etc/oauth2-proxy/emails.txt:ro
      - ./upstreams.txt:/etc/oauth2-proxy/upstreams.txt:ro
    depends_on:
      - app
      - admin-app
      - api-app
    restart: unless-stopped
```

**Step 3:** Alternative approach using environment file:

Create `upstreams.env`:

```bash
# Upstream services configuration
OAUTH2_PROXY_UPSTREAMS=http://app:8000/,http://admin-app:3000/admin/,http://api-app:5000/api/
```

Then reference it in `docker-compose.yml`:

```yaml
oauth2-proxy:
  image: quay.io/oauth2-proxy/oauth2-proxy:v7.6.0
  ports:
    - "127.0.0.1:4180:4180"
  env_file:
    - ./.env
    - ./upstreams.env  # Add upstream configuration
  environment:
    OAUTH2_PROXY_PROVIDER: google
    OAUTH2_PROXY_SCOPE: "openid email profile"
    OAUTH2_PROXY_REDIRECT_URL: "${FUNNEL_HOST}/oauth2/callback"
    OAUTH2_PROXY_WHITELIST_DOMAINS: "${FUNNEL_HOSTNAME}"
    # OAUTH2_PROXY_UPSTREAMS is now loaded from upstreams.env
    OAUTH2_PROXY_HTTP_ADDRESS: "0.0.0.0:4180"
    OAUTH2_PROXY_REVERSE_PROXY: "true"
    OAUTH2_PROXY_PASS_USER_HEADERS: "true"
    OAUTH2_PROXY_PREFER_EMAIL_TO_USER: "true"
    OAUTH2_PROXY_SET_XAUTHREQUEST: "true"
    OAUTH2_PROXY_AUTHENTICATED_EMAILS_FILE: "/etc/oauth2-proxy/emails.txt"
    OAUTH2_PROXY_SKIP_PROVIDER_BUTTON: "true"
    OAUTH2_PROXY_COOKIE_SECURE: "true"
    OAUTH2_PROXY_COOKIE_SAMESITE: "lax"
  volumes:
    - ./emails.txt:/etc/oauth2-proxy/emails.txt:ro
  depends_on:
    - app
    - admin-app
    - api-app
  restart: unless-stopped
```

**Benefits of File-Based Configuration:**

1. **Easy Management** - Add/remove routes without touching docker-compose.yml
2. **Version Control** - Track routing changes separately
3. **Comments** - Document each route with comments
4. **Reusability** - Use different upstream files for different environments
5. **Dynamic Updates** - Change routes and restart only the proxy service

**Managing Routes:**

```bash
# Add a new service route
echo "http://new-service:4000/newapp/" >> upstreams.txt

# Remove a route (edit the file)
nano upstreams.txt

# Apply changes
docker compose restart oauth2-proxy

# Or reload without full restart (if supported)
docker compose kill -s HUP oauth2-proxy
```

**Multiple Environment Support:**

```bash
# Different files for different environments
cp upstreams.txt upstreams.production.txt
cp upstreams.txt upstreams.development.txt

# Use environment-specific file
ln -sf upstreams.production.txt upstreams.txt
docker compose restart oauth2-proxy
```

**Advanced Upstream File Format:**

```txt
# upstreams-advanced.txt
# Supports more complex routing patterns

# Default app
http://app:8000/

# Admin with specific path matching
http://admin-app:3000/admin/

# API with version routing
http://api-v1:5000/api/v1/
http://api-v2:5001/api/v2/

# External services
http://grafana.local:3000/grafana/
http://192.168.1.50:8080/nas/

# WebSocket support (if needed)
ws://socketio-app:3001/socket.io/

# Static file server
http://static-files:8000/static/
```

### Method 2: Protecting External Applications (Non-Docker)

Sometimes you want to protect applications that are already running outside of Docker, such as:
- Services running directly on the host
- Applications on other machines in your network
- Legacy applications that can't be containerized
- Development servers

#### Example 1: Protecting a Local Service on Host

If you have a service running directly on your host machine (e.g., a local web server on port 8080):

```yaml
services:
  oauth2-proxy:
    image: quay.io/oauth2-proxy/oauth2-proxy:v7.6.0
    ports:
      - "127.0.0.1:4180:4180"
    env_file:
      - ./.env
    environment:
      OAUTH2_PROXY_PROVIDER: google
      OAUTH2_PROXY_SCOPE: "openid email profile"
      OAUTH2_PROXY_REDIRECT_URL: "${FUNNEL_HOST}/oauth2/callback"
      OAUTH2_PROXY_WHITELIST_DOMAINS: "${FUNNEL_HOSTNAME}"
      # Point to host machine (Docker's host.docker.internal or host IP)
      OAUTH2_PROXY_UPSTREAMS: "http://host.docker.internal:8080"
      OAUTH2_PROXY_HTTP_ADDRESS: "0.0.0.0:4180"
      OAUTH2_PROXY_REVERSE_PROXY: "true"
      OAUTH2_PROXY_PASS_USER_HEADERS: "true"
      OAUTH2_PROXY_PREFER_EMAIL_TO_USER: "true"
      OAUTH2_PROXY_SET_XAUTHREQUEST: "true"
      OAUTH2_PROXY_AUTHENTICATED_EMAILS_FILE: "/etc/oauth2-proxy/emails.txt"
      OAUTH2_PROXY_SKIP_PROVIDER_BUTTON: "true"
      OAUTH2_PROXY_COOKIE_SECURE: "true"
      OAUTH2_PROXY_COOKIE_SAMESITE: "lax"
    volumes:
      - ./emails.txt:/etc/oauth2-proxy/emails.txt:ro
    restart: unless-stopped
    # Linux: Add network mode to access host services
    network_mode: "host"  # Use this for Linux host access
    # OR for Windows/Mac, use extra_hosts:
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

**Important Notes for Host Access:**
- **Linux**: Use `network_mode: "host"` or `http://172.17.0.1:8080` (Docker bridge IP)
- **Windows/Mac**: Use `http://host.docker.internal:8080`
- **Alternative**: Find your host IP and use `http://YOUR_HOST_IP:8080`

#### Example 2: Protecting Multiple External Services

Protect services running on different machines in your network:

```yaml
services:
  oauth2-proxy:
    image: quay.io/oauth2-proxy/oauth2-proxy:v7.6.0
    ports:
      - "127.0.0.1:4180:4180"
    env_file:
      - ./.env
    environment:
      OAUTH2_PROXY_PROVIDER: google
      OAUTH2_PROXY_SCOPE: "openid email profile"
      OAUTH2_PROXY_REDIRECT_URL: "${FUNNEL_HOST}/oauth2/callback"
      OAUTH2_PROXY_WHITELIST_DOMAINS: "${FUNNEL_HOSTNAME}"
      # Multiple external services
      OAUTH2_PROXY_UPSTREAMS: |
        http://192.168.1.100:3000/,
        http://192.168.1.101:8080/nas/,
        http://host.docker.internal:9090/monitoring/
      OAUTH2_PROXY_HTTP_ADDRESS: "0.0.0.0:4180"
      OAUTH2_PROXY_REVERSE_PROXY: "true"
      OAUTH2_PROXY_PASS_USER_HEADERS: "true"
      OAUTH2_PROXY_PREFER_EMAIL_TO_USER: "true"
      OAUTH2_PROXY_SET_XAUTHREQUEST: "true"
      OAUTH2_PROXY_AUTHENTICATED_EMAILS_FILE: "/etc/oauth2-proxy/emails.txt"
      OAUTH2_PROXY_SKIP_PROVIDER_BUTTON: "true"
      OAUTH2_PROXY_COOKIE_SECURE: "true"
      OAUTH2_PROXY_COOKIE_SAMESITE: "lax"
    volumes:
      - ./emails.txt:/etc/oauth2-proxy/emails.txt:ro
    extra_hosts:
      - "host.docker.internal:host-gateway"
    restart: unless-stopped
```

**Access your external services:**
- Service 1: `https://your-host.your-tailnet.ts.net/` → `192.168.1.100:3000`
- NAS: `https://your-host.your-tailnet.ts.net/nas/` → `192.168.1.101:8080`
- Monitoring: `https://your-host.your-tailnet.ts.net/monitoring/` → Local host port 9090

#### Example 3: Mixed Docker + External Services

Combine Docker containers with external services:

```yaml
services:
  # Docker container
  portainer:
    image: portainer/portainer-ce:latest
    expose:
      - "9000"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - portainer-data:/data
    restart: unless-stopped

  # NGINX for complex routing
  nginx:
    image: nginx:alpine
    expose:
      - "8080"
    volumes:
      - ./nginx/mixed.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - portainer
    extra_hosts:
      - "host.docker.internal:host-gateway"
    restart: unless-stopped

  oauth2-proxy:
    image: quay.io/oauth2-proxy/oauth2-proxy:v7.6.0
    ports:
      - "127.0.0.1:4180:4180"
    env_file:
      - ./.env
    environment:
      OAUTH2_PROXY_PROVIDER: google
      OAUTH2_PROXY_SCOPE: "openid email profile"
      OAUTH2_PROXY_REDIRECT_URL: "${FUNNEL_HOST}/oauth2/callback"
      OAUTH2_PROXY_WHITELIST_DOMAINS: "${FUNNEL_HOSTNAME}"
      OAUTH2_PROXY_UPSTREAMS: "http://nginx:8080"
      OAUTH2_PROXY_HTTP_ADDRESS: "0.0.0.0:4180"
      OAUTH2_PROXY_REVERSE_PROXY: "true"
      OAUTH2_PROXY_PASS_USER_HEADERS: "true"
      OAUTH2_PROXY_PREFER_EMAIL_TO_USER: "true"
      OAUTH2_PROXY_SET_XAUTHREQUEST: "true"
      OAUTH2_PROXY_AUTHENTICATED_EMAILS_FILE: "/etc/oauth2-proxy/emails.txt"
      OAUTH2_PROXY_SKIP_PROVIDER_BUTTON: "true"
      OAUTH2_PROXY_COOKIE_SECURE: "true"
      OAUTH2_PROXY_COOKIE_SAMESITE: "lax"
    volumes:
      - ./emails.txt:/etc/oauth2-proxy/emails.txt:ro
    depends_on:
      - nginx
    restart: unless-stopped

volumes:
  portainer-data:
```

**Corresponding `nginx/mixed.conf`:**

```nginx
events {
    worker_connections 1024;
}

http {
    server {
        listen 8080;
        
        # Docker service (Portainer)
        location /portainer/ {
            proxy_pass http://portainer:9000/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        # External service running on host
        location /local-app/ {
            proxy_pass http://host.docker.internal:8080/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        # External service on another machine
        location /nas/ {
            proxy_pass http://192.168.1.50:5000/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        # Default redirect
        location = / {
            return 302 /portainer/;
        }
    }
}
```

#### Example 4: Common External Service Integrations

**Protecting a Home Assistant instance:**

```yaml
# Home Assistant running on host port 8123
services:
  oauth2-proxy:
    image: quay.io/oauth2-proxy/oauth2-proxy:v7.6.0
    ports:
      - "127.0.0.1:4180:4180"
    env_file:
      - ./.env
    environment:
      OAUTH2_PROXY_PROVIDER: google
      OAUTH2_PROXY_SCOPE: "openid email profile"
      OAUTH2_PROXY_REDIRECT_URL: "${FUNNEL_HOST}/oauth2/callback"
      OAUTH2_PROXY_WHITELIST_DOMAINS: "${FUNNEL_HOSTNAME}"
      OAUTH2_PROXY_UPSTREAMS: "http://host.docker.internal:8123"
      OAUTH2_PROXY_HTTP_ADDRESS: "0.0.0.0:4180"
      OAUTH2_PROXY_REVERSE_PROXY: "true"
      OAUTH2_PROXY_PASS_USER_HEADERS: "true"
      OAUTH2_PROXY_PREFER_EMAIL_TO_USER: "true"
      OAUTH2_PROXY_SET_XAUTHREQUEST: "true"
      OAUTH2_PROXY_AUTHENTICATED_EMAILS_FILE: "/etc/oauth2-proxy/emails.txt"
      OAUTH2_PROXY_SKIP_PROVIDER_BUTTON: "true"
      OAUTH2_PROXY_COOKIE_SECURE: "true"
      OAUTH2_PROXY_COOKIE_SAMESITE: "lax"
    volumes:
      - ./emails.txt:/etc/oauth2-proxy/emails.txt:ro
    extra_hosts:
      - "host.docker.internal:host-gateway"
    restart: unless-stopped
```

**Protecting a Pi-hole admin interface:**

```yaml
# Pi-hole running on 192.168.1.2:80/admin
services:
  oauth2-proxy:
    image: quay.io/oauth2-proxy/oauth2-proxy:v7.6.0
    ports:
      - "127.0.0.1:4180:4180"
    env_file:
      - ./.env
    environment:
      OAUTH2_PROXY_PROVIDER: google
      OAUTH2_PROXY_SCOPE: "openid email profile"
      OAUTH2_PROXY_REDIRECT_URL: "${FUNNEL_HOST}/oauth2/callback"
      OAUTH2_PROXY_WHITELIST_DOMAINS: "${FUNNEL_HOSTNAME}"
      OAUTH2_PROXY_UPSTREAMS: "http://192.168.1.2:80/admin/"
      OAUTH2_PROXY_HTTP_ADDRESS: "0.0.0.0:4180"
      OAUTH2_PROXY_REVERSE_PROXY: "true"
      OAUTH2_PROXY_PASS_USER_HEADERS: "true"
      OAUTH2_PROXY_PREFER_EMAIL_TO_USER: "true"
      OAUTH2_PROXY_SET_XAUTHREQUEST: "true"
      OAUTH2_PROXY_AUTHENTICATED_EMAILS_FILE: "/etc/oauth2-proxy/emails.txt"
      OAUTH2_PROXY_SKIP_PROVIDER_BUTTON: "true"
      OAUTH2_PROXY_COOKIE_SECURE: "true"
      OAUTH2_PROXY_COOKIE_SAMESITE: "lax"
    volumes:
      - ./emails.txt:/etc/oauth2-proxy/emails.txt:ro
    restart: unless-stopped
```

#### Troubleshooting External Service Connections

**Test connectivity from within the OAuth2 proxy container:**

```bash
# Test if the proxy can reach your external service
docker compose exec oauth2-proxy wget -qO- http://host.docker.internal:8080

# Check if a specific IP is reachable
docker compose exec oauth2-proxy ping 192.168.1.100

# Test with curl
docker compose exec oauth2-proxy curl -I http://192.168.1.100:3000
```

**Common connection issues:**

1. **Linux host services**: Use `http://172.17.0.1:PORT` or `network_mode: "host"`
2. **Firewall blocking**: Ensure the external service allows connections from Docker networks
3. **Service binding**: External service must bind to `0.0.0.0:PORT`, not `127.0.0.1:PORT`
4. **Network isolation**: Add external services to the same Docker network if needed

**Check Docker network configuration:**

```bash
# See available networks
docker network ls

# Inspect the default network
docker network inspect bridge

# Find Docker's gateway IP (usually 172.17.0.1 on Linux)
docker compose exec oauth2-proxy route -n
```

### Method 3: Using NGINX for Advanced Routing

For more complex routing scenarios, add an NGINX reverse proxy:

**Step 1:** Create `nginx/nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream main_app {
        server app:8000;
    }
    
    upstream admin_app {
        server admin-app:3000;
    }
    
    upstream api_app {
        server api-app:5000;
    }

    server {
        listen 8080;
        
        # Main application
        location / {
            proxy_pass http://main_app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        # Admin application
        location /admin/ {
            proxy_pass http://admin_app/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        # API application
        location /api/ {
            proxy_pass http://api_app/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

**Step 2:** Update `docker-compose.yml`:

```yaml
services:
  # Your applications
  app:
    build: ./app
    expose:
      - "8000"
    restart: unless-stopped

  admin-app:
    image: your-admin-app:latest
    expose:
      - "3000"
    restart: unless-stopped

  api-app:
    image: your-api-app:latest
    expose:
      - "5000"
    restart: unless-stopped

  # NGINX reverse proxy
  nginx:
    image: nginx:alpine
    expose:
      - "8080"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - app
      - admin-app
      - api-app
    restart: unless-stopped

  # OAuth2 proxy pointing to NGINX
  oauth2-proxy:
    image: quay.io/oauth2-proxy/oauth2-proxy:v7.6.0
    ports:
      - "127.0.0.1:4180:4180"
    env_file:
      - ./.env
    environment:
      OAUTH2_PROXY_PROVIDER: google
      OAUTH2_PROXY_SCOPE: "openid email profile"
      OAUTH2_PROXY_REDIRECT_URL: "${FUNNEL_HOST}/oauth2/callback"
      OAUTH2_PROXY_WHITELIST_DOMAINS: "${FUNNEL_HOSTNAME}"
      OAUTH2_PROXY_UPSTREAMS: "http://nginx:8080"  # Point to NGINX
      OAUTH2_PROXY_HTTP_ADDRESS: "0.0.0.0:4180"
      OAUTH2_PROXY_REVERSE_PROXY: "true"
      OAUTH2_PROXY_PASS_USER_HEADERS: "true"
      OAUTH2_PROXY_PREFER_EMAIL_TO_USER: "true"
      OAUTH2_PROXY_SET_XAUTHREQUEST: "true"
      OAUTH2_PROXY_AUTHENTICATED_EMAILS_FILE: "/etc/oauth2-proxy/emails.txt"
      OAUTH2_PROXY_SKIP_PROVIDER_BUTTON: "true"
      OAUTH2_PROXY_COOKIE_SECURE: "true"
      OAUTH2_PROXY_COOKIE_SAMESITE: "lax"
    volumes:
      - ./emails.txt:/etc/oauth2-proxy/emails.txt:ro
    depends_on:
      - nginx
    restart: unless-stopped
```

### Method 4: Different Authentication for Different Apps

Configure different authentication rules for different paths:

```yaml
# OAuth2 proxy with path-specific configuration
oauth2-proxy:
  image: quay.io/oauth2-proxy/oauth2-proxy:v7.6.0
  ports:
    - "127.0.0.1:4180:4180"
  env_file:
    - ./.env
  environment:
    OAUTH2_PROXY_PROVIDER: google
    OAUTH2_PROXY_SCOPE: "openid email profile"
    OAUTH2_PROXY_REDIRECT_URL: "${FUNNEL_HOST}/oauth2/callback"
    OAUTH2_PROXY_WHITELIST_DOMAINS: "${FUNNEL_HOSTNAME}"
    OAUTH2_PROXY_UPSTREAMS: "http://nginx:8080"
    OAUTH2_PROXY_HTTP_ADDRESS: "0.0.0.0:4180"
    OAUTH2_PROXY_REVERSE_PROXY: "true"
    OAUTH2_PROXY_PASS_USER_HEADERS: "true"
    OAUTH2_PROXY_PREFER_EMAIL_TO_USER: "true"
    OAUTH2_PROXY_SET_XAUTHREQUEST: "true"
    # Different email files for different paths
    OAUTH2_PROXY_AUTHENTICATED_EMAILS_FILE: "/etc/oauth2-proxy/emails.txt"
    # Skip auth for public API endpoints
    OAUTH2_PROXY_SKIP_AUTH_REGEX: "^/api/public.*"
    # Require admin emails for admin paths
    OAUTH2_PROXY_SKIP_AUTH_STRIP_HEADERS: "false"
    OAUTH2_PROXY_COOKIE_SECURE: "true"
    OAUTH2_PROXY_COOKIE_SAMESITE: "lax"
  volumes:
    - ./emails.txt:/etc/oauth2-proxy/emails.txt:ro
    - ./admin-emails.txt:/etc/oauth2-proxy/admin-emails.txt:ro
  depends_on:
    - nginx
  restart: unless-stopped
```

---

## Integration Examples

### Example 1: Protecting a Grafana Instance

```yaml
services:
  grafana:
    image: grafana/grafana:latest
    expose:
      - "3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana-data:/var/lib/grafana
    restart: unless-stopped

  oauth2-proxy:
    image: quay.io/oauth2-proxy/oauth2-proxy:v7.6.0
    ports:
      - "127.0.0.1:4180:4180"
    env_file:
      - ./.env
    environment:
      OAUTH2_PROXY_PROVIDER: google
      OAUTH2_PROXY_SCOPE: "openid email profile"
      OAUTH2_PROXY_REDIRECT_URL: "${FUNNEL_HOST}/oauth2/callback"
      OAUTH2_PROXY_WHITELIST_DOMAINS: "${FUNNEL_HOSTNAME}"
      OAUTH2_PROXY_UPSTREAMS: "http://grafana:3000"  # Point to Grafana
      OAUTH2_PROXY_HTTP_ADDRESS: "0.0.0.0:4180"
      OAUTH2_PROXY_REVERSE_PROXY: "true"
      OAUTH2_PROXY_PASS_USER_HEADERS: "true"
      OAUTH2_PROXY_PREFER_EMAIL_TO_USER: "true"
      OAUTH2_PROXY_SET_XAUTHREQUEST: "true"
      OAUTH2_PROXY_AUTHENTICATED_EMAILS_FILE: "/etc/oauth2-proxy/emails.txt"
      OAUTH2_PROXY_SKIP_PROVIDER_BUTTON: "true"
      OAUTH2_PROXY_COOKIE_SECURE: "true"
      OAUTH2_PROXY_COOKIE_SAMESITE: "lax"
    volumes:
      - ./emails.txt:/etc/oauth2-proxy/emails.txt:ro
    depends_on:
      - grafana
    restart: unless-stopped

volumes:
  grafana-data:
```

### Example 2: Protecting a Jupyter Notebook

```yaml
services:
  jupyter:
    image: jupyter/base-notebook:latest
    expose:
      - "8888"
    environment:
      - JUPYTER_ENABLE_LAB=yes
      - JUPYTER_TOKEN=""  # Disable token auth (OAuth2 handles it)
    volumes:
      - ./notebooks:/home/jovyan/work
    restart: unless-stopped

  oauth2-proxy:
    image: quay.io/oauth2-proxy/oauth2-proxy:v7.6.0
    ports:
      - "127.0.0.1:4180:4180"
    env_file:
      - ./.env
    environment:
      OAUTH2_PROXY_PROVIDER: google
      OAUTH2_PROXY_SCOPE: "openid email profile"
      OAUTH2_PROXY_REDIRECT_URL: "${FUNNEL_HOST}/oauth2/callback"
      OAUTH2_PROXY_WHITELIST_DOMAINS: "${FUNNEL_HOSTNAME}"
      OAUTH2_PROXY_UPSTREAMS: "http://jupyter:8888"  # Point to Jupyter
      OAUTH2_PROXY_HTTP_ADDRESS: "0.0.0.0:4180"
      OAUTH2_PROXY_REVERSE_PROXY: "true"
      OAUTH2_PROXY_PASS_USER_HEADERS: "true"
      OAUTH2_PROXY_PREFER_EMAIL_TO_USER: "true"
      OAUTH2_PROXY_SET_XAUTHREQUEST: "true"
      OAUTH2_PROXY_AUTHENTICATED_EMAILS_FILE: "/etc/oauth2-proxy/emails.txt"
      OAUTH2_PROXY_SKIP_PROVIDER_BUTTON: "true"
      OAUTH2_PROXY_COOKIE_SECURE: "true"
      OAUTH2_PROXY_COOKIE_SAMESITE: "lax"
    volumes:
      - ./emails.txt:/etc/oauth2-proxy/emails.txt:ro
    depends_on:
      - jupyter
    restart: unless-stopped
```

### Example 3: Protecting Multiple Services (Home Lab Setup)

```yaml
services:
  # Portainer for Docker management
  portainer:
    image: portainer/portainer-ce:latest
    expose:
      - "9000"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - portainer-data:/data
    restart: unless-stopped

  # Uptime Kuma for monitoring
  uptime-kuma:
    image: louislam/uptime-kuma:latest
    expose:
      - "3001"
    volumes:
      - uptime-kuma-data:/app/data
    restart: unless-stopped

  # File browser
  filebrowser:
    image: filebrowser/filebrowser:latest
    expose:
      - "80"
    volumes:
      - ./files:/srv
      - filebrowser-data:/database
    restart: unless-stopped

  # NGINX for routing
  nginx:
    image: nginx:alpine
    expose:
      - "8080"
    volumes:
      - ./nginx/homelab.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - portainer
      - uptime-kuma
      - filebrowser
    restart: unless-stopped

  oauth2-proxy:
    image: quay.io/oauth2-proxy/oauth2-proxy:v7.6.0
    ports:
      - "127.0.0.1:4180:4180"
    env_file:
      - ./.env
    environment:
      OAUTH2_PROXY_PROVIDER: google
      OAUTH2_PROXY_SCOPE: "openid email profile"
      OAUTH2_PROXY_REDIRECT_URL: "${FUNNEL_HOST}/oauth2/callback"
      OAUTH2_PROXY_WHITELIST_DOMAINS: "${FUNNEL_HOSTNAME}"
      OAUTH2_PROXY_UPSTREAMS: "http://nginx:8080"
      OAUTH2_PROXY_HTTP_ADDRESS: "0.0.0.0:4180"
      OAUTH2_PROXY_REVERSE_PROXY: "true"
      OAUTH2_PROXY_PASS_USER_HEADERS: "true"
      OAUTH2_PROXY_PREFER_EMAIL_TO_USER: "true"
      OAUTH2_PROXY_SET_XAUTHREQUEST: "true"
      OAUTH2_PROXY_AUTHENTICATED_EMAILS_FILE: "/etc/oauth2-proxy/emails.txt"
      OAUTH2_PROXY_SKIP_PROVIDER_BUTTON: "true"
      OAUTH2_PROXY_COOKIE_SECURE: "true"
      OAUTH2_PROXY_COOKIE_SAMESITE: "lax"
    volumes:
      - ./emails.txt:/etc/oauth2-proxy/emails.txt:ro
    depends_on:
      - nginx
    restart: unless-stopped

volumes:
  portainer-data:
  uptime-kuma-data:
  filebrowser-data:
```

**Corresponding `nginx/homelab.conf`:**

```nginx
events {
    worker_connections 1024;
}

http {
    server {
        listen 8080;
        
        # Default redirect to main dashboard
        location = / {
            return 302 /portainer/;
        }
        
        # Portainer
        location /portainer/ {
            proxy_pass http://portainer:9000/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        # Uptime Kuma
        location /uptime/ {
            proxy_pass http://uptime-kuma:3001/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
        
        # File Browser
        location /files/ {
            proxy_pass http://filebrowser:80/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

---

## Advanced Security

### IP Restrictions

Add IP restrictions to `docker-compose.yml`:

```yaml
environment:
  OAUTH2_PROXY_TRUSTED_IPS: "192.168.1.0/24,10.0.0.0/8"
```

### Session Management

```yaml
environment:
  OAUTH2_PROXY_COOKIE_EXPIRE: "24h"
  OAUTH2_PROXY_COOKIE_REFRESH: "1h"
```

### Additional OAuth2 Scopes

```yaml
environment:
  OAUTH2_PROXY_SCOPE: "openid email profile"
```

### Role-Based Access

Create different email files for different access levels:

```bash
# Create admin-only access file
echo "admin@company.com" > admin-emails.txt

# Create developer access file
echo -e "dev1@company.com\ndev2@company.com" > dev-emails.txt
```

Then mount different files for different services:

```yaml
volumes:
  - ./admin-emails.txt:/etc/oauth2-proxy/emails.txt:ro  # Admin service
  # or
  - ./dev-emails.txt:/etc/oauth2-proxy/emails.txt:ro    # Dev service
```

---

## Configuration Tips

### Best Practices

1. **Always use `expose` instead of `ports`** for your applications - only the OAuth2 proxy should be accessible from the host
2. **Update dependencies** in `depends_on` when adding new services
3. **Test locally first** before enabling Tailscale Funnel:
   ```bash
   docker compose up -d --build
   curl -I http://localhost:4180  # Should redirect to Google
   ```
4. **Check logs** for any configuration issues:
   ```bash
   docker compose logs oauth2-proxy
   docker compose logs your-app-name
   ```

### Deployment After Changes

```bash
# Rebuild and restart all services
docker compose down
docker compose up -d --build

# Check that all services are running
docker compose ps

# Restart Tailscale Funnel if needed
tailscale funnel off
tailscale funnel 4180
```

### Troubleshooting Multiple Apps

```bash
# Check which services are running
docker compose ps

# Check specific service logs
docker compose logs service-name

# Test individual services
docker compose exec service-name curl localhost:port

# Check NGINX routing (if using NGINX)
docker compose exec nginx nginx -t
docker compose logs nginx
```

### Environment Variables for Multiple Apps

You can use different environment files for different configurations:

```bash
# Create environment files
cp .env .env.production
cp .env .env.development

# Use specific environment file
docker compose --env-file .env.production up -d
```

---

## Common Patterns

### Pattern 1: Main App + Admin Panel

```yaml
# Main user-facing application
app:
  build: ./app
  expose: ["8000"]

# Admin panel (restricted access)
admin:
  build: ./admin
  expose: ["3000"]

# Route /admin/ to admin service, everything else to main app
```

### Pattern 2: API + Frontend

```yaml
# React/Vue frontend
frontend:
  build: ./frontend
  expose: ["3000"]

# API backend
api:
  build: ./api
  expose: ["8000"]

# Route /api/ to backend, everything else to frontend
```

### Pattern 3: Microservices

```yaml
# User service
user-service:
  image: your-user-service
  expose: ["8001"]

# Order service
order-service:
  image: your-order-service
  expose: ["8002"]

# Payment service
payment-service:
  image: your-payment-service
  expose: ["8003"]

# Route /users/, /orders/, /payments/ to respective services
```

---

For questions or issues with these advanced configurations, please refer to the main README or open an issue on GitHub.
