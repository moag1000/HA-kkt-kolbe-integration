"""Tuya BLE pairing protocol constants.

Reverse-engineered from KKT.Control v2.0.9 APK (com.KKTControl.com).
ThingClips SDK v4.4.0

STATUS: Experimental - NOT integrated into the main integration.
These constants document the Tuya BLE pairing protocol for future implementation.
"""

# =============================================================================
# KKT Control App Identity
# =============================================================================

KKT_APP_ID = "258744435"
KKT_PACKAGE_ID = "265726112"
KKT_APP_SCHEME = "KKTControl"
KKT_APP_ALIAS = "kkt.control"
KKT_BASE_VERSION = "odm/v7.0.0"

# OEM SDK encryption keys (from ThingNGConfig.java)
# NOTE: These are Mobile SDK keys, NOT Cloud API credentials
KKT_ENCRYPT_KEY_DEBUG = "f79qcwjp95y3krshvt8h"
KKT_ENCRYPT_SECRET_DEBUG = "cd55g3w8mfcvyp8tyqyev5w9wfch8qd7"
KKT_ENCRYPT_KEY_PROD = "eqcw9ycq7t7a4adk7dty"
KKT_ENCRYPT_SECRET_PROD = "7g7wvejdvae3k9s4qyxx3dvta5yh8ntg"

# Mini-app pairing entry points
KKT_QR_MINIAPP_BLE_WIFI = "entrykpb9a3qxkk5ol"
KKT_QR_MINIAPP_AP_MODE = "entryxa3aajgauptig"

# AP mode SSID prefix
KKT_AP_MODE_SSID = "SmartLife"

# =============================================================================
# BLE GATT Service & Characteristic UUIDs
# =============================================================================

# Telink BLE Mesh service (primary for Tuya devices)
UUID_TELINK_SERVICE = "00010203-0405-0607-0809-0a0b0c0d1910"
UUID_TELINK_PAIR = "00010203-0405-0607-0809-0a0b0c0d1914"
UUID_TELINK_COMMAND = "00010203-0405-0607-0809-0a0b0c0d1912"
UUID_TELINK_NOTIFY = "00010203-0405-0607-0809-0a0b0c0d1911"
UUID_TELINK_OTA = "00010203-0405-0607-0809-0a0b0c0d1913"

# Standard BLE Device Information Service
UUID_DEVICE_INFO_SERVICE = "0000180a-0000-1000-8000-00805f9b34fb"
UUID_FIRMWARE_REVISION = "00002a26-0000-1000-8000-00805f9b34fb"
UUID_MANUFACTURER_NAME = "00002a29-0000-1000-8000-00805f9b34fb"
UUID_MODEL_NUMBER = "00002a24-0000-1000-8000-00805f9b34fb"
UUID_HARDWARE_REVISION = "00002a27-0000-1000-8000-00805f9b34fb"

# Client Characteristic Configuration Descriptor (for enabling notifications)
UUID_CCCD = "00002902-0000-1000-8000-00805f9b34fb"

# Tuya BLE advertisement service UUID (for scanning)
TUYA_BLE_ADVERTISEMENT_UUID = 0xA201

# =============================================================================
# BLE Connection Types
# =============================================================================

CONNECT_TYPE_NORMAL = 0       # Normal reconnection to paired device
CONNECT_TYPE_ACTIVATOR = 1    # Initial pairing/activation
CONNECT_TYPE_PRECONNECT = 2   # Pre-connect for low power devices

# =============================================================================
# Security Levels
# =============================================================================

SECURITY_LEVEL_OLD = 0              # Legacy security (no ECDH)
SECURITY_LEVEL_OLD_NEED_UPDATE = 1  # Legacy, firmware update recommended
SECURITY_LEVEL_NEW = 2              # New ECDH-P256 based security

# =============================================================================
# ECDH Curve Types
# =============================================================================

CURVE_SECP_160_R1 = 0
CURVE_SECP_192_R1 = 1
CURVE_SECP_224_R1 = 2
CURVE_SECP_256_R1 = 3  # Primary curve used by Tuya
CURVE_SECP_256_K1 = 4

# ECDH public key size (uncompressed: 0x04 || X || Y)
ECDH_PUBLIC_KEY_SIZE = 65

# =============================================================================
# BLE Device Types (from advertisement)
# =============================================================================

BLE_TYPE_SINGLE_BLE = 100        # Pure BLE device
BLE_TYPE_WIFI = 200              # BLE+WiFi combo (KKT Kolbe devices)
BLE_TYPE_ZIGBEE = 300            # BLE+Zigbee combo
BLE_TYPE_THING_BEACON = 400      # Beacon device
BLE_TYPE_THING_BEACON_MESH = 500 # Beacon mesh

# =============================================================================
# Activation Modes
# =============================================================================

ACTIVATE_MODE_EZ = 1              # SmartConfig/EZ mode
ACTIVATE_MODE_AP = 2              # Access Point mode
ACTIVATE_MODE_SINGLE_BLE = 9     # Pure BLE device pairing
ACTIVATE_MODE_BLE_WIFI = 10      # BLE+WiFi combo (primary for KKT)
ACTIVATE_MODE_MULT_MODE = 20     # Multi-mode with fallback
ACTIVATE_MODE_BLE_WIFI_FIRST = 23 # BLE+WiFi, BLE priority
ACTIVATE_MODE_BLE_WIFI_BATCH = 33 # Batch BLE+WiFi pairing

# =============================================================================
# SupportType Flags (from advertisement flag byte)
# =============================================================================

SUPPORT_5G = 1
SUPPORT_PRODUCT_KEY = 2
SUPPORT_SHARE = 4
SUPPORT_PLUG_PLAY = 8
SUPPORT_QR_DEVICE = 16
SUPPORT_ADVERTISE_MAC = 32
SUPPORT_BIND = 128
SUPPORT_PRE_WIFI_LIST = 256
SUPPORT_SECURITY_SUPPORT = 512
SUPPORT_SECURITY_ENABLE = 1024
SUPPORT_ETHERNET = 2048
SUPPORT_BEACON_WIFI = 4096

# =============================================================================
# BLE Operation Codes
# =============================================================================

BLE_OP_CONNECT = 1
BLE_OP_DISCONNECT = 2
BLE_OP_READ = 3
BLE_OP_WRITE = 4
BLE_OP_WRITE_NO_RSP = 5
BLE_OP_NOTIFY = 6
BLE_OP_UNNOTIFY = 7
BLE_OP_READ_RSSI = 8
BLE_OP_CONFIG_MTU = 9
BLE_OP_INDICATE = 10
BLE_OP_DISCOVERY_SERVICE = 24

# =============================================================================
# BLE Connection States
# =============================================================================

BLE_STATE_DISCONNECTED = 0
BLE_STATE_CONNECTING = 1
BLE_STATE_CONNECTED = 2
BLE_STATE_DISCONNECTING = 3
BLE_STATE_SERVICE_READY = 19
BLE_STATUS_CONNECTED = 16
BLE_STATUS_DISCONNECTED = 32

# =============================================================================
# BLE Request Results
# =============================================================================

BLE_RESULT_SUCCESS = 0
BLE_RESULT_FAILED = -1
BLE_RESULT_CANCELED = -2
BLE_RESULT_ILLEGAL_ARGUMENT = -3
BLE_RESULT_NOT_SUPPORTED = -4
BLE_RESULT_BLUETOOTH_DISABLED = -5
BLE_RESULT_SERVICE_UNREADY = -6
BLE_RESULT_TIMEOUT = -7
BLE_RESULT_OVERFLOW = -8
BLE_RESULT_DENIED = -9
BLE_RESULT_EXCEPTION = -10

# =============================================================================
# WiFi Config Result Codes
# =============================================================================

WIFI_RESULT_CONNECT_SUCCESS = 0
WIFI_RESULT_DATA_FORMAT_ERROR = 1
WIFI_RESULT_SSID_NOT_FOUND = 2
WIFI_RESULT_PASSWORD_ERROR = 3
WIFI_RESULT_CONNECT_ROUTER_ERROR = 4
WIFI_RESULT_DHCP_ERROR = 5
WIFI_RESULT_CONNECT_FAILED = 6
WIFI_RESULT_URL_ERROR = 7
WIFI_RESULT_ACTIVATE_ERROR = 8
WIFI_RESULT_ACTIVATE_SUCCESS = 9

WIFI_RESULT_NAMES = {
    0: "Connected to WiFi successfully",
    1: "Data format error",
    2: "WiFi SSID not found",
    3: "WiFi password incorrect",
    4: "Failed to connect to router",
    5: "DHCP lease failed",
    6: "Network connection failed",
    7: "Cloud URL resolution failed",
    8: "Cloud activation failed",
    9: "Cloud activation succeeded",
}

# =============================================================================
# Packet Framing
# =============================================================================

BLE_DEFAULT_MTU = 23           # Standard BLE MTU
BLE_PAYLOAD_SIZE = 20          # 23 - 3 byte ATT header
BLE_PACKET_TYPE_CMD = 0        # Command packet
BLE_PACKET_TYPE_ACK = 1        # Acknowledgment packet

# Activation status notification command ID
ACTIVATION_STATUS_CMD_ID = 0x801F  # 32799

# =============================================================================
# Device Capability Bits
# =============================================================================

CAP_CONTROL_DURING_OTA = 1 << 0
CAP_LOW_POWER = 1 << 1
CAP_SUPPORT_BEACON = 1 << 2
CAP_HAS_LINK_ENCRYPT = 1 << 3
CAP_SUPPORT_TIMING = 1 << 5
CAP_BT_MULTI_MODE = 1 << 6
CAP_LINK_ENCRYPT = 1 << 7
CAP_SUPPORT_PSK = 1 << 8
CAP_SUPPORT_FITTING = 1 << 9
CAP_SUPPORT_SPLIT_OTA = 1 << 10
CAP_GW_CONNECT_MODE = 1 << 13
CAP_LEADER_FOLLOW = 1 << 15
CAP_SUPPORT_BOOT_OTA = 1 << 17
CAP_BLE_LAN = 1 << 18
CAP_BLE_STRUCT_DP = 1 << 19

# =============================================================================
# Cloud API Endpoints for BLE Pairing
# =============================================================================

API_DEVICE_LIST_TOKEN = "thing.m.device.list.token"            # v5.0 - Get activation token
API_DEVICE_TOKEN_CREATE = "thing.m.device.token.create"        # v1.0 - Create pairing token
API_DEVICE_AUTH_KEY_GET = "m.thing.device.auth.key.get"        # v3.0 - Get BLE auth key
API_DEVICE_AUTH_KEY_GET_V2 = "thing.m.device.auth.key.get"     # v2.0 - Alt auth key
API_DEVICE_RESET_KEY_GET = "m.thing.device.reset.key.get"      # v1.0 - Get reset key
API_DEVICE_KEYS_CREATE = "m.thing.device.keys.get.create"      # v1.0 - Create/get keys
API_DEVICE_REGISTER = "thing.m.device.register"                # v1.0 - Register device
API_DEVICE_ACTIVE = "thing.m.device.active"                    # v1.0 - Activate device
API_DEVICE_BLU_ACTIVE = "m.thing.device.blu.active"            # v2.0 - BLE activation
API_DEVICE_BLU_PREACTIVE = "thing.m.device.blu.preactive"      # v2.0 - BLE pre-activation
API_DEVICE_BIND_STATUS = "m.thing.device.bind.status.get"      # v2.0 - Check bind status
API_DEVICE_SECURITY_CONFIG = "thing.m.device.security.config.all"  # v1.0 - Security config

# Security/Certificate APIs
API_SEC_SERVER_CERT = "thing.device.sec.servercert.fetch"      # v1.0 - Server CA cert
API_SEC_DEVICE_CERT = "thing.device.sec.devcert.validate"      # v1.0 - Validate device cert
API_SEC_CERT_PPK = "thing.device.sec.devcert.ppk.validate"     # v1.0 - Validate cert PPK
API_SEC_RANDOM_ENCRYPT = "thing.device.sec.random.encrypt"     # v1.0 - Random encryption

# =============================================================================
# BLE Connect Ability (how device communicates)
# =============================================================================

BLE_CONNECT_BLE_AND_GATEWAY = 0  # Can connect via BLE and gateway
BLE_CONNECT_GATEWAY_ONLY = 1     # Gateway only
BLE_CONNECT_BLE_ONLY = 2         # BLE only

# =============================================================================
# Channel State Machine (for reliable BLE data transfer)
# =============================================================================

CHANNEL_IDLE = "IDLE"
CHANNEL_READY = "READY"
CHANNEL_WAIT_START_ACK = "WAIT_START_ACK"
CHANNEL_WRITING = "WRITING"
CHANNEL_SYNC = "SYNC"
CHANNEL_SYNC_ACK = "SYNC_ACK"
CHANNEL_SYNC_WAIT_PACKET = "SYNC_WAIT_PACKET"
CHANNEL_READING = "READING"

# Channel result codes
CHANNEL_SUCCESS = 0
CHANNEL_FAIL = -1
CHANNEL_TIMEOUT = -2
CHANNEL_BUSY = -3

# =============================================================================
# Default Timeouts
# =============================================================================

BLE_CONNECT_TIMEOUT_MS = 40000    # 40 seconds for BLE connection
BLE_ACTIVATE_TIMEOUT_S = 60      # 60 seconds for activation
BLE_LOW_POWER_PRECONNECT_DURATION = 10  # seconds
BLE_LOW_POWER_SESSION_MIN_COUNT = 3
