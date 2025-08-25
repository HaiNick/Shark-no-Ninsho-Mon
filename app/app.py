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
