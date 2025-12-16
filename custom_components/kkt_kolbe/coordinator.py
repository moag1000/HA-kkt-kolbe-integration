"""DataUpdateCoordinator for KKT Kolbe integration."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, DEFAULT_CONSECUTIVE_FAILURES_THRESHOLD
from .tuya_device import KKTKolbeTuyaDevice

_LOGGER = logging.getLogger(__name__)


class DeviceState(Enum):
    """Device connection states."""
    ONLINE = "online"
    OFFLINE = "offline"
    RECONNECTING = "reconnecting"
    UNREACHABLE = "unreachable"

class KKTKolbeUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching KKT Kolbe data from the device."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        device: KKTKolbeTuyaDevice,
    ) -> None:
        """Initialize the coordinator."""
        self.device = device
        self.entry = entry

        # State tracking
        self._device_state = DeviceState.OFFLINE
        self._last_successful_update: datetime | None = None
        self._consecutive_failures = 0

        # Update every 30 seconds for real-time control
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=30),
        )

    @property
    def device_state(self) -> DeviceState:
        """Get current device state."""
        return self._device_state

    @property
    def is_device_available(self) -> bool:
        """Check if device is available."""
        return self._device_state == DeviceState.ONLINE

    @property
    def last_successful_update(self) -> datetime | None:
        """Get timestamp of last successful update."""
        return self._last_successful_update

    @property
    def connection_info(self) -> dict[str, Any]:
        """Get connection status information."""
        return {
            "state": self._device_state.value,
            "last_update": self._last_successful_update,
            "consecutive_failures": self._consecutive_failures,
            "is_connected": self.device.is_connected,
        }

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the device."""
        from .exceptions import KKTTimeoutError, KKTConnectionError

        try:
            # Ensure device is connected
            if not self.device.is_connected:
                _LOGGER.debug(f"Device {self.device.device_id[:8]} not connected, attempting to connect")
                self._device_state = DeviceState.RECONNECTING
                await self.device.async_connect()

            # Get current device status
            status = await self.device.async_get_status()

            if not status:
                _LOGGER.warning(f"Device {self.device.device_id[:8]} returned empty status")
                self._consecutive_failures += 1
                raise UpdateFailed("Failed to get device status")

            # Success - update state
            if self._device_state != DeviceState.ONLINE:
                _LOGGER.info(f"Device {self.device.device_id[:8]} is now ONLINE")
            self._device_state = DeviceState.ONLINE
            self._consecutive_failures = 0
            self._last_successful_update = datetime.now()

            _LOGGER.debug(f"Device {self.device.device_id[:8]} status updated: {status}")
            return status

        except KKTTimeoutError as err:
            self._consecutive_failures += 1
            _LOGGER.warning(f"Timeout communicating with device {self.device.device_id[:8]}: {err}")

            # Mark offline after consecutive failures
            if self._consecutive_failures >= DEFAULT_CONSECUTIVE_FAILURES_THRESHOLD:
                if self._device_state == DeviceState.ONLINE:
                    _LOGGER.warning(f"Device {self.device.device_id[:8]} is now OFFLINE")
                self._device_state = DeviceState.OFFLINE

            # Don't raise UpdateFailed for timeouts - keep last known state
            return self.data or {}

        except KKTConnectionError as err:
            self._consecutive_failures += 1
            _LOGGER.warning(f"Connection error with device {self.device.device_id[:8]}: {err}")

            # Mark offline after consecutive failures
            if self._consecutive_failures >= DEFAULT_CONSECUTIVE_FAILURES_THRESHOLD:
                if self._device_state == DeviceState.ONLINE:
                    _LOGGER.warning(f"Device {self.device.device_id[:8]} is now OFFLINE")
                self._device_state = DeviceState.OFFLINE

            # Don't raise UpdateFailed for connection errors - keep last known state
            return self.data or {}

        except Exception as err:
            self._consecutive_failures += 1
            _LOGGER.error(f"Unexpected error communicating with device {self.device.device_id[:8]}: {err}")

            # Mark offline after consecutive failures
            if self._consecutive_failures >= DEFAULT_CONSECUTIVE_FAILURES_THRESHOLD:
                if self._device_state == DeviceState.ONLINE:
                    _LOGGER.warning(f"Device {self.device.device_id[:8]} is now OFFLINE")
                self._device_state = DeviceState.OFFLINE

            raise UpdateFailed(f"Error communicating with device: {err}") from err

    async def async_set_data_point(self, dp: int, value: Any) -> None:
        """Set a data point on the device and refresh data."""
        try:
            await self.device.async_set_dp(dp, value)
            # Immediately refresh data after command
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.error(f"Failed to set DP {dp} to {value}: {err}")
            raise UpdateFailed(f"Failed to set DP {dp}: {err}") from err

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information for device registry."""
        from .device_types import get_device_info_by_product_name

        product_name = self.entry.data.get("product_name", "unknown")
        device_info = get_device_info_by_product_name(product_name)

        return {
            "identifiers": {(DOMAIN, self.device.device_id)},
            "name": self.entry.data.get("name", device_info["name"]),
            "manufacturer": "KKT Kolbe",
            "model": device_info["name"],
            "model_id": device_info["model_id"],
            "sw_version": getattr(self.device, 'version', None),
            "hw_version": self.device.device_id[:8],  # Use first 8 chars of device ID
            "configuration_url": f"http://{self.device.ip_address}",
        }