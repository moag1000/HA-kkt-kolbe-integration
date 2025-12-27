"""Device detection helpers for KKT Kolbe integration."""
from __future__ import annotations

import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)


def detect_device_type_from_api(device: dict[str, Any]) -> tuple[str, str]:
    """Detect device type from Tuya API response.

    Uses multiple detection methods in order of accuracy:
    1. Tuya product_id match against KNOWN_DEVICES
    2. Device ID pattern matching
    3. Tuya category-based detection
    4. Keyword-based fallback

    Args:
        device: Device dict from Tuya API containing category, product_name,
                product_id, id, and name fields.

    Returns:
        Tuple of (device_type, internal_product_name)
        - device_type: Internal device key for entity lookup
        - internal_product_name: Product name for matching in KNOWN_DEVICES
    """
    from ..device_types import (
        find_device_by_product_name,
        find_device_by_device_id,
        KNOWN_DEVICES,
    )

    tuya_category = device.get("category", "").lower()
    api_product_name = device.get("product_name", "Unknown Device")
    product_id = device.get("product_id", "")
    device_id = device.get("id", "")
    device_name = device.get("name", "").lower()

    _LOGGER.debug(
        f"Device detection: product_id={product_id}, "
        f"device_id={device_id[:12] if device_id else 'N/A'}, "
        f"category={tuya_category}, product_name={api_product_name}"
    )

    # Method 1: Match by Tuya product_id (most accurate)
    if product_id:
        device_info = find_device_by_product_name(product_id)
        if device_info:
            for device_key, info in KNOWN_DEVICES.items():
                if product_id in info.get("product_names", []):
                    _LOGGER.info(f"Detected device by product_id: {device_key} ({product_id})")
                    return (device_key, product_id)

    # Method 2: Match by device_id pattern
    if device_id:
        device_info = find_device_by_device_id(device_id)
        if device_info:
            for device_key, info in KNOWN_DEVICES.items():
                # Check exact match
                if device_id in info.get("device_ids", []):
                    _LOGGER.info(f"Detected device by device_id: {device_key} ({device_id[:12]}...)")
                    return (device_key, info["product_names"][0])
                # Check pattern match
                for pattern in info.get("device_id_patterns", []):
                    if device_id.startswith(pattern):
                        _LOGGER.info(f"Detected device by device_id pattern: {device_key} ({pattern}*)")
                        return (device_key, info["product_names"][0])

    # Method 3: Category-based detection
    search_text = f"{api_product_name} {device_name}".lower()

    if tuya_category == "dcl":  # Cooktop category
        return ("ind7705hc_cooktop", "ind7705hc_cooktop")
    elif tuya_category == "yyj":  # Hood category
        if "solo" in search_text:
            return ("solo_hcm_hood", "bgvbvjwomgbisd8x")
        elif "ecco" in search_text:
            return ("ecco_hcm_hood", "gwdgkteknzvsattn")
        elif "flat" in search_text:
            return ("flat_hood", "luoxakxm2vm9azwu")
        elif "hermes" in search_text:
            return ("hermes_style_hood", "ypaixllljc2dcpae")
        else:
            return ("default_hood", "default_hood")

    # Method 4: Keyword-based fallback
    if "ind" in search_text or "cooktop" in search_text or "kochfeld" in search_text:
        return ("ind7705hc_cooktop", "ind7705hc_cooktop")
    elif any(kw in search_text for kw in ["hood", "hermes", "style", "ecco", "solo", "dunst", "abzug"]):
        if "solo" in search_text:
            return ("solo_hcm_hood", "bgvbvjwomgbisd8x")
        elif "ecco" in search_text:
            return ("ecco_hcm_hood", "gwdgkteknzvsattn")
        return ("default_hood", "default_hood")

    # Default: unknown
    return ("auto", api_product_name)


def detect_device_type_from_device_id(device_id: str) -> tuple[str, str, str]:
    """Detect device type from device_id only (for discovery without API).

    Uses device_id patterns from KNOWN_DEVICES to identify device type
    when no API data is available.

    Args:
        device_id: The Tuya device ID (20+ character alphanumeric string).

    Returns:
        Tuple of (device_type, product_name, friendly_name)
        - device_type: Internal device key
        - product_name: Product name for KNOWN_DEVICES lookup
        - friendly_name: Human-readable device name
    """
    from ..device_types import KNOWN_DEVICES

    if not device_id:
        return ("auto", "auto", "KKT Kolbe Device")

    _LOGGER.debug(f"Detecting device type from device_id: {device_id[:12]}...")

    # Check each known device for matches
    for device_key, info in KNOWN_DEVICES.items():
        # Check exact device_id match
        if device_id in info.get("device_ids", []):
            friendly_name = info.get("name", device_key)
            product_name = info["product_names"][0] if info.get("product_names") else device_key
            _LOGGER.info(f"Detected device by exact device_id: {device_key} -> {friendly_name}")
            return (device_key, product_name, friendly_name)

        # Check device_id pattern match
        for pattern in info.get("device_id_patterns", []):
            if device_id.startswith(pattern):
                friendly_name = info.get("name", device_key)
                product_name = info["product_names"][0] if info.get("product_names") else device_key
                _LOGGER.info(f"Detected device by pattern {pattern}*: {device_key} -> {friendly_name}")
                return (device_key, product_name, friendly_name)

    # No match found
    _LOGGER.debug(f"No device_id pattern matched for {device_id[:12]}, using defaults")
    return ("auto", "auto", "KKT Kolbe Device")


def get_device_type_options() -> list[dict[str, str]]:
    """Generate device type options from KNOWN_DEVICES.

    Creates a sorted list of device options for UI selectors,
    organized by category with specific devices first and
    generic/default options last.

    Returns:
        List of dicts with 'value' and 'label' keys for selector options.
    """
    from ..device_types import KNOWN_DEVICES, CATEGORY_HOOD, CATEGORY_COOKTOP

    options: list[dict[str, str]] = []
    hoods: list[dict[str, str]] = []
    cooktops: list[dict[str, str]] = []
    default_options: list[dict[str, str]] = []

    for device_key, device_info in KNOWN_DEVICES.items():
        category = device_info.get("category", "")
        name = device_info.get("name", device_key)

        if device_key == "default_hood":
            default_options.append({
                "value": device_key,
                "label": "Default Hood - Generic Range Hood (if model unknown)"
            })
        elif category == CATEGORY_HOOD:
            hoods.append({"value": device_key, "label": name})
        elif category == CATEGORY_COOKTOP:
            cooktops.append({"value": device_key, "label": name})

    # Sort alphabetically
    hoods.sort(key=lambda x: x["label"])
    cooktops.sort(key=lambda x: x["label"])

    # Build final list: specific hoods, cooktops, then defaults
    options.extend(hoods)
    options.extend(cooktops)
    options.extend(default_options)

    return options


def detect_device_type_from_product_key(product_key: str, device_id: str = "") -> tuple[str, str]:
    """Detect device type from product key (from UDP discovery).

    Uses the product_key broadcast by Tuya devices to identify the device type.
    Falls back to device_id pattern matching if product_key doesn't match.

    Args:
        product_key: The productKey from UDP broadcast.
        device_id: Optional device ID for fallback pattern matching.

    Returns:
        Tuple of (device_type, friendly_name)
    """
    from ..device_types import KNOWN_DEVICES

    if not product_key:
        # Try device_id fallback
        if device_id:
            device_type, _, friendly_name = detect_device_type_from_device_id(device_id)
            return (device_type, friendly_name)
        return ("auto", "KKT Kolbe Device")

    _LOGGER.debug(f"Detecting device type from product_key: {product_key}")

    # Check if product_key matches any known device's product_names
    for device_key, info in KNOWN_DEVICES.items():
        if product_key in info.get("product_names", []):
            friendly_name = info.get("name", device_key)
            _LOGGER.info(f"Detected device by product_key: {product_key} -> {friendly_name}")
            return (device_key, friendly_name)

    # Try keyword-based detection from product_key
    product_lower = product_key.lower()

    if "ind" in product_lower or "cooktop" in product_lower or "dcl" in product_lower:
        _LOGGER.info(f"Detected cooktop from product_key keywords: {product_key}")
        return ("ind7705hc_cooktop", "IND7705HC Induction Cooktop")

    if any(kw in product_lower for kw in ["hermes", "style", "hood", "yyj"]):
        _LOGGER.info(f"Detected hood from product_key keywords: {product_key}")
        return ("hermes_style_hood", "HERMES & STYLE Hood")

    if any(kw in product_lower for kw in ["solo", "ecco", "flat"]):
        if "solo" in product_lower:
            return ("solo_hcm_hood", "SOLO HCM Hood")
        elif "ecco" in product_lower:
            return ("ecco_hcm_hood", "ECCO HCM Hood")
        elif "flat" in product_lower:
            return ("flat_hood", "FLAT Hood")

    # Try device_id fallback
    if device_id:
        device_type, _, friendly_name = detect_device_type_from_device_id(device_id)
        if device_type != "auto":
            return (device_type, friendly_name)

    _LOGGER.debug(f"No match for product_key: {product_key}, using auto")
    return ("auto", "KKT Kolbe Device")


def enrich_device_info(
    device_info: dict[str, Any],
    device_id: str | None = None,
    api_device: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Enrich device_info with detected device type.

    Helper to ensure device_info always has device_type, product_name,
    and friendly_type fields populated.

    Args:
        device_info: The device info dict to enrich.
        device_id: Optional device ID for pattern-based detection.
        api_device: Optional API response for API-based detection.

    Returns:
        The enriched device_info dict.
    """
    current_type = device_info.get("device_type", "auto")

    # Only enrich if device_type is missing or "auto"
    if current_type not in ("auto", None, ""):
        return device_info

    # Try API-based detection first
    if api_device:
        detected_type, detected_product = detect_device_type_from_api(api_device)
        if detected_type != "auto":
            device_info["device_type"] = detected_type
            device_info["product_name"] = detected_product
            _LOGGER.debug(f"Enriched device_type from API: {detected_type}")
            return device_info

    # Fall back to device_id pattern detection
    device_id = device_id or device_info.get("device_id")
    if device_id:
        detected_type, detected_product, detected_friendly = detect_device_type_from_device_id(device_id)
        if detected_type != "auto":
            device_info["device_type"] = detected_type
            device_info["product_name"] = detected_product
            device_info["friendly_type"] = detected_friendly
            _LOGGER.debug(f"Enriched device_type from device_id: {detected_type}")

    return device_info
