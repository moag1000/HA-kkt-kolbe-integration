"""Icon downloader helper for KKT Kolbe integration.

Downloads device icons from Tuya Cloud and saves them locally
for use as device pictures in Home Assistant.
"""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

import aiohttp

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Tuya image base URLs (varies by region)
TUYA_IMAGE_BASE_URLS = [
    "https://images.tuyaus.com/",  # US
    "https://images.tuyaeu.com/",  # EU
    "https://images.tuyacn.com/",  # CN
]

# Default base URL (US works for most regions)
DEFAULT_IMAGE_BASE_URL = "https://images.tuyaus.com/"

# Local storage path relative to HA config
ICON_STORAGE_PATH = "www/kkt_kolbe/icons"


def get_icon_storage_path(hass: HomeAssistant) -> Path:
    """Get the full path to the icon storage directory."""
    return Path(hass.config.path(ICON_STORAGE_PATH))


def get_icon_url_for_device(device_id: str) -> str:
    """Get the local URL for a device's icon.

    Returns the URL that can be used in Home Assistant UI.
    Format: /local/kkt_kolbe/icons/{device_id}.png
    """
    return f"/local/kkt_kolbe/icons/{device_id}.png"


def build_full_icon_url(icon_path: str, base_url: str | None = None) -> str:
    """Build the full URL for a Tuya icon.

    Args:
        icon_path: The icon path from Tuya API (e.g., "smart/icon/xxx/yyy.png")
        base_url: Optional base URL override

    Returns:
        Full URL to the icon image
    """
    if not icon_path:
        return ""

    # If already a full URL, return as-is
    if icon_path.startswith("http://") or icon_path.startswith("https://"):
        return icon_path

    # Remove leading slash if present
    icon_path = icon_path.lstrip("/")

    base = base_url or DEFAULT_IMAGE_BASE_URL
    return f"{base}{icon_path}"


async def download_icon(
    hass: HomeAssistant,
    device_id: str,
    icon_path: str,
    force: bool = False,
) -> str | None:
    """Download a device icon from Tuya Cloud.

    Args:
        hass: Home Assistant instance
        device_id: The device ID (used as filename)
        icon_path: The icon path from Tuya API
        force: Force re-download even if file exists

    Returns:
        Local URL path if successful, None otherwise
    """
    if not icon_path:
        _LOGGER.debug("No icon path provided for device %s", device_id[:8])
        return None

    # Create storage directory
    storage_path = get_icon_storage_path(hass)
    try:
        storage_path.mkdir(parents=True, exist_ok=True)
    except OSError as err:
        _LOGGER.error("Failed to create icon storage directory: %s", err)
        return None

    # Target file path
    target_file = storage_path / f"{device_id}.png"

    # Check if already exists
    if target_file.exists() and not force:
        _LOGGER.debug("Icon for device %s already exists", device_id[:8])
        return get_icon_url_for_device(device_id)

    _LOGGER.info(
        "Attempting to download icon for device %s with path: %s",
        device_id[:8], icon_path[:50] if icon_path else "None"
    )

    # Try different base URLs
    for base_url in TUYA_IMAGE_BASE_URLS:
        full_url = build_full_icon_url(icon_path, base_url)
        _LOGGER.debug("Trying icon URL: %s", full_url)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(full_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    _LOGGER.debug("Icon download response: HTTP %s from %s", response.status, full_url)
                    if response.status == 200:
                        content = await response.read()

                        # Verify it's actually an image
                        # Note: Tuya CDN often returns application/octet-stream for images
                        content_type = response.headers.get("content-type", "")

                        # Check magic bytes for PNG/JPEG if content-type is generic
                        is_valid_image = content_type.startswith("image/")
                        if not is_valid_image and content_type in ("application/octet-stream", "binary/octet-stream", ""):
                            # Check PNG magic bytes: 89 50 4E 47
                            # Check JPEG magic bytes: FF D8 FF
                            if content[:4] == b'\x89PNG' or content[:3] == b'\xff\xd8\xff':
                                is_valid_image = True
                                _LOGGER.debug(
                                    "Detected image from magic bytes despite content-type: %s",
                                    content_type
                                )

                        if not is_valid_image:
                            _LOGGER.debug(
                                "URL %s returned non-image content type: %s",
                                full_url, content_type
                            )
                            continue

                        # Save to file
                        await hass.async_add_executor_job(
                            _write_file, target_file, content
                        )

                        _LOGGER.info(
                            "Downloaded icon for device %s from %s",
                            device_id[:8], base_url
                        )
                        return get_icon_url_for_device(device_id)
                    else:
                        _LOGGER.info(
                            "Icon download failed from %s: HTTP %s",
                            base_url, response.status
                        )
        except asyncio.TimeoutError:
            _LOGGER.debug("Timeout downloading from %s", full_url)
        except aiohttp.ClientError as err:
            _LOGGER.debug("Error downloading from %s: %s", full_url, err)

    _LOGGER.warning(
        "Could not download icon for device %s from any Tuya server",
        device_id[:8]
    )
    return None


def _write_file(path: Path, content: bytes) -> None:
    """Write content to file (blocking, run in executor)."""
    with open(path, "wb") as f:
        f.write(content)


async def download_all_icons(
    hass: HomeAssistant,
    devices: list[dict],
    force: bool = False,
) -> dict[str, str | None]:
    """Download icons for multiple devices.

    Args:
        hass: Home Assistant instance
        devices: List of device dicts with 'device_id' and 'icon' keys
        force: Force re-download even if files exist

    Returns:
        Dict mapping device_id to local URL (or None if failed)
    """
    results: dict[str, str | None] = {}

    for device in devices:
        device_id = device.get("device_id") or device.get("id")
        icon_path = device.get("icon") or device.get("icon_url")

        if not device_id:
            continue

        if icon_path:
            result = await download_icon(hass, device_id, icon_path, force)
            results[device_id] = result
        else:
            _LOGGER.debug("Device %s has no icon", device_id[:8])
            results[device_id] = None

    return results


def get_downloaded_icon_path(hass: HomeAssistant, device_id: str) -> Path | None:
    """Check if an icon exists for a device.

    Returns the file path if exists, None otherwise.
    """
    storage_path = get_icon_storage_path(hass)
    icon_file = storage_path / f"{device_id}.png"

    if icon_file.exists():
        return icon_file
    return None


def list_downloaded_icons(hass: HomeAssistant) -> list[dict]:
    """List all downloaded icons.

    Returns list of dicts with device_id, file_path, and local_url.
    """
    storage_path = get_icon_storage_path(hass)

    if not storage_path.exists():
        return []

    icons = []
    for icon_file in storage_path.glob("*.png"):
        device_id = icon_file.stem  # Filename without extension
        icons.append({
            "device_id": device_id,
            "file_path": str(icon_file),
            "local_url": get_icon_url_for_device(device_id),
        })

    return icons
