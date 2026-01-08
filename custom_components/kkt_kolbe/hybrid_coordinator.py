"""Hybrid coordinator supporting both local and API communication."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.update_coordinator import UpdateFailed

from .api import TuyaAPIError
from .api import TuyaCloudClient
from .api import TuyaDeviceNotFoundError
from .api import TuyaRateLimitError
from .exceptions import KKTConnectionError
from .exceptions import KKTRateLimitError
from .exceptions import KKTTimeoutError
from .tuya_device import KKTKolbeTuyaDevice

if TYPE_CHECKING:
    from .clients.tuya_sharing_client import TuyaSharingClient

_LOGGER = logging.getLogger(__name__)


class KKTKolbeHybridCoordinator(DataUpdateCoordinator):
    """Hybrid coordinator supporting both local and API communication."""

    def __init__(
        self,
        hass: HomeAssistant,
        device_id: str,
        local_device: KKTKolbeTuyaDevice | None = None,
        api_client: TuyaCloudClient | None = None,
        smartlife_client: TuyaSharingClient | None = None,
        update_interval: timedelta = timedelta(seconds=30),
        prefer_local: bool = True,
        entry: ConfigEntry | None = None,
        device_type: str | None = None,
    ):
        """Initialize the hybrid coordinator.

        Args:
            hass: Home Assistant instance
            device_id: Tuya device ID
            local_device: Local LAN device for direct communication
            api_client: TuyaCloudClient for IoT Platform API (requires developer account)
            smartlife_client: TuyaSharingClient for SmartLife cloud fallback
            update_interval: How often to poll for updates
            prefer_local: Whether to prefer local communication over cloud
            entry: Config entry reference
            device_type: Device type key from KNOWN_DEVICES
        """
        self.device_id = device_id
        self.local_device = local_device
        self.api_client = api_client
        self.smartlife_client = smartlife_client
        self.prefer_local = prefer_local
        self.config_entry = entry
        self.device_type = device_type

        # Communication mode tracking
        self.local_available = local_device is not None
        self.api_available = api_client is not None
        self.smartlife_available = smartlife_client is not None
        self.current_mode = "local" if self.local_available else ("api" if self.api_available else "smartlife")

        # Error tracking for fallback decisions
        self.local_consecutive_errors = 0
        self.api_consecutive_errors = 0
        self.max_consecutive_errors = 3

        # Timestamp tracking for last successful update
        self._last_update_success_time: datetime | None = None

        # DPS cache for merging partial updates
        # Tuya devices often send delta/partial updates (only changed DPs)
        # This cache accumulates all DPs seen so far
        self._dps_cache: dict[str, Any] = {}

        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"KKT Kolbe {device_id[:8]} Hybrid",
            update_interval=update_interval,
            # Prevent unnecessary state writes when data hasn't changed
            # Critical performance optimization for high-frequency updates
            always_update=False,
        )

    @property
    def last_update_success_time(self) -> datetime | None:
        """Return the timestamp of the last successful update."""
        return self._last_update_success_time

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data using hybrid approach."""
        _LOGGER.debug(f"Updating data for device {self.device_id[:8]} in {self.current_mode} mode")

        # Try primary mode first
        if self.current_mode == "local" and self.local_available:
            try:
                data = await self.async_update_local()
                self.local_consecutive_errors = 0
                self._last_update_success_time = datetime.now()
                return data
            except (KKTConnectionError, KKTTimeoutError) as err:
                self.local_consecutive_errors += 1
                _LOGGER.warning(
                    f"Local communication failed (attempt {self.local_consecutive_errors}): {err}"
                )

                # Switch to cloud if too many local errors
                if self.local_consecutive_errors >= self.max_consecutive_errors:
                    if self.api_available:
                        _LOGGER.info("Switching to API mode due to persistent local issues")
                        self.current_mode = "api"
                    elif self.smartlife_available:
                        _LOGGER.info("Switching to SmartLife mode due to persistent local issues")
                        self.current_mode = "smartlife"

        # Try API mode (IoT Platform)
        if self.api_available and self.current_mode in ["api", "local"]:
            try:
                data = await self.async_update_via_api()
                self.api_consecutive_errors = 0
                self._last_update_success_time = datetime.now()

                if self.current_mode != "api":
                    _LOGGER.debug("API communication successful as fallback")

                return data
            except (KKTRateLimitError, TuyaRateLimitError) as err:
                # HA 2025.12+: Propagate rate limit with retry_after
                retry_after = getattr(err, 'retry_after', None)
                _LOGGER.warning(
                    f"API rate limited for device {self.device_id[:8]}: "
                    f"retry after {retry_after}s" if retry_after else "no retry_after specified"
                )
                if retry_after:
                    raise UpdateFailed(
                        f"Rate limited: retry after {retry_after}s",
                        retry_after=retry_after,
                    ) from err
                raise UpdateFailed("Rate limited by Tuya API") from err
            except TuyaAPIError as err:
                self.api_consecutive_errors += 1
                _LOGGER.warning(
                    f"API communication failed (attempt {self.api_consecutive_errors}): {err}"
                )

        # Try SmartLife mode (cloud fallback for SmartLife users)
        if self.smartlife_available:
            try:
                data = await self.async_update_via_smartlife()
                self._last_update_success_time = datetime.now()

                if self.current_mode != "smartlife":
                    _LOGGER.debug("SmartLife communication successful as fallback")

                return data
            except Exception as err:
                _LOGGER.warning(f"SmartLife communication failed: {err}")

        # If multiple modes available, try hybrid approach
        if self.local_available and (self.api_available or self.smartlife_available):
            data = await self.async_update_hybrid()
            self._last_update_success_time = datetime.now()
            return data

        # Last resort: return cached data or raise error
        if self.data:
            _LOGGER.warning("All communication methods failed, using cached data")
            cached_data: dict[str, Any] = self.data
            return cached_data

        raise UpdateFailed("All communication methods failed and no cached data available")

    async def async_update_local(self) -> dict[str, Any]:
        """Update data via local communication.

        Important: Tuya devices often send partial/delta updates (only changed DPs).
        This method merges each partial update into a persistent cache, so all
        previously seen DPs remain available even if not included in the latest update.
        """
        if not self.local_device:
            raise KKTConnectionError("Local device not configured")

        _LOGGER.debug(f"Fetching data via local communication for {self.device_id[:8]}")

        try:
            # Get current device status (may be partial update)
            partial_status = await self.local_device.async_get_status()

            if not partial_status:
                raise KKTConnectionError("No data received from local device")

            # Merge partial update into our cache
            # This ensures we keep all DPs seen across multiple updates
            partial_count = len(partial_status)
            self._dps_cache.update(partial_status)

            # Log if we're merging partial updates
            if partial_count < len(self._dps_cache):
                _LOGGER.debug(
                    f"Device {self.device_id[:8]}: Merged {partial_count} DPs into cache "
                    f"(total cached: {len(self._dps_cache)} DPs)"
                )

            _LOGGER.debug(f"Device {self.device_id[:8]} returning merged data with {len(self._dps_cache)} DPs: {list(self._dps_cache.keys())}")

            return {
                "source": "local",
                "timestamp": asyncio.get_running_loop().time(),
                "dps": self._dps_cache.copy(),
                "available": True,
            }

        except Exception as err:
            raise KKTConnectionError(f"Local communication failed: {err}") from err

    async def async_update_via_api(self) -> dict[str, Any]:
        """Update data via API communication.

        Also merges partial updates into the DPS cache for consistency.
        """
        if not self.api_client:
            raise TuyaAPIError("API client not configured")

        _LOGGER.debug(f"Fetching data via API for {self.device_id}")

        try:
            # Get device status from API
            status_list = await self.api_client.get_device_status(self.device_id)

            # Convert API status format to DPS format
            api_dps: dict[str, Any] = {}
            for status_item in status_list:
                if not isinstance(status_item, dict):
                    continue
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
                            api_dps[str(dp_id)] = value
                            break

            # Merge API data into cache as well
            if api_dps:
                self._dps_cache.update(api_dps)

            return {
                "source": "api",
                "timestamp": asyncio.get_running_loop().time(),
                "dps": self._dps_cache.copy(),
                "available": True,
                "raw_api_status": status_list,
            }

        except TuyaDeviceNotFoundError as err:
            raise TuyaAPIError(f"Device {self.device_id} not found in API") from err
        except Exception as err:
            raise TuyaAPIError(f"API communication failed: {err}") from err

    async def async_update_via_smartlife(self) -> dict[str, Any]:
        """Update data via SmartLife cloud (tuya-device-sharing-sdk).

        This is the cloud fallback for users who authenticated via SmartLife app
        QR code instead of Tuya IoT Developer Platform.
        """
        if not self.smartlife_client:
            raise KKTConnectionError("SmartLife client not configured")

        _LOGGER.debug(f"Fetching data via SmartLife for {self.device_id[:8]}")

        try:
            # Get device status from SmartLife cloud
            status_list = await self.smartlife_client.async_get_device_status(self.device_id)

            # Convert SmartLife status format to DPS format
            smartlife_dps: dict[str, Any] = {}

            # DEBUG: Log all raw property codes AND values from SmartLife
            raw_codes = [item.get("code") for item in status_list if isinstance(item, dict)]
            _LOGGER.info(f"SmartLife raw property codes for {self.device_id[:8]}: {raw_codes}")
            # Log full status items to see if there are sub-properties (e.g., for RGB)
            for item in status_list:
                if isinstance(item, dict):
                    _LOGGER.info(
                        "SmartLife %s: code=%s, value=%s (type=%s)",
                        self.device_id[:8], item.get("code"), item.get("value"),
                        type(item.get("value")).__name__
                    )

            for status_item in status_list:
                if not isinstance(status_item, dict):
                    continue
                code = status_item.get("code")
                value = status_item.get("value")

                if code and value is not None:
                    # Map property codes back to DP numbers
                    dp_mapping = await self._get_dp_mapping()
                    for dp_id, dp_code in dp_mapping.items():
                        if dp_code == code:
                            smartlife_dps[str(dp_id)] = value
                            break

            # Merge SmartLife data into cache
            if smartlife_dps:
                self._dps_cache.update(smartlife_dps)

            _LOGGER.debug(
                f"SmartLife returned {len(status_list)} status items, "
                f"mapped to {len(smartlife_dps)} DPs"
            )

            return {
                "source": "smartlife",
                "timestamp": asyncio.get_running_loop().time(),
                "dps": self._dps_cache.copy(),
                "available": True,
                "raw_smartlife_status": status_list,
            }

        except Exception as err:
            raise KKTConnectionError(f"SmartLife communication failed: {err}") from err

    async def async_update_hybrid(self) -> dict[str, Any]:
        """Update data using hybrid approach - combine local and cloud data."""
        _LOGGER.debug(f"Updating data using hybrid approach for {self.device_id[:8]}")

        local_data = None
        cloud_data = None

        # Try to get data from local
        if self.local_available:
            try:
                local_data = await self.async_update_local()
            except Exception as err:
                _LOGGER.debug(f"Local update failed in hybrid mode: {err}")

        # Try to get data from cloud (API or SmartLife)
        if self.api_available:
            try:
                cloud_data = await self.async_update_via_api()
            except Exception as err:
                _LOGGER.debug(f"API update failed in hybrid mode: {err}")

        if not cloud_data and self.smartlife_available:
            try:
                cloud_data = await self.async_update_via_smartlife()
            except Exception as err:
                _LOGGER.debug(f"SmartLife update failed in hybrid mode: {err}")

        # Determine best data to use
        if local_data and cloud_data:
            # Prefer local data but use cloud for verification
            _LOGGER.debug("Both local and cloud data available, using local with cloud verification")
            return self._merge_hybrid_data(local_data, cloud_data)
        elif local_data:
            _LOGGER.debug("Only local data available")
            return local_data
        elif cloud_data:
            _LOGGER.debug("Only cloud data available")
            return cloud_data
        else:
            raise UpdateFailed("Both local and cloud communication failed")

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

        Tries to load mapping from device_types.py based on device_type,
        falls back to a generic mapping if not found.
        """
        # Try to get device-specific mapping from device_types
        if self.device_type:
            from .device_types import KNOWN_DEVICES
            device_config = KNOWN_DEVICES.get(self.device_type, {})
            data_points = device_config.get("data_points", {})
            if data_points:
                _LOGGER.debug(f"Using device-specific DP mapping for {self.device_type}")
                return data_points

        # Fallback to generic mapping for common KKT Kolbe devices
        _LOGGER.debug("Using generic DP mapping (no device-specific config found)")
        return {
            # Hood DPs
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
            # Cooktop DPs (IND7705HC)
            134: "general_timer",
            145: "child_lock",
            155: "power_limit",
            161: "zone_power_bitfield",
            162: "zone_levels_bitfield",
            163: "zone_boost_bitfield",
            164: "zone_keep_warm_bitfield",
            165: "zone_timer_bitfield",
            166: "zone_temp_bitfield",
            167: "zone_timer_remaining",
            168: "zone_target_temp",
            169: "zone_current_temp",
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
        if self.local_available and self.local_device and (self.prefer_local or self.current_mode == "local"):
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
        if self.api_available and self.api_client:
            try:
                # Get DP-to-property-code mapping for API commands
                dp_mapping = await self._get_dp_mapping()
                property_code = dp_mapping.get(dp_id)

                if property_code:
                    # Send command via Tuya Cloud API using property code
                    _LOGGER.debug(f"Attempting API command for DP {dp_id} (code: {property_code}): {value}")
                    commands = [{"code": property_code, "value": value}]
                    result = await self.api_client.send_commands(
                        self.device_id,
                        commands
                    )
                else:
                    # Fallback: try sending DP ID directly (iot-03 API)
                    _LOGGER.debug(f"No property code for DP {dp_id}, trying DP ID directly")
                    result = await self.api_client.send_dp_commands(
                        self.device_id,
                        {str(dp_id): value}
                    )

                if result:
                    _LOGGER.info(f"Command sent successfully via API for DP {dp_id}")
                    # Trigger update to reflect change
                    await self.async_request_refresh()
                    return True
                else:
                    _LOGGER.warning(f"API command returned failure for DP {dp_id}")
            except Exception as err:
                _LOGGER.warning(f"API command failed: {err}")

        # Try SmartLife if local and API failed
        if self.smartlife_available and self.smartlife_client:
            try:
                # Get DP-to-property-code mapping for SmartLife commands
                dp_mapping = await self._get_dp_mapping()
                property_code = dp_mapping.get(dp_id)

                if property_code:
                    _LOGGER.debug(f"Attempting SmartLife command for DP {dp_id} (code: {property_code}): {value}")
                    commands = [{"code": property_code, "value": value}]
                    result = await self.smartlife_client.async_send_commands(
                        self.device_id,
                        commands
                    )
                else:
                    # Try sending DP ID directly
                    _LOGGER.debug(f"No property code for DP {dp_id}, trying DP ID directly via SmartLife")
                    result = await self.smartlife_client.async_send_dp_commands(
                        self.device_id,
                        {str(dp_id): value}
                    )

                if result:
                    _LOGGER.info(f"Command sent successfully via SmartLife for DP {dp_id}")
                    await self.async_request_refresh()
                    return True
                else:
                    _LOGGER.warning(f"SmartLife command returned failure for DP {dp_id}")
            except Exception as err:
                _LOGGER.warning(f"SmartLife command failed: {err}")

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

    def set_smartlife_client(self, client: TuyaSharingClient) -> None:
        """Set or update the SmartLife client."""
        self.smartlife_client = client
        self.smartlife_available = True
        if not self.local_available and not self.api_available:
            self.current_mode = "smartlife"


# Backwards compatibility alias for tests
HybridCoordinator = KKTKolbeHybridCoordinator
