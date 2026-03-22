"""Tuya Cloud API endpoints for BLE device pairing.

Reverse-engineered from KKT.Control v2.0.9 APK.
Documents the cloud-side API calls needed for BLE device activation.

STATUS: Documentation only - NOT functional code.
These API calls require valid Tuya OAuth tokens.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from constants import (
    API_DEVICE_AUTH_KEY_GET,
    API_DEVICE_BLU_ACTIVE,
    API_DEVICE_BLU_PREACTIVE,
    API_DEVICE_BIND_STATUS,
    API_DEVICE_LIST_TOKEN,
    API_DEVICE_REGISTER,
    API_SEC_DEVICE_CERT,
    API_SEC_RANDOM_ENCRYPT,
    API_SEC_SERVER_CERT,
)


# =============================================================================
# Data classes for API request/response
# =============================================================================


@dataclass
class ActivationToken:
    """Token returned by thing.m.device.list.token."""

    token: str
    secret: str
    region: str
    expire_time: int


@dataclass
class AuthKey:
    """Auth key returned by m.thing.device.auth.key.get."""

    dev_id: str
    uuid: str
    name: str
    icon_url: str
    encrypted_auth_key: str
    random: str
    reset_key: str
    error_code: int
    error_msg: str


@dataclass
class SecurityCert:
    """Server certificate from thing.device.sec.servercert.fetch."""

    public_key: str
    ca_signature: str


@dataclass
class ActivationResult:
    """Result from device activation."""

    local_key: str  # The key we need for local LAN control!
    sec_key: str
    verify_key: str
    beacon_key: str
    need_beacon_key: bool


@dataclass
class DeviceInfo:
    """Device info received over BLE after connection."""

    auth_key: str
    dev_id: str
    device_capability: int
    device_version: str
    hardware_version: str
    mcu_version: str
    protocol_version: str
    is_bind: bool
    enable_security: bool
    new_auth_key: str
    need_beacon_key: bool
    plug_play_flag: bool
    zigbee_mac: str
    combos_flag: int
    support_boot_ota: bool


# =============================================================================
# API call documentation
# =============================================================================

# The following documents the exact API calls the app makes during BLE pairing.
# Each entry shows the endpoint, version, parameters, and expected response.

PAIRING_API_FLOW = [
    {
        "step": 1,
        "name": "Get Activation Token",
        "api": API_DEVICE_LIST_TOKEN,
        "version": "5.0",
        "method": "POST",
        "params": {
            "homeId": "<user's home ID from SmartLife account>",
        },
        "response": {
            "token": "string - activation token",
            "secret": "string - token secret",
            "region": "string - cloud region (eu, us, cn, in)",
            "expire_time": "int - Unix timestamp",
        },
        "notes": "Must be called before BLE connection. Token is sent to device over BLE.",
    },
    {
        "step": 2,
        "name": "Check Bind Status (optional)",
        "api": API_DEVICE_BIND_STATUS,
        "version": "2.0",
        "method": "POST",
        "params": {
            "uuid": "<device UUID from BLE advertisement>",
            "mac": "<device MAC from BLE advertisement>",
            "encryptValue": "<encrypted value>",
        },
        "response": {
            "isBind": "bool - whether device is already bound",
        },
        "notes": "Optional check before attempting pairing. Prevents duplicate binds.",
    },
    {
        "step": 3,
        "name": "Get BLE Auth Key",
        "api": API_DEVICE_AUTH_KEY_GET,
        "version": "3.0",
        "method": "POST",
        "params": {
            "uuid": "<device UUID from BLE DeviceInfoRsp>",
            "mac": "<device MAC>",
        },
        "response": {
            "devId": "string",
            "uuid": "string",
            "name": "string - device display name",
            "iconUrl": "string - device icon URL",
            "encryptedAuthKey": "string - encrypted auth key to send to device",
            "random": "string - random value for key derivation",
            "resetKey": "string - factory reset key",
        },
        "notes": "The encryptedAuthKey is sent to the device over BLE. "
        "The device uses it together with its internal key to derive the session.",
    },
    {
        "step": "3a (if SECURITY_LEVEL_NEW)",
        "name": "Fetch Server Certificate",
        "api": API_SEC_SERVER_CERT,
        "version": "1.0",
        "method": "POST",
        "params": {},
        "response": {
            "publicKey": "string - server ECDSA public key",
            "caSignature": "string - CA signature",
        },
        "notes": "Only for devices with new security level. Used to validate device identity.",
    },
    {
        "step": "3b (if SECURITY_LEVEL_NEW)",
        "name": "Validate Device Certificate",
        "api": API_SEC_DEVICE_CERT,
        "version": "1.0",
        "method": "POST",
        "params": {
            "uuid": "<device UUID>",
            "devCert": "<certificate read from device over BLE>",
        },
        "response": {
            "result": "bool - whether certificate is valid",
        },
    },
    {
        "step": "3c (if SECURITY_LEVEL_NEW)",
        "name": "Encrypt Random Challenge",
        "api": API_SEC_RANDOM_ENCRYPT,
        "version": "1.0",
        "method": "POST",
        "params": {
            "random": "<random challenge string>",
        },
        "response": {
            "originalVal": "string - original random",
            "encryptedVal": "string - server-encrypted random",
        },
        "notes": "Challenge-response to verify server identity to the device.",
    },
    {
        "step": 4,
        "name": "BLE Device Activation",
        "api": API_DEVICE_BLU_ACTIVE,
        "version": "2.0",
        "method": "POST",
        "params": {
            "mac": "<device MAC>",
            "productId": "<Tuya product ID>",
            "timezone": "<timezone string, e.g. Europe/Berlin>",
            "bindUser": True,
            "isShare": False,
            "cloudPv": "<cloud protocol version>",
            "type": 4,  # BLE activation type
            "protocolOpt": "<protocol options>",
        },
        "response": {
            "localKey": "string - AES key for local LAN communication",
            "secKey": "string - security key",
            "verifyKey": "string - verification key",
            "beaconKey": "string - beacon encryption key",
            "needBeaconKey": "bool",
        },
        "notes": "This is the final step. The localKey is what we need for "
        "TinyTuya local communication. After this, the device is registered "
        "and can be controlled locally without cloud.",
    },
]


def print_pairing_flow() -> None:
    """Print the documented pairing API flow."""
    print("=" * 70)
    print("Tuya BLE Device Pairing - Cloud API Flow")
    print("=" * 70)

    for step in PAIRING_API_FLOW:
        print(f"\n--- Step {step['step']}: {step['name']} ---")
        print(f"  API:     {step['api']} (v{step['version']})")
        print(f"  Method:  {step['method']}")
        print(f"  Params:  {step['params']}")
        if step.get("notes"):
            print(f"  Notes:   {step['notes']}")

    print(f"\n{'=' * 70}")
    print("NOTE: The BLE-side crypto (ECDH key exchange, AES-CBC encryption)")
    print("between steps 2 and 4 has been reverse-engineered.")
    print("See session_key.py for the session key derivation and encrypt/decrypt.")
    print()
    print("REMAINING UNKNOWN: The exact mapping of ECDH shared secret to")
    print("made_session_key() arguments has not been confirmed with real traffic.")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    print_pairing_flow()
