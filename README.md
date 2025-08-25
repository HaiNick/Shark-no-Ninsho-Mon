# public url + google login via tailscale funnel + oauth2-proxy

minimal, repeatable doc for future you (works on your Pi 5 / Debian 12)

## 0. prerequisites

* tailscale installed, logged in, and Funnel enabled for your tailnet.
* docker and docker compose installed.
* you have a Google account to allow.

Sanity:

```bash
tailscale status
docker --version
docker compose version
```

## 1. pick your public host

You will publish oauth2-proxy on localhost:4180 and let Funnel expose it as:

```
https://<your-host>.<your-tailnet>.ts.net
```

Example you used: `https://sharky.snowy-burbot.ts.net`

Keep that exact host string handy.

## 2. create Google OAuth client (one-time per host)

Console path changes sometimes; gist stays the same.

1. Open Google Cloud Console and select or create a project.
2. Consent screen:

   * User type: External.
   * Fill basic fields.
   * Scopes: only `openid`, `email`, `profile`.
   * For private use, keep it in Testing and add your Gmail under Test users; or switch to In production later (still fine with basic scopes).
3. Credentials -> Create credentials -> OAuth client ID

   * Application type: Web application.
   * Authorized redirect URI:
     `https://<your-host>.<your-tailnet>.ts.net/oauth2/callback`

Copy Client ID and Client Secret. You will not commit them.

## 3. project layout

```
project-root/
  emails.txt
  docker-compose.yml
  .env           # holds secrets, not committed
  app/
    Dockerfile
    requirements.txt
    app.py
```

## 4. allowed users

Put the exact Google accounts (one per line):

```
# file: emails.txt
your.primary@gmail.com
optional.second@gmail.com   # break-glass recommended
```

## 5. secrets and config

Create `.env` (do not commit it):

```bash
# file: .env
OAUTH2_PROXY_CLIENT_ID=copy-from-google
OAUTH2_PROXY_CLIENT_SECRET=copy-from-google
# 32 random bytes, base64. Generate with the command below and paste:
OAUTH2_PROXY_COOKIE_SECRET=REPLACE_WITH_32BYTE_BASE64
# public host used by Funnel
FUNNEL_HOST=https://<your-host>.<your-tailnet>.ts.net
FUNNEL_HOSTNAME=<your-host>.<your-tailnet>.ts.net
```

Generate cookie secret:

```bash
head -c 32 /dev/urandom | base64
```

## 6. docker-compose.yml

```yaml
version: "3.8"

services:
  app:
    build: ./app
    expose:
      - "8000"              # internal only; do not publish
    restart: unless-stopped

  oauth2-proxy:
    image: quay.io/oauth2-proxy/oauth2-proxy:v7.6.0
    ports:
      - "127.0.0.1:4180:4180"  # Funnel proxies to this
    env_file:
      - ./.env
    environment:
      OAUTH2_PROXY_PROVIDER: google
      OAUTH2_PROXY_SCOPE: "openid email profile"
      OAUTH2_PROXY_REDIRECT_URL: "${FUNNEL_HOST}/oauth2/callback"
      OAUTH2_PROXY_WHITELIST_DOMAINS: "${FUNNEL_HOSTNAME}"
      OAUTH2_PROXY_UPSTREAMS: "http://app:8000"
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
    restart: unless-stopped
```

## 7. flask test app

Dockerfile:

```dockerfile
# file: app/Dockerfile
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
CMD ["gunicorn", "-b", "0.0.0.0:8000", "-w", "2", "app:app"]
```

requirements.txt:

```
# file: app/requirements.txt
flask==3.0.3
gunicorn==22.0.0
```

app.py:

```python
# file: app/app.py
from flask import Flask, request, jsonify
app = Flask(__name__)

def get_email():
    return (request.headers.get("X-Forwarded-Email")
            or request.headers.get("X-Auth-Request-Email")
            or request.headers.get("X-Forwarded-User"))

@app.route("/")
def index():
    email = get_email()
    return f"""<html><body>
      <h1>It works</h1>
      <p>Authenticated as: {email}</p>
      <p>See <a href="/api/whoami">/api/whoami</a> and <a href="/headers">/headers</a>.</p>
    </body></html>"""

@app.route("/api/whoami")
def whoami():
    return jsonify({
        "email": get_email(),
        "remote_addr": request.headers.get("X-Real-IP") or request.remote_addr,
    })

@app.route("/headers")
def headers():
    wanted = [
        "X-Forwarded-Email","X-Forwarded-User","X-Auth-Request-Email",
        "X-Forwarded-Proto","X-Forwarded-Host","X-Forwarded-Uri","X-Real-IP"
    ]
    return "<pre>" + "\n".join(f"{k}: {request.headers.get(k)}" for k in wanted) + "</pre>"
```

## 8. build and start

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f oauth2-proxy
```

You should see oauth2-proxy listening on 0.0.0.0:4180 and loading emails.txt.

## 9. publish with tailscale funnel

```bash
tailscale funnel 4180
# or keep it running in background:
# tailscale funnel --bg 4180
```

CLI outputs your public URL. It should match `FUNNEL_HOST`.

## 10. verify

Open:

* `https://<your-host>.<your-tailnet>.ts.net` -> redirected to Google -> sign in with an email from emails.txt.
* `https://<host>/api/whoami` -> JSON with your email.
* `https://<host>/headers` -> sanity headers.

CLI checks:

```bash
tailscale funnel status
ss -tulpen | grep 4180
```

## 11. stop and clean up

Turn off Funnel:

```bash
tailscale funnel off
# or: tailscale funnel 4180 off
tailscale funnel status
```

Stop containers:

```bash
docker compose down
# or keep state but stop:
# docker compose stop
```

Optional cleanup:

```bash
docker compose down --volumes --rmi local
```

## 12. common failures and fast fixes

* redirect\_uri\_mismatch

  * Google Console redirect must be exactly `https://<host>/oauth2/callback`.
  * `OAUTH2_PROXY_REDIRECT_URL` must match it exactly.
* authenticated but headers missing

  * Ensure `OAUTH2_PROXY_PASS_USER_HEADERS=true` and `OAUTH2_PROXY_SET_XAUTHREQUEST=true`.
  * In your app, read `X-Forwarded-User` as fallback.
* bypass risk

  * Do not publish the app service. Only `expose: 8000` is allowed; no `ports:` on `app`.
* testing-mode reconsent

  * External + Testing requires re-consent every 7 days for Test users. If that annoys you, set consent screen to In production while keeping scopes to `openid email profile`.

## 13. security notes

* Store secrets in `.env`, not in compose. Rotate Google Client Secret if you ever leak it.
* Add a second allowed email in `emails.txt` as break-glass to avoid lockout.
* Keep the upstream app private to your docker network; all public traffic must pass oauth2-proxy.
* Consider basic app hardening: update images regularly, minimal scopes, logs review.

## 14. alternatives and when to use them

* private only (no Internet): skip Funnel, use `tailscale serve` and Tailscale identity headers inside the tailnet.
* many users or complex policy: use an access broker (e.g., OIDC/OAuth proxy with groups, country blocks, per-path rules). You can still front it with Funnel.

## 15. intellectual sparring (assumptions, counterarguments, stress test, other lenses)

* hidden assumptions

  * Assuming public exposure is necessary. If the audience is just you, tailnet-only Serve is simpler and removes public surface.
  * Assuming a single Google account is always available. If it is locked or 2FA breaks, you are locked out. Keep a break-glass user.
* counterarguments

  * "Network-layer auth via Tailscale ACLs is enough." For Internet users, you are not on the tailnet, so you need app-layer auth. oauth2-proxy provides that cleanly.
  * "Why not put the app directly on the Internet with Google login?" You can, but Funnel saves you from managing TLS and public networking yourself.
* stress-test the logic

  * If someone can reach the upstream app directly (e.g., host port published, or another reverse proxy), they bypass OAuth. Verify there is no listener except 127.0.0.1:4180.
  * Tokens and cookies: basic scopes avoid Google verification; if you add sensitive scopes later, you may trigger verification requirements.
* other lenses

  * Observability: add `docker compose logs -f` tailing and maybe a small `/healthz` in the app.
  * Persistence: if you want Funnel to survive reboots, use `tailscale funnel --bg 4180` under a systemd service that restarts tailscaled first.

That is it. Save this doc with your project, and you can recreate the stack in a few minutes. If you want, I can package this into a single shell script that scaffolds the files and prints a final checklist.