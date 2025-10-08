"""Application configuration helpers."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import os


def _to_bool(value: object, default: bool = False) -> bool:
    """Convert environment values to booleans."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "t", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """Structured application settings."""

    secret_key: str
    routes_db_path: str
    emails_file: str
    health_check_enabled: bool
    health_check_interval: int
    upstream_ssl_verify: bool


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings sourced from environment variables."""
    base_dir = Path(__file__).resolve().parent
    env = os.environ

    secret_key = env.get("SECRET_KEY", "dev-secret-key-change-in-production")

    default_routes_path = base_dir / "routes.json"
    routes_db_path = env.get("ROUTES_DB_PATH", str(default_routes_path))

    default_emails_path = base_dir / "emails.txt"
    emails_file = env.get("EMAILS_FILE", str(default_emails_path))

    health_check_enabled = _to_bool(env.get("HEALTH_CHECK_ENABLED"), default=True)

    try:
        interval = int(env.get("HEALTH_CHECK_INTERVAL", 300))
    except (TypeError, ValueError):
        interval = 300
    health_check_interval = max(0, interval)

    upstream_ssl_verify = _to_bool(env.get("UPSTREAM_SSL_VERIFY"), default=False)

    return Settings(
        secret_key=secret_key,
        routes_db_path=routes_db_path,
        emails_file=emails_file,
        health_check_enabled=health_check_enabled,
        health_check_interval=health_check_interval,
        upstream_ssl_verify=upstream_ssl_verify,
    )
