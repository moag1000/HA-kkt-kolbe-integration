"""Global API management for KKT Kolbe integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import GLOBAL_API_STORAGE_KEY, DEFAULT_API_ENDPOINT, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Persistent storage version
STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.api_credentials"


class GlobalAPIManager:
    """Manages global API credentials for all KKT Kolbe devices."""

    def __init__(self, hass: HomeAssistant):
        """Initialize the global API manager."""
        self.hass = hass
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)

    async def async_load_stored_credentials(self) -> dict[str, str] | None:
        """Load credentials from persistent storage."""
        try:
            data = await self._store.async_load()
            if data:
                _LOGGER.debug("Loaded API credentials from persistent storage")
                # Also update runtime cache
                self.hass.data[GLOBAL_API_STORAGE_KEY] = data
                return data
        except Exception as err:
            _LOGGER.error(f"Failed to load API credentials: {err}")
        return None

    def get_stored_api_credentials(self) -> dict[str, str] | None:
        """Get stored global API credentials (from runtime cache)."""
        global_api_data = self.hass.data.get(GLOBAL_API_STORAGE_KEY)
        if global_api_data:
            return {
                "client_id": global_api_data.get("client_id"),
                "client_secret": global_api_data.get("client_secret"),
                "endpoint": global_api_data.get("endpoint", DEFAULT_API_ENDPOINT)
            }
        return None

    async def async_store_api_credentials(self, client_id: str, client_secret: str, endpoint: str | None = None) -> None:
        """Store global API credentials persistently."""
        if endpoint is None:
            endpoint = DEFAULT_API_ENDPOINT

        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "endpoint": endpoint
        }

        # Store in runtime cache
        self.hass.data[GLOBAL_API_STORAGE_KEY] = data

        # Persist to storage
        try:
            await self._store.async_save(data)
            _LOGGER.info("Global API credentials stored persistently for KKT Kolbe integration")
        except Exception as err:
            _LOGGER.error(f"Failed to persist API credentials: {err}")

    def store_api_credentials(self, client_id: str, client_secret: str, endpoint: str | None = None) -> None:
        """Store global API credentials (runtime only - use async version for persistence)."""
        if endpoint is None:
            endpoint = DEFAULT_API_ENDPOINT

        if GLOBAL_API_STORAGE_KEY not in self.hass.data:
            self.hass.data[GLOBAL_API_STORAGE_KEY] = {}

        self.hass.data[GLOBAL_API_STORAGE_KEY] = {
            "client_id": client_id,
            "client_secret": client_secret,
            "endpoint": endpoint
        }

        _LOGGER.info("Global API credentials stored in runtime cache")

    def has_stored_credentials(self) -> bool:
        """Check if we have stored API credentials (runtime cache only)."""
        creds = self.get_stored_api_credentials()
        return (
            creds is not None
            and creds.get("client_id")
            and creds.get("client_secret")
        )

    async def async_has_stored_credentials(self) -> bool:
        """Check if we have stored API credentials (including persistent storage)."""
        # First check runtime cache
        if self.has_stored_credentials():
            return True

        # Try loading from persistent storage
        creds = await self.async_load_stored_credentials()
        return (
            creds is not None
            and creds.get("client_id")
            and creds.get("client_secret")
        )

    def clear_stored_credentials(self) -> None:
        """Clear stored global API credentials (runtime only)."""
        if GLOBAL_API_STORAGE_KEY in self.hass.data:
            del self.hass.data[GLOBAL_API_STORAGE_KEY]
            _LOGGER.info("Global API credentials cleared from runtime cache")

    async def async_clear_stored_credentials(self) -> None:
        """Clear stored global API credentials (including persistent storage)."""
        if GLOBAL_API_STORAGE_KEY in self.hass.data:
            del self.hass.data[GLOBAL_API_STORAGE_KEY]
        try:
            await self._store.async_remove()
            _LOGGER.info("Global API credentials cleared from persistent storage")
        except Exception as err:
            _LOGGER.error(f"Failed to clear persistent API credentials: {err}")

    async def test_stored_credentials(self) -> bool:
        """Test stored API credentials."""
        creds = self.get_stored_api_credentials()
        if not creds:
            return False

        try:
            from .api import TuyaCloudClient

            api_client = TuyaCloudClient(
                client_id=creds["client_id"],
                client_secret=creds["client_secret"],
                endpoint=creds["endpoint"]
            )

            async with api_client:
                return await api_client.test_connection()

        except Exception as err:
            _LOGGER.error(f"Stored API credentials test failed: {err}")
            return False

    async def get_kkt_devices_from_api(self) -> list:
        """Get KKT Kolbe devices using stored credentials."""
        creds = self.get_stored_api_credentials()
        if not creds:
            return []

        try:
            from .api import TuyaCloudClient

            api_client = TuyaCloudClient(
                client_id=creds["client_id"],
                client_secret=creds["client_secret"],
                endpoint=creds["endpoint"]
            )

            async with api_client:
                if await api_client.test_connection():
                    # Use get_device_list_with_details to get full device info
                    # including product_id and local_key for proper detection
                    devices = await api_client.get_device_list_with_details()

                    # Filter for KKT Kolbe devices
                    kkt_devices = []
                    for device in devices:
                        product_name = device.get("product_name", "").lower()
                        device_name = device.get("name", "").lower()
                        category = device.get("category", "").lower()

                        # Match by keywords or Tuya category
                        is_kkt = any(keyword in f"{product_name} {device_name}"
                                     for keyword in ["kkt", "kolbe", "range", "hood", "induction"])
                        is_hood_category = category in ["yyj", "dcl"]  # Hood or Cooktop

                        if is_kkt or is_hood_category:
                            has_local_key = bool(device.get('local_key'))
                            _LOGGER.info(f"Found KKT device: {device.get('name')} "
                                        f"(product_id={device.get('product_id', 'N/A')}, "
                                        f"local_key={'present' if has_local_key else 'MISSING'})")
                            kkt_devices.append(device)

                    return kkt_devices

        except Exception as err:
            _LOGGER.error(f"Failed to get devices from API: {err}")

        return []

    def get_api_info_summary(self) -> str:
        """Get a summary of stored API info for display."""
        creds = self.get_stored_api_credentials()
        if not creds:
            return "No API credentials stored"

        client_id = creds.get("client_id", "")
        endpoint = creds.get("endpoint", "")

        # Show partial client ID for security
        masked_id = f"{client_id[:6]}...{client_id[-4:]}" if len(client_id) > 10 else client_id

        region_map = {
            "https://openapi.tuyaeu.com": "EU",
            "https://openapi.tuyaus.com": "US",
            "https://openapi.tuyacn.com": "CN",
            "https://openapi.tuyain.com": "IN"
        }
        region = region_map.get(endpoint, "Custom")

        return f"Client ID: {masked_id} | Region: {region}"