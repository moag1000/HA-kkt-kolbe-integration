"""Constants for KKT Kolbe integration."""
from __future__ import annotations

from typing import Final

# === VERSION ===
VERSION: Final = "3.0.8"

# === CORE IDENTIFIERS ===
DOMAIN: Final = "kkt_kolbe"
MANUFACTURER: Final = "KKT Kolbe"

# === CONNECTION STABILITY CONFIGURATION ===
DEFAULT_SCAN_INTERVAL: Final = 30  # seconds
DEFAULT_CONNECTION_TIMEOUT: Final = 15.0  # seconds
DEFAULT_STATUS_TIMEOUT: Final = 10.0  # seconds
DEFAULT_SET_DP_TIMEOUT: Final = 8.0  # seconds
DEFAULT_PROTOCOL_TIMEOUT: Final = 3.0  # seconds
DEFAULT_RECONNECT_TEST_TIMEOUT: Final = 5.0  # seconds

# === RECONNECTION CONFIGURATION ===
DEFAULT_BASE_BACKOFF: Final = 5  # seconds
DEFAULT_MAX_BACKOFF: Final = 300  # 5 minutes
DEFAULT_MAX_RECONNECT_ATTEMPTS: Final = 10
DEFAULT_CONSECUTIVE_FAILURES_THRESHOLD: Final = 3

# === ADAPTIVE INTERVALS ===
ADAPTIVE_UPDATE_INTERVAL_OFFLINE: Final = 120  # 2 minutes during offline
ADAPTIVE_UPDATE_INTERVAL_RECONNECTING: Final = 60  # 1 minute during reconnection

# === CIRCUIT BREAKER CONFIGURATION ===
CIRCUIT_BREAKER_SLEEP_INTERVAL: Final = 3600  # 1 hour sleep when unreachable
CIRCUIT_BREAKER_MAX_SLEEP_RETRIES: Final = 3  # Max retries per sleep cycle

# === TCP KEEP-ALIVE CONFIGURATION ===
TCP_KEEPALIVE_IDLE: Final = 60  # seconds before sending keepalive probes
TCP_KEEPALIVE_INTERVAL: Final = 10  # seconds between keepalive probes
TCP_KEEPALIVE_COUNT: Final = 5  # number of failed probes before declaring dead

# === GLOBAL STORAGE ===
GLOBAL_API_STORAGE_KEY: Final = f"{DOMAIN}_global_api"

# === API CONFIGURATION KEYS ===
CONF_API_CLIENT_ID: Final = "api_client_id"
CONF_API_CLIENT_SECRET: Final = "api_client_secret"
CONF_API_ENDPOINT: Final = "api_endpoint"
CONF_API_ENABLED: Final = "api_enabled"
CONF_INTEGRATION_MODE: Final = "integration_mode"

# === API DEFAULTS ===
DEFAULT_API_ENDPOINT: Final = "https://openapi.tuyaeu.com"

# === INTEGRATION MODES ===
MODE_MANUAL: Final = "manual"
MODE_API_DISCOVERY: Final = "api_discovery"
MODE_HYBRID: Final = "hybrid"

# === DEVICE CATEGORIES (Tuya) ===
CATEGORY_HOOD: Final = "yyj"  # Dunstabzugshaube
CATEGORY_COOKTOP: Final = "dcl"  # Induktionskochfeld

# === DEVICE MODELS ===
MODELS: Final[dict[str, dict[str, str]]] = {
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

# === FAN SPEED MAPPINGS ===
FAN_SPEEDS: Final[dict[str, int]] = {
    "off": 0,
    "low": 25,
    "middle": 50,
    "high": 75,
    "strong": 100,
}

FAN_SPEED_TO_DP: Final[dict[int, str]] = {
    0: "off",
    25: "low",
    50: "middle",
    75: "high",
    100: "strong",
}

# === RGB LIGHT MODES ===
# From HERMES manual: weiß > rot > grün > blau > gelb > lila > orange > cyan > grasgrün
# Device uses 1-based indexing for colors
RGB_MODES: Final[dict[int, str]] = {
    0: "Off",
    1: "White",
    2: "Red",
    3: "Green",
    4: "Blue",
    5: "Yellow",
    6: "Purple",
    7: "Orange",
    8: "Cyan",
    9: "Grass Green",
}