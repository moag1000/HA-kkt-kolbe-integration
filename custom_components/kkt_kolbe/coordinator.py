"""DataUpdateCoordinator for KKT Kolbe integration."""
from __future__ import annotations

import logging
from datetime import datetime
from datetime import timedelta
from enum import Enum
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import CIRCUIT_BREAKER_MAX_SLEEP_RETRIES
from .const import CIRCUIT_BREAKER_SLEEP_INTERVAL
from .const import DEFAULT_BASE_BACKOFF
from .const import DEFAULT_CONSECUTIVE_FAILURES_THRESHOLD
from .const import DEFAULT_MAX_BACKOFF
from .const import DEFAULT_MAX_RECONNECT_ATTEMPTS
from .const import DOMAIN
from .const import MAX_ERROR_HISTORY
from .tuya_device import KKTKolbeTuyaDevice

_LOGGER = logging.getLogger(__name__)

# Polling intervals
POLL_INTERVAL_ONLINE = 30  # Normal polling when device is online (seconds)
POLL_INTERVAL_OFFLINE = 60  # Slower polling when device is offline (seconds)
POLL_INTERVAL_RECONNECTING = 15  # Faster polling when trying to reconnect (seconds)
POLL_INTERVAL_UNREACHABLE = 300  # Very slow polling when circuit breaker tripped (seconds)


class DeviceState(Enum):
    """Device connection states."""
    ONLINE = "online"
    OFFLINE = "offline"
    RECONNECTING = "reconnecting"
    UNREACHABLE = "unreachable"  # Circuit breaker tripped - no more retries until reset

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

        # DPS cache for merging partial updates
        # Tuya devices often send delta/partial updates (only changed DPs)
        # This cache accumulates all DPs seen so far
        self._dps_cache: dict[str, Any] = {}

        # Error history for diagnostics
        self._error_history: list[dict[str, Any]] = []

        # Exponential backoff configuration
        self._base_backoff: float = float(DEFAULT_BASE_BACKOFF)
        self._max_backoff: float = float(DEFAULT_MAX_BACKOFF)
        self._current_backoff: float = self._base_backoff
        self._reconnect_attempts: int = 0
        self._max_reconnect_attempts: int = DEFAULT_MAX_RECONNECT_ATTEMPTS

        # Circuit breaker configuration
        self._circuit_breaker_retries: int = 0
        self._circuit_breaker_next_retry: datetime | None = None

        # Update every 30 seconds for real-time control
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=30),
            # Prevent unnecessary state writes when data hasn't changed
            # Critical performance optimization for high-frequency updates
            always_update=False,
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
            "reconnect_attempts": self._reconnect_attempts,
            "current_backoff": self._current_backoff,
            "circuit_breaker_retries": self._circuit_breaker_retries,
            "circuit_breaker_next_retry": self._circuit_breaker_next_retry,
        }

    def _record_error(self, error_type: str, message: str, recoverable: bool = True) -> None:
        """Record an error to the error history for diagnostics."""
        error_entry = {
            "timestamp": datetime.now(),
            "error_type": error_type,
            "message": str(message),
            "recoverable": recoverable,
            "device_state": self._device_state.value,
            "consecutive_failures": self._consecutive_failures,
        }
        self._error_history.append(error_entry)

        # Trim history to max size
        if len(self._error_history) > MAX_ERROR_HISTORY:
            self._error_history = self._error_history[-MAX_ERROR_HISTORY:]

    def _adjust_poll_interval(self) -> None:
        """Adjust polling interval based on device state."""
        if self._device_state == DeviceState.ONLINE:
            new_interval = timedelta(seconds=POLL_INTERVAL_ONLINE)
        elif self._device_state == DeviceState.RECONNECTING:
            new_interval = timedelta(seconds=POLL_INTERVAL_RECONNECTING)
        elif self._device_state == DeviceState.UNREACHABLE:
            # Circuit breaker tripped - poll very slowly
            new_interval = timedelta(seconds=POLL_INTERVAL_UNREACHABLE)
        else:  # OFFLINE
            new_interval = timedelta(seconds=POLL_INTERVAL_OFFLINE)

        current_interval = self.update_interval  # type: ignore[has-type]
        if current_interval != new_interval:
            _LOGGER.debug(
                f"Device {self.device.device_id[:8]}: Adjusting poll interval to {new_interval.total_seconds()}s (state: {self._device_state.value})"
            )
            self.update_interval = new_interval

    def _apply_exponential_backoff(self) -> None:
        """Apply exponential backoff with jitter for reconnection attempts."""
        import random
        # Exponential backoff: base * 2^attempts, with jitter
        self._current_backoff = min(
            self._max_backoff,
            self._base_backoff * (2 ** min(self._reconnect_attempts, 8))  # Cap exponent at 8
        )
        # Add jitter (±25%)
        jitter = self._current_backoff * 0.25 * (random.random() * 2 - 1)
        self._current_backoff = max(self._base_backoff, self._current_backoff + jitter)

    def _check_circuit_breaker(self) -> bool:
        """Check if circuit breaker allows retry.

        Returns True if retry is allowed, False if circuit breaker is tripped.
        """
        # If we're in UNREACHABLE state, check if we can retry
        if self._device_state == DeviceState.UNREACHABLE:
            if self._circuit_breaker_next_retry:
                if datetime.now() < self._circuit_breaker_next_retry:
                    # Still in sleep period
                    return False
            # Allow retry - reset attempt counter but not circuit breaker retry counter
            self._reconnect_attempts = 0
            self._current_backoff = self._base_backoff
            return True

        # Check if we've exceeded max reconnect attempts
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            # Trip the circuit breaker
            self._circuit_breaker_retries += 1
            self._device_state = DeviceState.UNREACHABLE

            # Schedule next retry with increasing delay
            sleep_multiplier = min(self._circuit_breaker_retries, CIRCUIT_BREAKER_MAX_SLEEP_RETRIES)
            sleep_interval = CIRCUIT_BREAKER_SLEEP_INTERVAL * sleep_multiplier
            self._circuit_breaker_next_retry = datetime.now() + timedelta(seconds=sleep_interval)

            _LOGGER.warning(
                f"Device {self.device.device_id[:8]}: Circuit breaker tripped after "
                f"{self._max_reconnect_attempts} attempts. "
                f"Retry #{self._circuit_breaker_retries} scheduled in {sleep_interval}s"
            )
            self._adjust_poll_interval()
            return False

        return True

    def _reset_on_success(self) -> None:
        """Reset all failure counters on successful update."""
        was_offline = self._device_state != DeviceState.ONLINE
        if was_offline:
            _LOGGER.info(f"Device {self.device.device_id[:8]} is now ONLINE (recovered from {self._device_state.value})")

        self._device_state = DeviceState.ONLINE
        self._consecutive_failures = 0
        self._reconnect_attempts = 0
        self._current_backoff = self._base_backoff
        self._circuit_breaker_retries = 0
        self._circuit_breaker_next_retry = None
        self._last_successful_update = datetime.now()
        self._is_first_update = False

    def _get_cached_data(self) -> dict[str, Any]:
        """Get cached data for use during errors/offline.

        Returns the merged DPS cache wrapped in proper structure,
        or falls back to self.data if cache is empty.
        """
        if self._dps_cache:
            return {
                "dps": self._dps_cache.copy(),
                "source": "cached",
                "timestamp": self._last_successful_update.isoformat() if self._last_successful_update else None,
                "available": False,  # Mark as cached/stale data
            }
        return self.data or {}

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the device.

        Important: Tuya devices often send partial/delta updates (only changed DPs).
        This method merges each partial update into a persistent cache, so all
        previously seen DPs remain available even if not included in the latest update.
        """
        from .exceptions import KKTConnectionError
        from .exceptions import KKTTimeoutError

        try:
            # Ensure device is connected
            if not self.device.is_connected:
                _LOGGER.debug(f"Device {self.device.device_id[:8]} not connected, attempting to connect")
                self._device_state = DeviceState.RECONNECTING
                await self.device.async_connect()

            # Get current device status (may be partial update)
            partial_status: dict[str, Any] = await self.device.async_get_status()

            if not partial_status:
                _LOGGER.warning(f"Device {self.device.device_id[:8]} returned empty status")
                self._consecutive_failures += 1
                raise UpdateFailed("Failed to get device status")

            # Merge partial update into our cache
            # This ensures we keep all DPs seen across multiple updates
            partial_count = len(partial_status)
            self._dps_cache.update(partial_status)

            # Log if we're merging partial updates
            if partial_count < len(self._dps_cache):
                _LOGGER.debug(
                    f"Device {self.device.device_id[:8]}: Merged {partial_count} DPs into cache "
                    f"(total cached: {len(self._dps_cache)} DPs)"
                )

            # Success - reset all failure counters and update state
            self._reset_on_success()

            # Adjust poll interval for online state
            self._adjust_poll_interval()

            # Return merged cache with proper structure
            merged_data = {
                "dps": self._dps_cache.copy(),
                "source": "merged_cache",
                "timestamp": datetime.now().isoformat(),
                "available": True,
            }
            _LOGGER.debug(f"Device {self.device.device_id[:8]} returning merged data with {len(self._dps_cache)} DPs: {list(self._dps_cache.keys())}")
            return merged_data

        except KKTTimeoutError as err:
            self._consecutive_failures += 1
            self._reconnect_attempts += 1
            self._record_error("timeout", str(err), recoverable=True)
            _LOGGER.warning(
                f"Timeout communicating with device {self.device.device_id[:8]}: {err} "
                f"(failure #{self._consecutive_failures}, reconnect attempt #{self._reconnect_attempts})"
            )

            # Check circuit breaker before state transitions
            if not self._check_circuit_breaker():
                return self._get_cached_data()

            # Apply exponential backoff
            self._apply_exponential_backoff()

            # Mark as reconnecting after first failure, offline after threshold
            if self._consecutive_failures >= DEFAULT_CONSECUTIVE_FAILURES_THRESHOLD:
                if self._device_state not in (DeviceState.OFFLINE, DeviceState.UNREACHABLE):
                    _LOGGER.warning(f"Device {self.device.device_id[:8]} is now OFFLINE after {self._consecutive_failures} failures")
                    self._device_state = DeviceState.OFFLINE
            elif self._device_state == DeviceState.ONLINE:
                _LOGGER.info(f"Device {self.device.device_id[:8]} is RECONNECTING...")
                self._device_state = DeviceState.RECONNECTING

            # Adjust poll interval based on new state
            self._adjust_poll_interval()

            # Don't raise UpdateFailed for timeouts - keep cached data
            return self._get_cached_data()

        except KKTConnectionError as err:
            self._consecutive_failures += 1
            self._reconnect_attempts += 1
            self._record_error("connection", str(err), recoverable=True)
            _LOGGER.warning(
                f"Connection error with device {self.device.device_id[:8]}: {err} "
                f"(failure #{self._consecutive_failures}, reconnect attempt #{self._reconnect_attempts})"
            )

            # Check circuit breaker before state transitions
            if not self._check_circuit_breaker():
                return self._get_cached_data()

            # Apply exponential backoff
            self._apply_exponential_backoff()

            # Mark as reconnecting after first failure, offline after threshold
            if self._consecutive_failures >= DEFAULT_CONSECUTIVE_FAILURES_THRESHOLD:
                if self._device_state not in (DeviceState.OFFLINE, DeviceState.UNREACHABLE):
                    _LOGGER.warning(f"Device {self.device.device_id[:8]} is now OFFLINE after {self._consecutive_failures} failures")
                    self._device_state = DeviceState.OFFLINE
            elif self._device_state == DeviceState.ONLINE:
                _LOGGER.info(f"Device {self.device.device_id[:8]} is RECONNECTING...")
                self._device_state = DeviceState.RECONNECTING

            # Adjust poll interval based on new state
            self._adjust_poll_interval()

            # Don't raise UpdateFailed for connection errors - keep cached data
            return self._get_cached_data()

        except Exception as err:
            self._consecutive_failures += 1
            self._reconnect_attempts += 1
            self._record_error("unexpected", str(err), recoverable=False)
            _LOGGER.error(
                f"Unexpected error communicating with device {self.device.device_id[:8]}: {err} "
                f"(failure #{self._consecutive_failures}, reconnect attempt #{self._reconnect_attempts})"
            )

            # Check circuit breaker before state transitions
            if not self._check_circuit_breaker():
                return self._get_cached_data()

            # Apply exponential backoff
            self._apply_exponential_backoff()

            # Mark as reconnecting after first failure, offline after threshold
            if self._consecutive_failures >= DEFAULT_CONSECUTIVE_FAILURES_THRESHOLD:
                if self._device_state not in (DeviceState.OFFLINE, DeviceState.UNREACHABLE):
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
            # Immediately refresh data after command (use async_refresh for immediate update)
            await self.async_refresh()
        except Exception as err:
            _LOGGER.error(f"Failed to set DP {dp} to {value}: {err}")
            raise UpdateFailed(f"Failed to set DP {dp}: {err}") from err

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for device registry."""
        from .device_types import get_device_info_by_product_name

        product_name = self.entry.data.get("product_name", "unknown")
        device_type_info = get_device_info_by_product_name(product_name)

        return DeviceInfo(
            identifiers={(DOMAIN, self.device.device_id)},
            name=self.entry.data.get("name", device_type_info["name"]),
            manufacturer="KKT Kolbe",
            model=device_type_info["name"],
            model_id=device_type_info["model_id"],
            sw_version=getattr(self.device, 'version', None),
            hw_version=self.device.device_id[:8],  # Use first 8 chars of device ID
            configuration_url=f"http://{self.device.ip_address}",
        )


# Backwards compatibility alias for tests
KKTKolbeDataUpdateCoordinator = KKTKolbeUpdateCoordinator
