"""Validation helpers for KKT Kolbe config flows."""
from __future__ import annotations

import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)


def is_valid_ip(ip_address: str) -> bool:
    """Validate IP address format.

    Args:
        ip_address: The IP address string to validate.

    Returns:
        True if valid IPv4 address, False otherwise.
    """
    if not ip_address:
        return False
    try:
        parts = ip_address.split(".")
        if len(parts) != 4:
            return False
        for part in parts:
            num = int(part)
            if not 0 <= num <= 255:
                return False
        return True
    except (ValueError, AttributeError):
        return False


def is_valid_device_id(device_id: str) -> bool:
    """Validate Tuya device ID format.

    Device IDs are typically 20+ alphanumeric characters.

    Args:
        device_id: The device ID string to validate.

    Returns:
        True if valid device ID format, False otherwise.
    """
    if not device_id:
        return False
    return len(device_id) >= 20 and device_id.isalnum()


def is_valid_local_key(local_key: str) -> bool:
    """Validate Tuya local key format.

    Local keys are 16-character encryption keys.

    Args:
        local_key: The local key string to validate.

    Returns:
        True if valid local key format, False otherwise.
    """
    if not local_key:
        return False
    return len(local_key) >= 16


def is_private_ip(ip_address: str | None) -> bool:
    """Check if an IP address is a private/local network address.

    Returns True for:
    - 10.0.0.0/8 (Class A private)
    - 172.16.0.0/12 (Class B private)
    - 192.168.0.0/16 (Class C private)
    - 169.254.0.0/16 (Link-local)

    Args:
        ip_address: The IP address to check.

    Returns:
        True if IP is in private range, False otherwise.
    """
    import ipaddress as ipaddr

    if not ip_address:
        return False
    try:
        ip = ipaddr.ip_address(ip_address)
        return ip.is_private or ip.is_link_local
    except ValueError:
        return False


def validate_manual_input(user_input: dict[str, Any]) -> dict[str, str]:
    """Validate manual configuration input.

    Args:
        user_input: Dictionary containing user form input.

    Returns:
        Dictionary of field names to error keys.
    """
    errors: dict[str, str] = {}

    # Validate IP address
    ip_address = user_input.get("host", "").strip()
    if ip_address and not is_valid_ip(ip_address):
        errors["host"] = "invalid_ip"

    # Validate device ID
    device_id = user_input.get("device_id", "").strip()
    if device_id and not is_valid_device_id(device_id):
        errors["device_id"] = "invalid_device_id"

    return errors


def validate_api_credentials(user_input: dict[str, Any]) -> dict[str, str]:
    """Validate API credentials input.

    Args:
        user_input: Dictionary containing API credential input.

    Returns:
        Dictionary of field names to error keys.
    """
    errors: dict[str, str] = {}

    client_id = user_input.get("api_client_id", "").strip()
    client_secret = user_input.get("api_client_secret", "").strip()

    if not client_id:
        errors["api_client_id"] = "api_client_id_required"
    elif len(client_id) < 10:
        errors["api_client_id"] = "api_client_id_invalid"

    if not client_secret:
        errors["api_client_secret"] = "api_client_secret_required"
    elif len(client_secret) < 20:
        errors["api_client_secret"] = "api_client_secret_invalid"

    return errors


def validate_local_key_input(local_key: str) -> str | None:
    """Validate local key input and return error key if invalid.

    Args:
        local_key: The local key to validate.

    Returns:
        Error key string if invalid, None if valid.
    """
    if not local_key:
        return "invalid_local_key"
    if not is_valid_local_key(local_key):
        return "invalid_local_key"
    return None
