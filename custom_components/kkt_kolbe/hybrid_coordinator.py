"""Hybrid coordinator supporting both local and API communication."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.core import callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.update_coordinator import UpdateFailed

from .api import TuyaAPIError
from .api import TuyaCloudClient
from .api import TuyaDeviceNotFoundError
from .api import TuyaRateLimitError
from .exceptions import KKTAuthenticationError
from .exceptions import KKTConnectionError
from .exceptions import KKTRateLimitError
from .exceptions import KKTTimeoutError
from .tuya_device import KKTKolbeTuyaDevice

if TYPE_CHECKING:
    from .clients.tuya_sharing_client import TuyaSharingClient

_LOGGER = logging.getLogger(__name__)

# Common Tuya cloud error codes seen in send_commands responses. Tuya's docs
# are notoriously incomplete — these mappings are based on field observation
# and the public Tuya OpenAPI documentation. Used to give users actionable
# error messages instead of raw integers.
_TUYA_ERROR_CODES: dict[str, str] = {
    "1004": "request signature invalid (token expired or wrong client)",
    "1010": "token invalid (re-authenticate via Reconfigure)",
    "1100": "param missing or malformed",
    "1106": "permission denied (token lacks scope or device not bound to user)",
    "1109": "param value invalid (value out of range or wrong type for the code)",
    "2001": "device not found in cloud (device removed or wrong device_id)",
    "2008": "device offline OR command code not in device.function (most common: stale spec)",
    "2009": "device hardware error (device firmware / hardware reported failure)",
    "28841105": "no permission for this device (device unbound from user)",
}


def _decode_tuya_error_code(raw_error: str) -> str | None:
    """Extract a Tuya error code from a raw exception string and decode it.

    The SDK surfaces errors like ``"network error:(2008) 2008"`` — a parenthesised
    code plus repeated number. We extract the integer and look it up in our
    known-codes table. Returns a human-readable explanation or ``None`` if no
    known code is found.
    """
    import re

    match = re.search(r"\((\d{4,8})\)", raw_error)
    if not match:
        # Fallback: standalone integer at the end of the string
        match = re.search(r"\b(\d{4,8})\b", raw_error)
    if not match:
        return None
    return _TUYA_ERROR_CODES.get(match.group(1))


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

        # Self-healing local_key resync (Error 914 recovery). Throttle to avoid
        # spamming SmartLife API when key really is correct but Wi-Fi is flaky.
        self._last_key_resync_attempt: datetime | None = None
        self._key_resync_min_interval = timedelta(minutes=10)

        # Timestamp tracking for last successful update
        self._last_update_success_time: datetime | None = None

        # Background connect tracking (non-blocking setup)
        self._initial_connect_done = False

        # DPS cache for merging partial updates
        # Tuya devices often send delta/partial updates (only changed DPs)
        # This cache accumulates all DPs seen so far
        self._dps_cache: dict[str, Any] = {}

        # MQTT push state — see docs/superpowers/specs/2026-05-04-mqtt-push-listener-design.md
        self.last_update_was_push: bool = False
        self.last_push_report_type: str = ""
        self._push_callback_registered: bool = False

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

    @property
    def smartlife_device_online(self) -> bool | None:
        """Return ``device.online`` from the SmartLife SDK cache.

        This is Tuya cloud's authoritative view of whether the device is
        currently reachable via MQTT (mirrors what the Tuya app shows). In
        SmartLife mode this is more reliable than our internal
        ``connection_state`` state machine, which only tracks our own send/poll
        attempts. HA-Core's official Tuya integration uses ``device.online``
        directly for entity availability — adopting the same pattern is on
        the v4.8 roadmap.

        Returns:
            ``True`` / ``False`` if the SmartLife client knows the device,
            ``None`` if SmartLife is not configured or the device is not in
            the cache yet (caller should fall back to other availability
            signals).
        """
        if not self.smartlife_client or not hasattr(self.smartlife_client, "_manager"):
            return None
        manager = self.smartlife_client._manager
        if not manager or not hasattr(manager, "device_map"):
            return None
        device = manager.device_map.get(self.device_id)
        if device is None:
            return None
        return bool(getattr(device, "online", False))

    def mark_initial_connect_done(self) -> None:
        """Mark that the background connection attempt has completed."""
        self._initial_connect_done = True

    @callback
    def _handle_push_update(self, updated_dps: dict[str, Any], report_type: str) -> None:
        """Handle an MQTT push update from the SmartLife SDK.

        Called by TuyaSharingClient._dispatch_push on the HA event loop.
        Merges changed DPs into our cache, marks the next coordinator update
        as push-originated so entities can hard-release optimistic locks on
        confirmed writes (see KKTBaseEntity._handle_coordinator_update),
        and triggers immediate state fan-out.

        This callback is synchronous — never await or block here. To trigger
        async work, use self.hass.async_create_task(...).
        """
        self._dps_cache.update({str(k): v for k, v in updated_dps.items()})

        new_data = {
            "dps": dict(self._dps_cache),
            "source": "smartlife_push",
            "timestamp": datetime.now().isoformat(),
        }
        self.last_update_was_push = True
        self.last_push_report_type = report_type
        try:
            self.async_set_updated_data(new_data)
        finally:
            # Reset after fan-out so subsequent polled updates aren't mistaken for pushes
            self.last_update_was_push = False
            self.last_push_report_type = ""

    async def async_register_push(self) -> None:
        """Register the MQTT push callback with the SmartLife client.

        Called by __init__.py during entry setup, after the coordinator is
        constructed and the SmartLife client (if any) is wired in. Safe to
        call when smartlife_client is None — silently skips registration for
        local-only setups.

        Also runs the cloud-spec audit: compares our hardcoded device-type
        DP mapping against what Tuya cloud actually exposes for this device,
        logs the mismatch, and creates a repair issue if any DPs are
        local-only AND no local_device is configured.

        Note: We deliberately do NOT use async_added_to_hass here.
        DataUpdateCoordinator (unlike Entity) has no such lifecycle hook,
        so HA would never invoke it in production — see commit history for
        the v4.7 critical-bug fix.
        """
        if self.smartlife_client is None or self._push_callback_registered:
            return
        self.smartlife_client.register_push_callback(self.device_id, self._handle_push_update)
        self._push_callback_registered = True
        await self._audit_cloud_spec_coverage()

    async def _audit_cloud_spec_coverage(self) -> None:
        """Audit which device DPs are local-only vs cloud-supported.

        Loads the live ``device.local_strategy`` from the SDK and compares
        against our hardcoded ``device_types.py`` data_points mapping.
        Logs every DP that the cloud does NOT know about, and — if no
        local_device is configured — raises a repair issue so the user
        sees a fix-it card in the HA UI.
        """
        if not hasattr(self.smartlife_client, "get_device_codes"):
            return
        live_codes = self.smartlife_client.get_device_codes(self.device_id)
        if not live_codes:
            return

        expected_dps = await self._get_dp_mapping()
        if not expected_dps:
            return

        local_only_dps = [dp for dp in expected_dps if dp not in live_codes]
        if not local_only_dps:
            _LOGGER.debug("Device %s: cloud-spec covers all expected DPs", self.device_id[:8])
            return

        _LOGGER.info(
            "Device %s: %d DP(s) are local-only (cloud-spec missing): %s. "
            "These features will only work over the local Tuya protocol — "
            "ensure a LAN IP is configured.",
            self.device_id[:8],
            len(local_only_dps),
            ", ".join(f"DP{dp}={expected_dps[dp]}" for dp in sorted(local_only_dps)),
        )

        if not self.local_available:
            try:
                from homeassistant.helpers import issue_registry as ir

                from .const import DOMAIN

                ir.async_create_issue(
                    self.hass,
                    DOMAIN,
                    f"local_only_dp_no_ip_{self.device_id}",
                    is_fixable=False,
                    severity=ir.IssueSeverity.WARNING,
                    translation_key="local_only_dp_no_ip",
                    translation_placeholders={
                        "device_id_short": self.device_id[:8],
                        "missing_dps": ", ".join(f"DP{dp}={expected_dps[dp]}" for dp in sorted(local_only_dps)),
                    },
                    learn_more_url="https://github.com/moag1000/HA-kkt-kolbe-integration#local-only-features",
                )
            except Exception as err:
                _LOGGER.debug("Failed to create local-only-dp repair issue: %s", err)

    async def async_shutdown(self) -> None:
        """Unregister the push callback before tearing down the coordinator."""
        if self._push_callback_registered and self.smartlife_client is not None:
            self.smartlife_client.unregister_push_callback(self.device_id, self._handle_push_update)
            self._push_callback_registered = False
        await super().async_shutdown()

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data using hybrid approach."""
        # Before background connect completes, return empty data immediately
        if not self._initial_connect_done and not self._dps_cache:
            _LOGGER.debug("Device %s: awaiting background connection, skipping update", self.device_id[:8])
            return {"dps": {}, "source": "pending", "available": False}

        _LOGGER.debug(f"Updating data for device {self.device_id[:8]} in {self.current_mode} mode")

        # Try primary mode first
        if self.current_mode == "local" and self.local_available:
            try:
                data = await self.async_update_local()
                self.local_consecutive_errors = 0
                self._last_update_success_time = datetime.now()
                return data
            except KKTAuthenticationError as err:
                # Error 914 / decrypt failures = stale local_key. Try to pull a
                # fresh key from SmartLife and retry once before giving up to cloud.
                _LOGGER.warning(
                    "Local auth failed for device %s (likely stale local_key): %s",
                    self.device_id[:8],
                    err,
                )
                if await self._async_try_resync_local_key():
                    try:
                        data = await self.async_update_local()
                        self.local_consecutive_errors = 0
                        self._last_update_success_time = datetime.now()
                        _LOGGER.info(
                            "Self-heal succeeded: local_key resynced from SmartLife for device %s",
                            self.device_id[:8],
                        )
                        return data
                    except (KKTAuthenticationError, KKTConnectionError, KKTTimeoutError) as retry_err:
                        _LOGGER.warning(
                            "Retry after key resync still failed for device %s: %s",
                            self.device_id[:8],
                            retry_err,
                        )
                self.local_consecutive_errors += 1
                if self.local_consecutive_errors >= self.max_consecutive_errors:
                    if self.api_available:
                        _LOGGER.info("Switching to API mode after failed key resync")
                        self.current_mode = "api"
                    elif self.smartlife_available:
                        _LOGGER.info("Switching to SmartLife mode after failed key resync")
                        self.current_mode = "smartlife"
            except (KKTConnectionError, KKTTimeoutError) as err:
                self.local_consecutive_errors += 1
                _LOGGER.warning(f"Local communication failed (attempt {self.local_consecutive_errors}): {err}")

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
                retry_after = getattr(err, "retry_after", None)
                _LOGGER.warning(
                    f"API rate limited for device {self.device_id[:8]}: retry after {retry_after}s"
                    if retry_after
                    else "no retry_after specified"
                )
                if retry_after:
                    raise UpdateFailed(
                        f"Rate limited: retry after {retry_after}s",
                        retry_after=retry_after,
                    ) from err
                raise UpdateFailed("Rate limited by Tuya API") from err
            except TuyaAPIError as err:
                self.api_consecutive_errors += 1
                _LOGGER.warning(f"API communication failed (attempt {self.api_consecutive_errors}): {err}")

        # Try SmartLife mode (cloud fallback for SmartLife users)
        if self.smartlife_available:
            try:
                data = await self.async_update_via_smartlife()
                self._last_update_success_time = datetime.now()

                if self.current_mode != "smartlife":
                    _LOGGER.debug("SmartLife communication successful as fallback")

                return data
            except ConfigEntryAuthFailed:
                # Auth errors must propagate to trigger HA's reauth flow
                raise
            except Exception as err:
                _LOGGER.debug("SmartLife communication failed: %s", err)

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

        _LOGGER.warning("All communication methods failed for device %s, no cached data", self.device_id[:8])
        return {"dps": {}, "source": "failed", "available": False}

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

            _LOGGER.debug(
                f"Device {self.device_id[:8]} returning merged data with {len(self._dps_cache)} DPs: {list(self._dps_cache.keys())}"
            )

            return {
                "source": "local",
                "timestamp": asyncio.get_running_loop().time(),
                "dps": self._dps_cache.copy(),
                "available": True,
            }

        except KKTAuthenticationError:
            # Preserve auth-error type so the coordinator can trigger key resync.
            raise
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
                        self.device_id[:8],
                        item.get("code"),
                        item.get("value"),
                        type(item.get("value")).__name__,
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

            _LOGGER.debug(f"SmartLife returned {len(status_list)} status items, mapped to {len(smartlife_dps)} DPs")

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
        success, reason = await self._async_send_command_with_reason(dp, value)
        if not success:
            raise HomeAssistantError(f"Failed to set DP {dp} to {value} — {reason}")

    async def _async_send_command_with_reason(self, dp_id: int, value: Any) -> tuple[bool, str]:
        """Send command and return (success, reason). Wrapper around async_send_command
        that captures the underlying failure reason for error messages."""
        # We re-implement the dispatch here so we can capture the actual error message.
        # See async_send_command for the original behavior.
        _LOGGER.debug(f"Sending command to DP {dp_id}: {value}")
        last_error: str = "no communication method available"

        if self.local_available and self.local_device and (self.prefer_local or self.current_mode == "local"):
            try:
                result = await self.local_device.async_set_dp(dp_id, value)
                if result:
                    await self.async_request_refresh()
                    return True, "local"
                last_error = "local: device returned failure"
            except Exception as err:
                last_error = f"local: {err}"
                _LOGGER.warning("Local command failed for DP %d: %s", dp_id, err)

        if self.api_available and self.api_client:
            try:
                dp_mapping = await self._get_dp_mapping()
                property_code = dp_mapping.get(dp_id)
                if property_code:
                    commands = [{"code": property_code, "value": value}]
                    result = await self.api_client.send_commands(self.device_id, commands)
                else:
                    result = await self.api_client.send_dp_commands(self.device_id, {str(dp_id): value})
                if result:
                    await self.async_request_refresh()
                    return True, "api"
                last_error = f"api: command returned failure for DP {dp_id}"
                _LOGGER.warning(last_error)
            except Exception as err:
                last_error = f"api: {err}"
                _LOGGER.warning("API command failed for DP %d: %s", dp_id, err)

        if self.smartlife_available and self.smartlife_client:
            # Cloud-spec gate: KKT hoods expose RGB / brightness / scene_data
            # only via the local Tuya protocol. Tuya cloud's function-spec
            # doesn't include those codes, so SmartLife send_commands always
            # fails with error 2008. Don't even try the round-trip — surface
            # a clear "set local IP" message instead. (Confirmed pattern from
            # Issue #5 + Issue #2 + APK reverse engineering. See memory file
            # project_kkt_rgb_local_only.md for the full history.)
            if self._is_dp_local_only(dp_id):
                last_error = self._format_local_only_dp_message(dp_id)
                _LOGGER.warning(
                    "DP %d is local-only on this device — skipping SmartLife (would fail with 2008)",
                    dp_id,
                )
            else:
                success, smartlife_error = await self._async_send_via_smartlife(dp_id, value)
                if success:
                    await self.async_request_refresh()
                    return True, "smartlife"
                last_error = smartlife_error

        _LOGGER.error("All command sending methods failed for DP %d = %s (%s)", dp_id, value, last_error)
        return False, last_error

    def _is_dp_local_only(self, dp_id: int) -> bool:
        """Return True if DP is known to be missing from Tuya cloud's spec.

        Decided by inspecting live ``device.local_strategy`` from the SDK:
        if the DP is not present, the cloud cannot accept commands for it
        and SmartLife send_commands will always return error 2008. Returns
        False (allow cloud attempt) when we can't make the determination —
        e.g. SDK manager not yet initialised.
        """
        if not self.smartlife_client or not hasattr(self.smartlife_client, "get_device_codes"):
            return False
        live_codes = self.smartlife_client.get_device_codes(self.device_id)
        if not live_codes:
            # Cache empty — could be transient (manager still loading).
            # Don't gate; fall through to the normal cloud send.
            return False
        return dp_id not in live_codes

    def _format_local_only_dp_message(self, dp_id: int) -> str:
        """Build a one-line error for a local-only DP that can't be sent via cloud."""
        if self.local_available:
            # Should not happen — if local was available we'd have used it above.
            return f"DP {dp_id} is local-only and the local send already failed"
        return (
            f"DP {dp_id} is local-only on this device — Tuya cloud does not expose "
            f"its code (typical for KKT RGB / brightness / scene_data). "
            f"Set the device's LAN IP under: Settings → Devices & Services → "
            f"KKT Kolbe → device → ⋮ Reconfigure → Connection. Local Key is already "
            f"populated from your SmartLife setup. Find the IP in your router's "
            f"DHCP/client list (e.g. FritzBox → Heimnetz)."
        )

    async def async_send_command(self, dp_id: int, value: Any) -> bool:
        """Send command using available communication method.

        Tries local → API → SmartLife in order. Returns True on first success.
        Backward-compatible wrapper around ``_async_send_command_with_reason``.
        """
        success, _ = await self._async_send_command_with_reason(dp_id, value)
        return success

    async def _async_send_via_smartlife(self, dp_id: int, value: Any) -> tuple[bool, str]:
        """Send a command via SmartLife.

        Builds commands using live ``device.local_strategy[dp].status_code``
        (cloud's ground truth), falling back to the hardcoded mapping in
        ``device_types.py`` if the live spec is unavailable.

        We do NOT auto-refresh the SDK device cache on failure: the SDK's
        ``Manager.update_device_cache()`` clears ``device_map`` before
        re-fetching homes from cloud — if the re-fetch fails (network /
        auth / rate-limit) the cache stays empty and breaks ALL subsequent
        operations including the MQTT push listener. Cache refresh is
        exposed as a manual diagnostic action via the
        ``kkt_kolbe.refresh_smartlife_cache`` service instead.

        On failure, the error context includes which code/DP was attempted,
        what codes the device actually advertises, and a human-readable
        decode of common Tuya error codes — so the user (and us) doesn't
        have to dig through diagnostics to understand a single failure.

        Returns ``(success, error_reason)``.
        """
        live_codes: dict[int, str] = {}
        property_code: str | None = None
        try:
            if hasattr(self.smartlife_client, "get_device_codes"):
                live_codes = self.smartlife_client.get_device_codes(self.device_id)
            property_code = live_codes.get(dp_id)
            if not property_code:
                dp_mapping = await self._get_dp_mapping()
                property_code = dp_mapping.get(dp_id)
                if property_code:
                    _LOGGER.debug(
                        "Falling back to hardcoded code %s for DP %d (live mapping missing)",
                        property_code,
                        dp_id,
                    )
            if property_code:
                commands = [{"code": property_code, "value": value}]
                result = await self.smartlife_client.async_send_commands(self.device_id, commands)
            else:
                result = await self.smartlife_client.async_send_dp_commands(self.device_id, {str(dp_id): value})
            if result:
                return True, "smartlife"
            last_error = f"smartlife: command returned failure for DP {dp_id}"
            _LOGGER.warning(last_error)
            return False, last_error
        except Exception as err:
            last_error = self._format_smartlife_error(err, dp_id, property_code, live_codes)
            _LOGGER.warning("SmartLife command failed for DP %d: %s", dp_id, last_error)
            return False, last_error

    @staticmethod
    def _format_smartlife_error(
        err: Exception, dp_id: int, attempted_code: str | None, live_codes: dict[int, str]
    ) -> str:
        """Format a SmartLife send-failure with all context the user needs.

        Includes:
        - The raw SDK exception
        - What code we tried to send (so the user knows the request)
        - A decode of the Tuya error code (1106, 2008, etc.) since the SDK
          only surfaces the number
        - The codes the device actually advertises in ``local_strategy`` —
          if none of them match what we sent, we point that out

        Goal: a one-line warning that tells the user what to do next, without
        having to download diagnostics and cross-reference codes.
        """
        err_str = str(err)
        parts: list[str] = [f"smartlife: {err_str}"]

        decoded = _decode_tuya_error_code(err_str)
        if decoded:
            parts.append(f"meaning: {decoded}")

        if attempted_code:
            parts.append(f"attempted code='{attempted_code}' for DP {dp_id}")
        else:
            parts.append(f"attempted raw DP {dp_id} (no code mapping found)")

        if live_codes:
            known = sorted(live_codes.values())
            if attempted_code and attempted_code not in known:
                parts.append(
                    f"WARNING: '{attempted_code}' not in device's known codes — device accepts: {', '.join(known)}"
                )
            else:
                parts.append(f"device's known codes: {', '.join(known)}")

        return " | ".join(parts)

    async def _async_try_resync_local_key(self) -> bool:
        """Pull a fresh local_key from SmartLife and apply it to the local device.

        Triggered when the local connection raises KKTAuthenticationError
        (Error 914 across all protocol versions and key variants). Most common
        cause: the device was re-paired in the SmartLife app, rotating the key
        on the cloud side while the integration kept caching the old one.

        Returns:
            True if a new key was retrieved and applied (caller should retry the
            local update). False if no SmartLife client is configured, the
            throttle window is still active, the device wasn't found in the
            cloud, or the cloud key matches what we already have.
        """
        if not self.smartlife_client or not self.local_device or not self.config_entry:
            return False

        now = datetime.now()
        if (
            self._last_key_resync_attempt is not None
            and now - self._last_key_resync_attempt < self._key_resync_min_interval
        ):
            _LOGGER.debug(
                "Skipping local_key resync for device %s: throttle window active (last attempt %s)",
                self.device_id[:8],
                self._last_key_resync_attempt.isoformat(timespec="seconds"),
            )
            return False

        self._last_key_resync_attempt = now

        try:
            sl_device = await self.smartlife_client.async_refresh_device(self.device_id)
        except Exception as err:
            _LOGGER.warning(
                "local_key resync failed for device %s: cloud refresh raised %s: %s",
                self.device_id[:8],
                type(err).__name__,
                err,
            )
            return False

        if sl_device is None:
            _LOGGER.warning(
                "local_key resync: device %s not found in SmartLife device list",
                self.device_id[:8],
            )
            return False

        fresh_key = sl_device.local_key
        if not fresh_key:
            _LOGGER.warning(
                "local_key resync: SmartLife returned empty local_key for device %s",
                self.device_id[:8],
            )
            return False

        if fresh_key == self.local_device.local_key:
            _LOGGER.info(
                "local_key resync: SmartLife key matches stored key for device %s — "
                "Error 914 is not a key-rotation issue (check device state / firmware)",
                self.device_id[:8],
            )
            return False

        _LOGGER.warning(
            "local_key resync: applying rotated key for device %s "
            "(stored length=%d, fresh length=%d)",
            self.device_id[:8],
            len(self.local_device.local_key),
            len(fresh_key),
        )

        # Persist the fresh key in the config entry so it survives restarts.
        new_data = dict(self.config_entry.data)
        new_data["local_key"] = fresh_key
        new_data[CONF_ACCESS_TOKEN] = fresh_key
        # Pick up any IP refresh from the same SmartLife response while we have it.
        fresh_ip = getattr(sl_device, "ip", None)
        if fresh_ip:
            import ipaddress

            try:
                if ipaddress.ip_address(fresh_ip).is_private and fresh_ip != self.local_device.ip_address:
                    new_data[CONF_IP_ADDRESS] = fresh_ip
                    new_data["ip_address"] = fresh_ip
                    self.local_device.ip_address = fresh_ip
                    _LOGGER.info(
                        "local_key resync: IP also refreshed for device %s: %s",
                        self.device_id[:8],
                        fresh_ip,
                    )
            except ValueError:
                pass
        self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)

        # Force a clean reconnect with the new key on the next status call.
        await self.local_device.async_disconnect()
        self.local_device.local_key = fresh_key
        self.local_device._local_key_bytes = None

        return True

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
