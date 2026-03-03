"""Application-wide constants to replace magic numbers and strings."""


class Limits:
    MAX_LOG_ENTRIES = 200
    LOG_MESSAGE_MAX_LEN = 500
    ROUTE_TEST_COOLDOWN_SEC = 30
    SYNC_DEBOUNCE_SEC = 1.0
    SYNC_LOCK_TIMEOUT_SEC = 30
    HEALTH_POOL_WORKERS = 5
    HEALTH_FUTURE_TIMEOUT_SEC = 10
    HEALTH_BACKOFF_MAX_SEC = 1800


class RateLimits:
    ROUTES_READ = "100 per hour"
    ROUTES_WRITE = "50 per hour"
    ROUTE_TEST = "10 per hour"
    EMAILS_READ = "100 per hour"
    EMAILS_WRITE = "20 per hour"
    EMAILS_UPDATE = "10 per hour"
    EMAILS_REFRESH = "10 per hour"
    LOGS_READ = "30 per minute"


class Defaults:
    PORT = 8000
    PROTOCOL = "http"
    TARGET_PATH = "/"
    TIMEOUT = 30
    HEALTH_CHECK_INTERVAL = 300
