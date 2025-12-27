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

# Polling intervals
POLL_INTERVAL_ONLINE = 30  # Normal polling when device is online (seconds)
POLL_INTERVAL_OFFLINE = 60  # Slower polling when device is offline (seconds)
POLL_INTERVAL_RECONNECTING = 15  # Faster polling when trying to reconnect (seconds)


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

        # State tracking - start in RECONNECTING to allow initial connection attempts
        self._device_state = DeviceState.RECONNECTING
        self._last_successful_update: datetime | None = None
        self._consecutive_failures = 0
        self._is_first_update = True  # Track first update for lenient handling

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
        """Check if device is available.

        Returns True for ONLINE state, and also for RECONNECTING during initial startup
        to prevent entities from immediately showing as unavailable.
        """
        # Device is available if online
        if self._device_state == DeviceState.ONLINE:
            return True

        # During initial startup phase, also treat RECONNECTING as available
        # This prevents "unavailable" flash during first connection attempt
        if self._is_first_update and self._device_state == DeviceState.RECONNECTING:
            return True

        return False

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

    def _adjust_poll_interval(self) -> None:
        """Adjust polling interval based on device state."""
        if self._device_state == DeviceState.ONLINE:
            new_interval = timedelta(seconds=POLL_INTERVAL_ONLINE)
        elif self._device_state == DeviceState.RECONNECTING:
            new_interval = timedelta(seconds=POLL_INTERVAL_RECONNECTING)
        else:  # OFFLINE or UNREACHABLE
            new_interval = timedelta(seconds=POLL_INTERVAL_OFFLINE)

        if self.update_interval != new_interval:
            _LOGGER.debug(
                f"Device {self.device.device_id[:8]}: Adjusting poll interval to {new_interval.total_seconds()}s (state: {self._device_state.value})"
            )
            self.update_interval = new_interval

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
            was_offline = self._device_state != DeviceState.ONLINE
            if was_offline:
                _LOGGER.info(f"Device {self.device.device_id[:8]} is now ONLINE (recovered from {self._device_state.value})")
            self._device_state = DeviceState.ONLINE
            self._consecutive_failures = 0
            self._last_successful_update = datetime.now()
            self._is_first_update = False  # First successful update completed

            # Adjust poll interval for online state
            self._adjust_poll_interval()

            _LOGGER.debug(f"Device {self.device.device_id[:8]} status updated: {status}")
            return status

        except KKTTimeoutError as err:
            self._consecutive_failures += 1
            _LOGGER.warning(f"Timeout communicating with device {self.device.device_id[:8]}: {err} (failure #{self._consecutive_failures})")

            # Mark as reconnecting after first failure, offline after threshold
            if self._consecutive_failures >= DEFAULT_CONSECUTIVE_FAILURES_THRESHOLD:
                if self._device_state != DeviceState.OFFLINE:
                    _LOGGER.warning(f"Device {self.device.device_id[:8]} is now OFFLINE after {self._consecutive_failures} failures")
                self._device_state = DeviceState.OFFLINE
            elif self._device_state == DeviceState.ONLINE:
                _LOGGER.info(f"Device {self.device.device_id[:8]} is RECONNECTING...")
                self._device_state = DeviceState.RECONNECTING

            # Adjust poll interval based on new state
            self._adjust_poll_interval()

            # Don't raise UpdateFailed for timeouts - keep last known state
            return self.data or {}

        except KKTConnectionError as err:
            self._consecutive_failures += 1
            _LOGGER.warning(f"Connection error with device {self.device.device_id[:8]}: {err} (failure #{self._consecutive_failures})")

            # Mark as reconnecting after first failure, offline after threshold
            if self._consecutive_failures >= DEFAULT_CONSECUTIVE_FAILURES_THRESHOLD:
                if self._device_state != DeviceState.OFFLINE:
                    _LOGGER.warning(f"Device {self.device.device_id[:8]} is now OFFLINE after {self._consecutive_failures} failures")
                self._device_state = DeviceState.OFFLINE
            elif self._device_state == DeviceState.ONLINE:
                _LOGGER.info(f"Device {self.device.device_id[:8]} is RECONNECTING...")
                self._device_state = DeviceState.RECONNECTING

            # Adjust poll interval based on new state
            self._adjust_poll_interval()

            # Don't raise UpdateFailed for connection errors - keep last known state
            return self.data or {}

        except Exception as err:
            self._consecutive_failures += 1
            _LOGGER.error(f"Unexpected error communicating with device {self.device.device_id[:8]}: {err} (failure #{self._consecutive_failures})")

            # Mark as reconnecting after first failure, offline after threshold
            if self._consecutive_failures >= DEFAULT_CONSECUTIVE_FAILURES_THRESHOLD:
                if self._device_state != DeviceState.OFFLINE:
                    _LOGGER.warning(f"Device {self.device.device_id[:8]} is now OFFLINE after {self._consecutive_failures} failures")
                self._device_state = DeviceState.OFFLINE
            elif self._device_state == DeviceState.ONLINE:
                _LOGGER.info(f"Device {self.device.device_id[:8]} is RECONNECTING...")
                self._device_state = DeviceState.RECONNECTING

            # Adjust poll interval based on new state
            self._adjust_poll_interval()

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