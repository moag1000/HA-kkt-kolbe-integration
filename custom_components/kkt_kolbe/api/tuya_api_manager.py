"""TinyTuya API Manager following Home Assistant authentication patterns."""
import asyncio
import logging
from typing import Dict, List, Optional, Callable, Awaitable

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.exceptions import ConfigEntryAuthFailed

from .tuya_cloud_client import TuyaCloudClient
from .api_exceptions import TuyaAPIError, TuyaAuthenticationError
from ..const import (
    CONF_API_CLIENT_ID,
    CONF_API_CLIENT_SECRET,
    CONF_API_ENDPOINT,
    DEFAULT_API_ENDPOINT,
)

_LOGGER = logging.getLogger(__name__)


class TuyaAPIManager:
    """Manages TinyTuya Cloud API authentication following HA patterns."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        reauth_callback: Optional[Callable[[], Awaitable[None]]] = None,
    ):
        """Initialize the API manager."""
        self.hass = hass
        self.config_entry = config_entry
        self._reauth_callback = reauth_callback
        self._client: Optional[TuyaCloudClient] = None
        self._lock = asyncio.Lock()

    @property
    def client_id(self) -> str:
        """Get API client ID from config."""
        return self.config_entry.data[CONF_API_CLIENT_ID]

    @property
    def client_secret(self) -> str:
        """Get API client secret from config."""
        return self.config_entry.data[CONF_API_CLIENT_SECRET]

    @property
    def endpoint(self) -> str:
        """Get API endpoint from config."""
        return self.config_entry.data.get(CONF_API_ENDPOINT, DEFAULT_API_ENDPOINT)

    async def async_get_client(self) -> TuyaCloudClient:
        """Get authenticated API client."""
        async with self._lock:
            if self._client is None:
                session = async_get_clientsession(self.hass)
                self._client = TuyaCloudClient(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    endpoint=self.endpoint,
                    session=session,
                )

            try:
                # Ensure client is authenticated
                await self._client._ensure_authenticated()
                return self._client

            except TuyaAuthenticationError as err:
                _LOGGER.error("API authentication failed: %s", err)
                # Trigger reauthentication flow
                if self._reauth_callback:
                    await self._reauth_callback()
                raise ConfigEntryAuthFailed("API authentication failed") from err

    async def async_get_device_list(self) -> List[Dict]:
        """Get device list with error handling."""
        try:
            client = await self.async_get_client()
            return await client.get_device_list()
        except TuyaAPIError as err:
            _LOGGER.error("Failed to get device list: %s", err)
            raise

    async def async_get_device_properties(self, device_id: str) -> Dict:
        """Get device properties with error handling."""
        try:
            client = await self.async_get_client()
            return await client.get_device_properties(device_id)
        except TuyaAPIError as err:
            _LOGGER.error("Failed to get device properties for %s: %s", device_id, err)
            raise

    async def async_get_device_status(self, device_id: str) -> Dict:
        """Get device status with error handling."""
        try:
            client = await self.async_get_client()
            return await client.get_device_status(device_id)
        except TuyaAPIError as err:
            _LOGGER.error("Failed to get device status for %s: %s", device_id, err)
            raise

    async def async_get_device_shadow_properties(self, device_id: str, codes: Optional[List[str]] = None) -> Dict:
        """Get device shadow properties (live data) with error handling."""
        try:
            client = await self.async_get_client()
            return await client.get_device_shadow_properties(device_id, codes)
        except TuyaAPIError as err:
            _LOGGER.error("Failed to get shadow properties for %s: %s", device_id, err)
            raise

    async def async_set_device_shadow_properties(self, device_id: str, properties: Dict[str, any]) -> Dict:
        """Set device shadow properties (send commands) with error handling."""
        try:
            client = await self.async_get_client()
            return await client.set_device_shadow_properties(device_id, properties)
        except TuyaAPIError as err:
            _LOGGER.error("Failed to set shadow properties for %s: %s", device_id, err)
            raise

    async def async_get_device_real_time_data(self, device_id: str, codes: List[str]) -> Dict:
        """Get real-time device data for specific codes with error handling."""
        try:
            client = await self.async_get_client()
            return await client.get_device_real_time_data(device_id, codes)
        except TuyaAPIError as err:
            _LOGGER.error("Failed to get real-time data for %s: %s", device_id, err)
            raise

    async def async_test_connection(self) -> bool:
        """Test API connection."""
        try:
            client = await self.async_get_client()
            return await client.test_connection()
        except Exception as err:
            _LOGGER.error("API connection test failed: %s", err)
            return False

    async def async_close(self) -> None:
        """Close the API manager and clean up resources."""
        if self._client:
            await self._client.__aexit__(None, None, None)
            self._client = None