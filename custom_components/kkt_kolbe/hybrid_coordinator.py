"""Hybrid coordinator supporting both local and API communication."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import TuyaCloudClient, TuyaAPIError, TuyaDeviceNotFoundError
from .tuya_device import KKTKolbeTuyaDevice
from .exceptions import KKTConnectionError, KKTTimeoutError

_LOGGER = logging.getLogger(__name__)


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
    ):
        """Initialize the hybrid coordinator."""
        self.device_id = device_id
        self.local_device = local_device
        self.api_client = api_client
        self.prefer_local = prefer_local

        # Communication mode tracking
        self.local_available = local_device is not None
        self.api_available = api_client is not None
        self.current_mode = "local" if self.local_available else "api"

        # Error tracking for fallback decisions
        self.local_consecutive_errors = 0
        self.api_consecutive_errors = 0
        self.max_consecutive_errors = 3

        super().__init__(
            hass,
            _LOGGER,
            name=f"KKT Kolbe {device_id[:8]} Hybrid",
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data using hybrid approach."""
        _LOGGER.debug(f"Updating data for device {self.device_id[:8]} in {self.current_mode} mode")

        # Try primary mode first
        if self.current_mode == "local" and self.local_available:
            try:
                data = await self.async_update_local()
                self.local_consecutive_errors = 0
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

                # If we were in fallback mode and API works, consider it primary
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

    def _merge_hybrid_data(self, local_data: Dict, api_data: Dict) -> Dict:
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
        """Get DP to property code mapping for the device."""
        # This should be enhanced to use actual device configuration
        # For now, return a basic mapping for common KKT Kolbe devices
        return {
            1: "switch",
            4: "light",
            6: "switch_lamp",
            7: "switch_wash",
            10: "fan_speed_enum",
            13: "countdown",
            101: "RGB",
            102: "fan_speed",
            103: "day",
            104: "switch_led_1",
            105: "countdown_1",
            106: "switch_led",
            107: "colour_data",
            108: "work_mode",
            109: "day_1",
        }

    async def async_set_data_point(self, dp: int, value: Any) -> None:
        """Set a data point on the device (compatibility wrapper for async_send_command)."""
        success = await self.async_send_command(dp, value)
        if not success:
            raise Exception(f"Failed to set DP {dp} to {value}")

    async def async_send_command(self, dp_id: int, value: Any) -> bool:
        """Send command using available communication method."""
        _LOGGER.debug(f"Sending command to DP {dp_id}: {value}")

        # Try local first if available and preferred
        if self.local_available and (self.prefer_local or self.current_mode == "local"):
            try:
                result = await self.local_device.async_set_dp(dp_id, value)
                if result:
                    _LOGGER.debug("Command sent successfully via local communication")
                    # Trigger immediate update to reflect change
                    await self.async_request_refresh()
                    return True
            except Exception as err:
                _LOGGER.warning(f"Local command failed: {err}")

        # Try API if local failed or not preferred
        if self.api_available:
            try:
                # API command sending would need to be implemented
                # This is a placeholder for the actual API command implementation
                _LOGGER.warning("API command sending not yet implemented")
                return False
            except Exception as err:
                _LOGGER.warning(f"API command failed: {err}")

        _LOGGER.error("All command sending methods failed")
        return False

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