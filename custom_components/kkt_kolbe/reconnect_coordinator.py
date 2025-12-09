"""Enhanced coordinator with automatic reconnection and availability tracking."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.const import STATE_UNAVAILABLE

from .const import DOMAIN
from .tuya_device import KKTKolbeTuyaDevice
from .exceptions import KKTTimeoutError, KKTConnectionError

_LOGGER = logging.getLogger(__name__)


class DeviceState(Enum):
    """Device connection states."""
    ONLINE = "online"
    OFFLINE = "offline"
    RECONNECTING = "reconnecting"
    UNREACHABLE = "unreachable"


class ReconnectCoordinator(DataUpdateCoordinator):
    """Coordinator with automatic reconnection and device availability tracking."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        device: KKTKolbeTuyaDevice,
        update_interval: int = 30,
    ) -> None:
        """Initialize the reconnect coordinator."""
        self.device = device
        self.entry = entry

        # Connection state tracking
        self._device_state = DeviceState.OFFLINE
        self._last_successful_update: datetime | None = None
        self._consecutive_failures = 0
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 10

        # Backoff configuration
        self._base_backoff_time = 5  # seconds
        self._max_backoff_time = 300  # 5 minutes
        self._current_backoff_time = self._base_backoff_time

        # Reconnection task
        self._reconnect_task: asyncio.Task | None = None
        self._reconnect_lock = asyncio.Lock()

        # Health check interval (separate from data updates)
        self._health_check_interval = timedelta(minutes=5)
        self._health_check_unsub = None

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}_reconnect",
            update_interval=timedelta(seconds=update_interval),
        )

    async def async_added_to_hass(self) -> None:
        """When coordinator is added to hass."""
        await super().async_added_to_hass()

        # Start health check
        self._health_check_unsub = async_track_time_interval(
            self.hass,
            self._async_health_check,
            self._health_check_interval
        )

    async def async_will_remove_from_hass(self) -> None:
        """When coordinator is removed from hass."""
        await super().async_will_remove_from_hass()

        # Cancel health check
        if self._health_check_unsub:
            self._health_check_unsub()

        # Cancel any ongoing reconnection
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()

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
            "reconnect_attempts": self._reconnect_attempts,
            "is_connected": self.device.is_connected,
        }

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from device with reconnection logic."""
        try:
            # Check if we need to reconnect
            if not self.device.is_connected:
                if self._device_state != DeviceState.RECONNECTING:
                    await self._async_mark_offline()
                    await self._async_start_reconnection()

                # Return cached data while reconnecting
                return self.data or {}

            # Try to get device status
            status = await self._async_fetch_with_timeout()

            if status:
                # Success - update tracking
                await self._async_mark_online()
                self._consecutive_failures = 0
                self._last_successful_update = datetime.now()
                self._current_backoff_time = self._base_backoff_time

                _LOGGER.debug(
                    f"Device {self.device.device_id[:8]} successfully updated. "
                    f"State: {self._device_state.value}"
                )
                return status
            else:
                # Empty status - device might be in weird state
                raise UpdateFailed("Device returned empty status")

        except (KKTTimeoutError, KKTConnectionError) as err:
            self._consecutive_failures += 1
            _LOGGER.warning(
                f"Device {self.device.device_id[:8]} communication failed "
                f"(attempt {self._consecutive_failures}): {err}"
            )

            # Mark offline after 3 consecutive failures
            if self._consecutive_failures >= 3:
                await self._async_mark_offline()
                await self._async_start_reconnection()

            # Return cached data
            return self.data or {}

        except Exception as err:
            self._consecutive_failures += 1
            _LOGGER.error(
                f"Unexpected error with device {self.device.device_id[:8]}: {err}"
            )

            # For unexpected errors, still try to reconnect
            if self._consecutive_failures >= 3:
                await self._async_mark_offline()
                await self._async_start_reconnection()

            raise UpdateFailed(f"Device communication error: {err}") from err

    async def _async_fetch_with_timeout(self, timeout: int = 10) -> dict[str, Any]:
        """Fetch device status with timeout."""
        try:
            async with asyncio.timeout(timeout):
                return await self.device.async_get_status()
        except asyncio.TimeoutError:
            raise KKTTimeoutError(f"Device fetch timed out after {timeout}s")

    async def _async_mark_online(self) -> None:
        """Mark device as online."""
        if self._device_state != DeviceState.ONLINE:
            self._device_state = DeviceState.ONLINE
            self._reconnect_attempts = 0
            _LOGGER.info(f"Device {self.device.device_id[:8]} is now ONLINE")

            # Fire event for device online
            self.hass.bus.async_fire(
                f"{DOMAIN}_device_online",
                {"device_id": self.device.device_id, "ip": self.device.ip_address}
            )

    async def _async_mark_offline(self) -> None:
        """Mark device as offline."""
        if self._device_state == DeviceState.ONLINE:
            self._device_state = DeviceState.OFFLINE
            _LOGGER.warning(f"Device {self.device.device_id[:8]} is now OFFLINE")

            # Fire event for device offline
            self.hass.bus.async_fire(
                f"{DOMAIN}_device_offline",
                {"device_id": self.device.device_id, "ip": self.device.ip_address}
            )

    async def _async_start_reconnection(self) -> None:
        """Start reconnection process if not already running."""
        async with self._reconnect_lock:
            # Check if reconnection is already in progress
            if self._reconnect_task and not self._reconnect_task.done():
                return

            # Check if we've exceeded max attempts
            if self._reconnect_attempts >= self._max_reconnect_attempts:
                if self._device_state != DeviceState.UNREACHABLE:
                    self._device_state = DeviceState.UNREACHABLE
                    _LOGGER.error(
                        f"Device {self.device.device_id[:8]} marked as UNREACHABLE "
                        f"after {self._max_reconnect_attempts} attempts"
                    )
                return

            # Start reconnection task
            self._device_state = DeviceState.RECONNECTING
            self._reconnect_task = self.hass.async_create_task(
                self._async_reconnect_with_backoff()
            )

    async def _async_reconnect_with_backoff(self) -> None:
        """Reconnect with exponential backoff."""
        while self._reconnect_attempts < self._max_reconnect_attempts:
            self._reconnect_attempts += 1

            _LOGGER.info(
                f"Reconnection attempt {self._reconnect_attempts}/{self._max_reconnect_attempts} "
                f"for device {self.device.device_id[:8]} "
                f"(waiting {self._current_backoff_time}s)"
            )

            # Wait with backoff
            await asyncio.sleep(self._current_backoff_time)

            try:
                # Try to reconnect
                await self.device.async_connect()

                # Test connection
                status = await self._async_fetch_with_timeout(timeout=5)

                if status:
                    # Success!
                    await self._async_mark_online()
                    self._consecutive_failures = 0
                    self._last_successful_update = datetime.now()

                    # Update data
                    self.async_set_updated_data(status)

                    _LOGGER.info(
                        f"Successfully reconnected to device {self.device.device_id[:8]} "
                        f"after {self._reconnect_attempts} attempts"
                    )
                    return

            except Exception as err:
                _LOGGER.debug(
                    f"Reconnection attempt {self._reconnect_attempts} failed: {err}"
                )

            # Increase backoff time (exponential backoff with jitter)
            import random
            self._current_backoff_time = min(
                self._current_backoff_time * 2 + random.uniform(0, 1),
                self._max_backoff_time
            )

        # Max attempts reached
        self._device_state = DeviceState.UNREACHABLE
        _LOGGER.error(
            f"Failed to reconnect to device {self.device.device_id[:8]} "
            f"after {self._max_reconnect_attempts} attempts"
        )

    @callback
    async def _async_health_check(self, _now) -> None:
        """Periodic health check for device availability."""
        if self._device_state == DeviceState.UNREACHABLE:
            # Reset and try again for unreachable devices
            _LOGGER.info(
                f"Health check: Retrying unreachable device {self.device.device_id[:8]}"
            )
            self._reconnect_attempts = 0
            self._current_backoff_time = self._base_backoff_time
            await self._async_start_reconnection()

        elif self._device_state == DeviceState.OFFLINE:
            # Try to reconnect offline devices
            _LOGGER.debug(
                f"Health check: Checking offline device {self.device.device_id[:8]}"
            )
            await self._async_start_reconnection()

    async def async_request_reconnect(self) -> bool:
        """Manually request device reconnection."""
        _LOGGER.info(f"Manual reconnection requested for device {self.device.device_id[:8]}")

        # Reset counters
        self._reconnect_attempts = 0
        self._current_backoff_time = self._base_backoff_time
        self._consecutive_failures = 0

        # Close existing connection
        if self.device.is_connected:
            await self.device.async_disconnect()

        # Start reconnection
        await self._async_start_reconnection()

        # Wait a bit for reconnection to complete
        await asyncio.sleep(5)

        return self._device_state == DeviceState.ONLINE

    async def async_set_data_point(self, dp: int, value: Any) -> None:
        """Set a data point on the device with reconnection on failure."""
        if not self.is_device_available:
            _LOGGER.warning(
                f"Cannot set DP {dp} - device {self.device.device_id[:8]} is {self._device_state.value}"
            )
            raise UpdateFailed(f"Device is {self._device_state.value}")

        try:
            await self.device.async_set_dp(dp, value)
            # Immediately refresh data after command
            await self.async_request_refresh()

        except (KKTTimeoutError, KKTConnectionError) as err:
            _LOGGER.error(f"Failed to set DP {dp}: {err}")

            # Mark offline and start reconnection
            await self._async_mark_offline()
            await self._async_start_reconnection()

            raise UpdateFailed(f"Device communication failed: {err}") from err

        except Exception as err:
            _LOGGER.error(f"Unexpected error setting DP {dp}: {err}")
            raise UpdateFailed(f"Failed to set DP {dp}: {err}") from err