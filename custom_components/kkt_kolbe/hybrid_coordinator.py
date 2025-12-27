"""Hybrid coordinator supporting both local and API communication."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import TuyaCloudClient, TuyaAPIError, TuyaDeviceNotFoundError
from .tuya_device import KKTKolbeTuyaDevice
from .exceptions import KKTConnectionError, KKTTimeoutError, KKTDataPointError
from .coordinator import DeviceState

_LOGGER = logging.getLogger(__name__)

# Polling intervals for different modes
POLL_INTERVAL_LOCAL = 30  # Local communication (seconds)
POLL_INTERVAL_API = 60  # API-only or fallback (seconds) - respect API rate limits
POLL_INTERVAL_RECONNECTING = 15  # Trying to reconnect to local (seconds)


class KKTKolbeHybridCoordinator(DataUpdateCoordinator):
    """Hybrid coordinator supporting both local and API communication."""

    def __init__(
        self,
        hass: HomeAssistant,
        device_id: str,
        local_device: KKTKolbeTuyaDevice | None = None,
        api_client: TuyaCloudClient | None = None,
        update_interval: timedelta = timedelta(seconds=30),
        prefer_local: bool = True,
        entry: ConfigEntry | None = None,
    ):
        """Initialize the hybrid coordinator."""
        self.device_id = device_id
        self.local_device = local_device
        self.api_client = api_client
        self.prefer_local = prefer_local
        self.entry = entry  # Store entry for compatibility with standard coordinator

        # Communication mode tracking
        self.local_available = local_device is not None
        self.api_available = api_client is not None
        self.current_mode = "local" if self.local_available else "api"

        # Error tracking for fallback decisions
        self.local_consecutive_errors = 0
        self.api_consecutive_errors = 0
        self.max_consecutive_errors = 3

        # Statistics tracking
        self._last_successful_update: datetime | None = None
        self._last_local_update: datetime | None = None
        self._last_api_update: datetime | None = None

        # Device state tracking for compatibility with base coordinator
        self._is_first_update = True

        super().__init__(
            hass,
            _LOGGER,
            name=f"KKT Kolbe {device_id[:8]} Hybrid",
            update_interval=update_interval,
        )

    @property
    def device(self) -> KKTKolbeTuyaDevice | None:
        """Get local device (compatibility property)."""
        return self.local_device

    @property
    def device_state(self) -> DeviceState:
        """Get current device state as DeviceState enum (compatible with KKTKolbeUpdateCoordinator)."""
        if self.local_consecutive_errors == 0 and self._last_successful_update:
            return DeviceState.ONLINE
        elif self.local_consecutive_errors < self.max_consecutive_errors:
            return DeviceState.RECONNECTING
        else:
            return DeviceState.OFFLINE

    @property
    def is_device_available(self) -> bool:
        """Check if device is available.

        Returns True if we have had a successful update or are in first update phase.
        """
        # Device is available if we had a recent successful update
        if self._last_successful_update and self.local_consecutive_errors < self.max_consecutive_errors:
            return True

        # During initial startup, treat as available to prevent flash of unavailable
        if self._is_first_update:
            return True

        # Also available if we have cached data
        if self.data is not None and len(self.data) > 0:
            return True

        return False

    @property
    def connection_info(self) -> dict[str, Any]:
        """Get connection status information."""
        return {
            "mode": self.current_mode,
            "local_available": self.local_available,
            "api_available": self.api_available,
            "local_errors": self.local_consecutive_errors,
            "api_errors": self.api_consecutive_errors,
            "last_update": self._last_successful_update.isoformat() if self._last_successful_update else None,
            "last_local_update": self._last_local_update.isoformat() if self._last_local_update else None,
            "last_api_update": self._last_api_update.isoformat() if self._last_api_update else None,
        }

    @property
    def last_update_success_time(self) -> datetime | None:
        """Get last successful update time (compatibility property)."""
        return self._last_successful_update

    @property
    def last_successful_update(self) -> datetime | None:
        """Get last successful update time (alias for last_update_success_time)."""
        return self._last_successful_update

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information for device registry (compatibility with standard coordinator)."""
        from .device_types import get_device_info_by_product_name
        from .const import DOMAIN

        # Get product name from entry if available
        product_name = "unknown"
        if self.entry:
            product_name = self.entry.data.get("product_name", "unknown")

        device_info = get_device_info_by_product_name(product_name)

        # Build device info dict
        info: dict[str, Any] = {
            "identifiers": {(DOMAIN, self.device_id)},
            "manufacturer": "KKT Kolbe",
            "model": device_info["name"],
            "model_id": device_info.get("model_id", "unknown"),
        }

        # Add name from entry if available
        if self.entry:
            info["name"] = self.entry.data.get("name", device_info["name"])
        else:
            info["name"] = device_info["name"]

        # Add version info from local device if available
        if self.local_device:
            info["sw_version"] = getattr(self.local_device, 'version', None)
            info["hw_version"] = self.device_id[:8]
            if hasattr(self.local_device, 'ip_address') and self.local_device.ip_address:
                info["configuration_url"] = f"http://{self.local_device.ip_address}"

        return info

    def _adjust_poll_interval(self) -> None:
        """Adjust polling interval based on current mode."""
        if self.current_mode == "local" and self.local_consecutive_errors == 0:
            new_interval = timedelta(seconds=POLL_INTERVAL_LOCAL)
        elif self.current_mode == "api":
            # API polling should be slower to respect rate limits
            new_interval = timedelta(seconds=POLL_INTERVAL_API)
        else:
            # Reconnecting - faster polling
            new_interval = timedelta(seconds=POLL_INTERVAL_RECONNECTING)

        if self.update_interval != new_interval:
            _LOGGER.debug(
                f"Device {self.device_id[:8]}: Adjusting poll interval to "
                f"{new_interval.total_seconds()}s (mode: {self.current_mode})"
            )
            self.update_interval = new_interval

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data using hybrid approach."""
        _LOGGER.debug(f"Updating data for device {self.device_id[:8]} in {self.current_mode} mode")

        # Adjust polling interval based on current state
        self._adjust_poll_interval()

        # Try primary mode first
        if self.current_mode == "local" and self.local_available:
            try:
                data = await self.async_update_local()
                self.local_consecutive_errors = 0
                self._last_successful_update = datetime.now()
                self._last_local_update = datetime.now()

                # Try to switch back to local after successful update
                if self.current_mode == "api" and self.prefer_local:
                    _LOGGER.info(f"Device {self.device_id[:8]} local recovered, switching back to local mode")
                    self.current_mode = "local"

                return data
            except (KKTConnectionError, KKTTimeoutError) as err:
                self.local_consecutive_errors += 1
                _LOGGER.warning(
                    f"Local communication failed (attempt {self.local_consecutive_errors}): {err}"
                )

                # Switch to API if too many local errors
                if (
                    self.local_consecutive_errors >= self.max_consecutive_errors
                    and self.api_available
                ):
                    _LOGGER.info("Switching to API mode due to persistent local communication issues")
                    self.current_mode = "api"

        # Try API mode (either as primary or fallback)
        if self.api_available:
            try:
                data = await self.async_update_via_api()
                self.api_consecutive_errors = 0
                self._last_successful_update = datetime.now()
                self._last_api_update = datetime.now()

                # If we were in fallback mode and API works, log it
                if self.current_mode != "api":
                    _LOGGER.debug("API communication successful as fallback")

                return data
            except TuyaAPIError as err:
                self.api_consecutive_errors += 1
                _LOGGER.warning(
                    f"API communication failed (attempt {self.api_consecutive_errors}): {err}"
                )

        # If both modes failed or unavailable, try hybrid approach
        if self.local_available and self.api_available:
            return await self.async_update_hybrid()

        # Last resort: return cached data or raise error
        if self.data:
            _LOGGER.warning("All communication methods failed, using cached data")
            return self.data

        raise UpdateFailed("All communication methods failed and no cached data available")

    async def async_update_local(self) -> dict[str, Any]:
        """Update data via local communication."""
        if not self.local_device:
            raise KKTConnectionError("Local device not configured")

        _LOGGER.debug(f"Fetching data via local communication for {self.device_id[:8]}")

        try:
            # Get current device status
            status = await self.local_device.async_get_status()

            if not status:
                raise KKTConnectionError("No data received from local device")

            return {
                "source": "local",
                "timestamp": asyncio.get_running_loop().time(),
                "dps": status,
                "available": True,
            }

        except Exception as err:
            raise KKTConnectionError(f"Local communication failed: {err}")

    async def async_update_via_api(self) -> dict[str, Any]:
        """Update data via API communication."""
        if not self.api_client:
            raise TuyaAPIError("API client not configured")

        _LOGGER.debug(f"Fetching data via API for {self.device_id}")

        try:
            # Get device status from API
            status_list = await self.api_client.get_device_status(self.device_id)

            # Convert API status format to DPS format
            dps = {}
            for status_item in status_list:
                code = status_item.get("code")
                value = status_item.get("value")

                # We need to map property codes back to DP numbers
                # This would ideally use the device configuration
                if code and value is not None:
                    # For now, use a simple mapping - this should be enhanced
                    # with proper DP mapping from device configuration
                    dp_mapping = await self._get_dp_mapping()
                    for dp_id, dp_code in dp_mapping.items():
                        if dp_code == code:
                            dps[str(dp_id)] = value
                            break

            return {
                "source": "api",
                "timestamp": asyncio.get_running_loop().time(),
                "dps": dps,
                "available": True,
                "raw_api_status": status_list,
            }

        except TuyaDeviceNotFoundError:
            raise TuyaAPIError(f"Device {self.device_id} not found in API")
        except Exception as err:
            raise TuyaAPIError(f"API communication failed: {err}")

    async def async_update_hybrid(self) -> dict[str, Any]:
        """Update data using hybrid approach - combine local and API data."""
        _LOGGER.debug(f"Updating data using hybrid approach for {self.device_id[:8]}")

        local_data = None
        api_data = None

        # Try to get data from both sources
        try:
            local_data = await self.async_update_local()
        except Exception as err:
            _LOGGER.debug(f"Local update failed in hybrid mode: {err}")

        try:
            api_data = await self.async_update_via_api()
        except Exception as err:
            _LOGGER.debug(f"API update failed in hybrid mode: {err}")

        # Determine best data to use
        if local_data and api_data:
            # Prefer local data but use API for verification
            _LOGGER.debug("Both local and API data available, using local with API verification")
            return self._merge_hybrid_data(local_data, api_data)
        elif local_data:
            _LOGGER.debug("Only local data available")
            return local_data
        elif api_data:
            _LOGGER.debug("Only API data available")
            return api_data
        else:
            raise UpdateFailed("Both local and API communication failed")

    def _merge_hybrid_data(self, local_data: dict, api_data: dict) -> dict:
        """Merge local and API data intelligently."""
        # Start with local data as base
        merged_data = local_data.copy()

        # Add API data as additional information
        merged_data["api_verification"] = api_data.get("raw_api_status", [])
        merged_data["source"] = "hybrid"

        # Compare DPS values for discrepancies
        local_dps = local_data.get("dps", {})
        api_dps = api_data.get("dps", {})

        discrepancies = {}
        for dp_id in set(local_dps.keys()) | set(api_dps.keys()):
            local_val = local_dps.get(dp_id)
            api_val = api_dps.get(dp_id)

            if local_val != api_val:
                discrepancies[dp_id] = {
                    "local": local_val,
                    "api": api_val,
                }

        if discrepancies:
            _LOGGER.debug(f"Data discrepancies found: {discrepancies}")
            merged_data["discrepancies"] = discrepancies

        return merged_data

    async def _get_dp_mapping(self) -> dict[int, str]:
        """Get DP to property code mapping for the device.

        This maps Tuya property codes to KKT Kolbe data point IDs.
        Used for converting API status responses to DPS format.
        """
        # Comprehensive mapping for KKT Kolbe devices
        return {
            # Common Hood DPs
            1: "switch",              # Main power
            4: "light",               # Light on/off
            5: "bright_value",        # Light brightness
            6: "switch_lamp",         # Filter status / Lamp switch
            7: "switch_wash",         # Wash mode
            10: "fan_speed_enum",     # Fan speed (enum)
            13: "countdown",          # Timer
            14: "filter_hour",        # Filter hours
            101: "RGB",               # RGB mode
            102: "fan_speed",         # Fan speed (numeric 0-9)
            103: "day",               # Carbon filter days
            104: "switch_led_1",      # LED switch
            105: "countdown_1",       # Timer (alternate)
            106: "switch_led",        # LED switch (alternate)
            107: "colour_data",       # RGB color data
            108: "work_mode",         # Work mode
            109: "day_1",             # Metal filter days

            # Cooktop DPs
            134: "timer",             # General timer
            145: "senior_mode",       # Senior mode
            148: "quick_level_1",     # Zone 1 quick level
            149: "quick_level_2",     # Zone 2 quick level
            150: "quick_level_3",     # Zone 3 quick level
            151: "quick_level_4",     # Zone 4 quick level
            152: "quick_level_5",     # Zone 5 quick level
            161: "zone_selected",     # Zone selection bitfield
            162: "zone_power",        # Zone power levels bitfield
            163: "zone_boost",        # Zone boost bitfield
            164: "zone_warm",         # Zone keep warm bitfield
            165: "flex_zone",         # Flex zone bitfield
            166: "bbq_mode",          # BBQ mode bitfield
            167: "zone_timer",        # Zone timers bitfield
            168: "zone_core_temp",    # Zone core sensor temp bitfield
            169: "zone_display_temp", # Zone display temp bitfield
        }

    async def async_try_recover_local(self) -> bool:
        """Try to recover local connection when in API mode.

        Returns True if local connection was recovered.
        """
        if not self.local_device or self.current_mode != "api":
            return False

        _LOGGER.debug(f"Device {self.device_id[:8]}: Attempting to recover local connection")

        try:
            # Try to reconnect
            await self.local_device.async_connect()

            # Test with a status request
            status = await self.local_device.async_get_status()
            if status:
                _LOGGER.info(f"Device {self.device_id[:8]}: Local connection recovered!")
                self.local_consecutive_errors = 0
                self.current_mode = "local"
                self._adjust_poll_interval()
                return True

        except Exception as err:
            _LOGGER.debug(f"Device {self.device_id[:8]}: Local recovery failed: {err}")

        return False

    async def async_set_data_point(self, dp: int, value: Any) -> None:
        """Set a data point on the device (compatibility wrapper for async_send_command)."""
        success, error_msg = await self.async_send_command(dp, value)
        if not success:
            raise KKTDataPointError(
                dp=dp,
                operation="set",
                value=value,
                device_id=self.device_id,
                reason=error_msg,
            )

    async def async_send_command(self, dp_id: int, value: Any) -> tuple[bool, str]:
        """Send command using available communication method.

        Returns:
            Tuple of (success: bool, error_message: str)
        """
        _LOGGER.debug(f"Sending command to DP {dp_id}: {value}")
        last_error = ""

        # Try local first if available and preferred
        if self.local_available and (self.prefer_local or self.current_mode == "local"):
            try:
                if self.local_device is None:
                    last_error = "Local device not initialized"
                    _LOGGER.warning(last_error)
                else:
                    result = await self.local_device.async_set_dp(dp_id, value)
                    if result:
                        _LOGGER.debug("Command sent successfully via local communication")
                        # Trigger immediate update to reflect change
                        await self.async_request_refresh()
                        return True, ""
                    else:
                        last_error = "Local device returned False (command rejected or device offline)"
                        _LOGGER.warning(f"Local command failed: {last_error}")
            except Exception as err:
                last_error = f"Local communication error: {err}"
                _LOGGER.warning(last_error)
        else:
            if not self.local_available:
                last_error = "Local connection not available"
            else:
                last_error = f"Local not preferred (mode={self.current_mode})"
            _LOGGER.debug(f"Skipping local: {last_error}")

        # Try API if local failed or not preferred
        if self.api_available and self.api_client:
            try:
                # Send command via API
                success = await self.api_client.send_dp_command(
                    self.device_id, dp_id, value
                )
                if success:
                    _LOGGER.info(f"Command sent successfully via API to DP {dp_id}")
                    # Trigger immediate update to reflect change
                    await self.async_request_refresh()
                    return True, ""
                else:
                    last_error = "API command returned False (rejected by device or API)"
                    _LOGGER.warning(last_error)
            except Exception as err:
                last_error = f"API error: {err}"
                _LOGGER.warning(last_error)
        elif not self.api_available:
            _LOGGER.debug("API not available for fallback")

        _LOGGER.error(f"All command sending methods failed: {last_error}")
        return False, last_error

    def set_local_device(self, device: KKTKolbeTuyaDevice) -> None:
        """Set or update the local device."""
        self.local_device = device
        self.local_available = True
        if self.prefer_local:
            self.current_mode = "local"
            self.local_consecutive_errors = 0

    def set_api_client(self, client: TuyaCloudClient) -> None:
        """Set or update the API client."""
        self.api_client = client
        self.api_available = True
        if not self.local_available:
            self.current_mode = "api"
            self.api_consecutive_errors = 0