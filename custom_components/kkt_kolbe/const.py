"""Constants for KKT Kolbe integration."""
from __future__ import annotations

DOMAIN = "kkt_kolbe"

MANUFACTURER = "KKT Kolbe"

# Connection stability configuration
DEFAULT_SCAN_INTERVAL = 30  # seconds
DEFAULT_CONNECTION_TIMEOUT = 15.0  # seconds
DEFAULT_STATUS_TIMEOUT = 10.0  # seconds
DEFAULT_SET_DP_TIMEOUT = 8.0  # seconds
DEFAULT_PROTOCOL_TIMEOUT = 3.0  # seconds
DEFAULT_RECONNECT_TEST_TIMEOUT = 5.0  # seconds

# Reconnection configuration
DEFAULT_BASE_BACKOFF = 5  # seconds
DEFAULT_MAX_BACKOFF = 300  # 5 minutes
DEFAULT_MAX_RECONNECT_ATTEMPTS = 10
DEFAULT_CONSECUTIVE_FAILURES_THRESHOLD = 3

# Adaptive intervals (during offline/reconnection)
ADAPTIVE_UPDATE_INTERVAL_OFFLINE = 120  # 2 minutes during offline
ADAPTIVE_UPDATE_INTERVAL_RECONNECTING = 60  # 1 minute during reconnection

# Circuit breaker configuration
CIRCUIT_BREAKER_SLEEP_INTERVAL = 3600  # 1 hour sleep when unreachable
CIRCUIT_BREAKER_MAX_SLEEP_RETRIES = 3  # Max retries per sleep cycle

# TCP Keep-Alive configuration
TCP_KEEPALIVE_IDLE = 60  # seconds before sending keepalive probes
TCP_KEEPALIVE_INTERVAL = 10  # seconds between keepalive probes
TCP_KEEPALIVE_COUNT = 5  # number of failed probes before declaring dead

# Global API storage key
GLOBAL_API_STORAGE_KEY = f"{DOMAIN}_global_api"

# API Configuration
CONF_API_CLIENT_ID = "api_client_id"
CONF_API_CLIENT_SECRET = "api_client_secret"
CONF_API_ENDPOINT = "api_endpoint"
CONF_API_ENABLED = "api_enabled"
CONF_INTEGRATION_MODE = "integration_mode"

# Default API endpoint
DEFAULT_API_ENDPOINT = "https://openapi.tuyaeu.com"

# Integration modes
MODE_MANUAL = "manual"
MODE_API_DISCOVERY = "api_discovery"
MODE_HYBRID = "hybrid"

# Device categories
CATEGORY_HOOD = "yyj"  # Dunstabzugshaube
CATEGORY_COOKTOP = "dcl"  # Induktionskochfeld

# Device models
MODELS = {
    "e1k6i0zo": {
        "name": "HERMES & STYLE",
        "category": CATEGORY_HOOD,
        "product_id": "ypaixllljc2dcpae",
    },
    "IND7705HC": {
        "name": "IND7705HC",
        "category": CATEGORY_COOKTOP,
        "product_id": "p8volecsgzdyun29",
    },
}

# Fan speed mappings
FAN_SPEEDS = {
    "off": 0,
    "low": 25,
    "middle": 50,
    "high": 75,
    "strong": 100,
}

FAN_SPEED_TO_DP = {
    0: "off",
    25: "low",
    50: "middle",
    75: "high",
    100: "strong",
}

# RGB Light modes
RGB_MODES = {
    0: "Off",
    1: "White",
    2: "Warm White",
    3: "Cool White",
    4: "Red",
    5: "Green",
    6: "Blue",
    7: "Yellow",
    8: "Purple",
    9: "Rainbow",
}