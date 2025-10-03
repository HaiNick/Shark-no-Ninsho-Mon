"""Development entry point - Runs Flask app with relaxed auth."""
from __future__ import annotations

import os
from pathlib import Path

# Ensure development-oriented environment variables are present
os.environ.setdefault('FLASK_ENV', 'development')
os.environ.setdefault('DEBUG', 'True')
os.environ.setdefault('DEV_MODE', 'true')

from config import get_settings

settings = get_settings()

# Make sure the development email exists so authorization checks succeed
emails_path = Path(settings.emails_file)
emails_path.parent.mkdir(parents=True, exist_ok=True)

if not emails_path.exists():
    emails_path.write_text('dev@localhost\n', encoding='utf-8')
else:
    existing = {line.strip().lower() for line in emails_path.read_text(encoding='utf-8').splitlines()}
    if 'dev@localhost' not in existing:
        with emails_path.open('a', encoding='utf-8') as handle:
            handle.write('dev@localhost\n')

from app import app, refresh_authorized_emails

refresh_authorized_emails()

if __name__ == '__main__':
    print('=' * 60)
    print('DEVELOPMENT MODE - Authentication Bypassed')
    print('=' * 60)
    print('URL: http://localhost:8000')
    print('Logged in as: dev@localhost')
    print('All routes accessible without OAuth2')
    print('=' * 60)
    print()

    app.run(host='0.0.0.0', port=8000, debug=True)
