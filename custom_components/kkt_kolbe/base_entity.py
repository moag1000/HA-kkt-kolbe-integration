"""Base entity for KKT Kolbe devices.

Based on patterns from https://github.com/ludeeus/integration_blueprint
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import DOMAIN
from .data import KKTCoordinator
from .pending_writes import PendingWrites
from .pending_writes import effective_dps
from .pending_writes import pending_writes_for

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)


def entity_unique_id(entry_id: str, platform: str, dp: int, name: str, zone: int | None = None) -> str:
    """Return the unique_id of a device-profile entity.

    Format: ``{entry_id}_{platform}_dp{dp}[_zone{zone}]_{name}``. The DP keeps
    entities with the same name apart; the name is the stable English profile
    name, not the translated entity name. Actions use this to find an entity
    of a device (e.g. its power switch) without guessing from entity_ids.
    """
    zone_part = f"_zone{zone}" if zone is not None else ""
    return f"{entry_id}_{platform}_dp{dp}{zone_part}_{name.lower().replace(' ', '_')}"


class KKTBaseEntity(CoordinatorEntity["KKTCoordinator"]):
    """Base entity for all KKT Kolbe entities."""

    _attr_has_entity_name = True

    # Exclude non-historical attributes from database recording (HA 2024.6+)
    # This reduces database size by not recording frequently changing diagnostic data
    _unrecorded_attributes = frozenset(
        {
            "raw_dp_data",
            "last_update",
            "data_point",
            "device_id",
            "zone",
            "connection_status",
        }
    )

    def __init__(
        self,
        coordinator: KKTCoordinator,
        entry: ConfigEntry,
        config: dict[str, Any],
        platform: str,
        zone: int | None = None,
    ) -> None:
        """Initialize the base entity."""
        super().__init__(coordinator)

        self._entry = entry
        self._config = config
        self._platform = platform
        self._zone = zone

        # Extract common configuration
        self._dp = config["dp"]
        self._name = config["name"]

        # Last known value per data point, to prevent "unknown" values when a
        # DP is temporarily missing. Keyed by DP: an entity reads more than its
        # own DP (fan and light also read the hood power DP 1), and a value of
        # one DP must never stand in for another.
        self._dp_cache: dict[int, Any] = {}
        self._last_update_time: datetime | None = None

        # Device info cache
        self._device_info_cached: DeviceInfo | None = None

        # Set up entity attributes
        self._setup_entity_attributes()

        # Device info will be built as property when needed (self.hass not available in __init__)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this entity."""
        # Don't cache if hass is not available yet - rebuild once it is
        if not self.hass:
            return self._build_device_info()

        # Cache device info once hass is available
        if not hasattr(self, "_device_info_cached") or self._device_info_cached is None:
            self._device_info_cached = self._build_device_info()
        return self._device_info_cached

    def _setup_entity_attributes(self) -> None:
        """Set up common entity attributes."""
        # Generate unique ID - ALWAYS include DP to prevent collisions
        self._attr_unique_id = entity_unique_id(self._entry.entry_id, self._platform, self._dp, self._name, self._zone)

        # Set translation key if provided (Gold Quality requirement)
        translation_key = self._config.get("translation_key")
        if translation_key:
            self._attr_translation_key = translation_key
            # When using translation_key, don't set name (HA uses translation)
        else:
            # Derive a translation key from the entity name so localized
            # names are used even when no explicit translation_key is given.
            self._attr_translation_key = slugify(self._name)

        # Set device class if provided
        self._attr_device_class = self._config.get("device_class")

        # Set entity category if provided
        entity_category = self._config.get("entity_category")
        if entity_category:
            from homeassistant.const import EntityCategory

            if hasattr(EntityCategory, entity_category.upper()):
                self._attr_entity_category = getattr(EntityCategory, entity_category.upper())

        # Disable advanced/diagnostic entities by default (Gold Tier requirement)
        if self._config.get("advanced", False) or entity_category == "diagnostic":
            self._attr_entity_registry_enabled_default = False

    def _runtime_attr(self, name: str) -> str:
        """Return a string attribute from entry.runtime_data ("" if unavailable)."""
        value = getattr(getattr(self._entry, "runtime_data", None), name, None)
        return value if isinstance(value, str) else ""

    def _build_device_info(self) -> DeviceInfo:
        """Build standardized device info using KNOWN_DEVICES."""
        from .device_types import KNOWN_DEVICES

        # Device type resolved during setup lives on entry.runtime_data
        device_type_key = self._runtime_attr("device_type") or "auto"
        device_id = self._entry.data.get("device_id", "unknown")

        known = KNOWN_DEVICES.get(device_type_key)
        if known is not None:
            device_name = str(known.get("name", "KKT Kolbe Device"))
            # Human readable model ("HERMES & STYLE Hood"); the Tuya model code
            # ("e1k6i0zo") goes to model_id, not to model or hw_version.
            model = device_name
            model_id = known.get("model_id")
        else:
            device_name = "KKT Kolbe Device"
            model = None
            model_id = None

        info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device_name,
            manufacturer="KKT Kolbe",
            sw_version=self._get_software_version(),
        )
        if model:
            info["model"] = model
        if model_id:
            info["model_id"] = str(model_id)
        return info

    def _get_software_version(self) -> str:
        """Get software version from device data."""
        # Try to get protocol version from device via coordinator
        if hasattr(self.coordinator, "device") and self.coordinator.device:
            device = self.coordinator.device
            # Check for detected protocol version
            version = getattr(device, "version", None)
            if version and version != "auto":
                return f"Tuya Protocol {version}"
            # Check connection stats for detected version
            if hasattr(device, "_connection_stats"):
                detected = device._connection_stats.get("protocol_version_detected")
                if detected:
                    return f"Tuya Protocol {detected}"

        # Try to get from entry data (may be set during discovery)
        version = self._entry.data.get("version")
        if version and version != "auto":
            return f"Tuya Protocol {version}"

        # Use integration version as fallback
        from .const import VERSION

        return f"v{VERSION}"

    @property
    def available(self) -> bool:
        """Return if entity is available.

        Entities are available if:
        1. We have current data from coordinator, OR
        2. We have a cached value from previous successful update, OR
        3. We're in initial startup phase (coordinator hasn't had consecutive failures)

        Entities only become unavailable after persistent connection issues.
        """
        # Check coordinator device state if available (KKTKolbeUpdateCoordinator)
        if hasattr(self.coordinator, "is_device_available"):
            # Use coordinator's device state which tracks consecutive failures
            device_available = self.coordinator.is_device_available

            # If device is online, we're always available
            if device_available:
                return True

            # Circuit breaker tripped (UNREACHABLE): the device has failed
            # persistently and retries are suspended. Do NOT keep masking this
            # with a stale cached value — surface it as unavailable so the user
            # (and automations) see the real state instead of a frozen reading.
            device_state = getattr(self.coordinator, "device_state", None)
            if device_state is not None and device_state.value == "unreachable":
                return False

            # If device is offline but we have cached data, still report as available
            # This prevents flapping during temporary connection issues
            if self._dp_cache.get(self._dp) is not None:
                return True

            # If device is offline and no cached data, check if we ever had data
            if self.coordinator.data is not None and len(self.coordinator.data) > 0:
                return True

        # Fallback for other coordinators: check if we have any data
        has_data = self.coordinator.data is not None and len(self.coordinator.data) > 0
        has_cached_value = self._dp_cache.get(self._dp) is not None

        # More lenient: available if we have data OR cache OR no failures yet
        is_available = has_data or has_cached_value or self.coordinator.last_update_success

        if not is_available:
            _LOGGER.debug(
                f"Entity {self._attr_unique_id} unavailable: "
                f"last_update_success={self.coordinator.last_update_success}, "
                f"has_data={has_data}, has_cached_value={has_cached_value}, "
                f"data_keys={list(self.coordinator.data.keys()) if self.coordinator.data else 'None'}"
            )

        return is_available

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Debug logging for coordinator updates
        if _LOGGER.isEnabledFor(logging.DEBUG):
            data_keys = list(self.coordinator.data.keys()) if self.coordinator.data else []
            _LOGGER.debug(
                f"Coordinator update for {self._attr_unique_id}: "
                f"DP {self._dp}, Zone: {self._zone}, "
                f"Available DPs: {data_keys}"
            )

        # Pending writes are released centrally (PendingWrites.apply) as soon
        # as the device reports the written value, whether by push or by poll.
        # Update cached state from coordinator data
        self._update_cached_state()
        self.async_write_ha_state()

    def _update_cached_state(self) -> None:
        """Update the cached state from coordinator data."""
        # This method should be overridden by specific entity types

    @property
    def _pending_writes(self) -> PendingWrites:
        """Unconfirmed writes of this device (shared by all its entities)."""
        return pending_writes_for(self.coordinator)

    def _is_optimistic_active(self) -> bool:
        """Return True while a write to this entity's DP awaits confirmation."""
        return self._pending_writes.get(self._dp) is not None

    @property
    def _optimistic_value(self) -> Any:
        """Value of the unconfirmed write to this entity's DP, if any."""
        write = self._pending_writes.get(self._dp)
        return write.value if write is not None else None

    def _effective_dps(self) -> dict[Any, Any]:
        """Reported DPs with the device's unconfirmed writes overlaid."""
        return effective_dps(self.coordinator)

    def _raw_dp_value(self, dp: int) -> Any:
        """Return the raw (not zone-decoded) effective value of a DP, or None."""
        dps_data = self._effective_dps()
        value = dps_data.get(str(dp))
        return dps_data.get(dp) if value is None else value

    def _get_data_point_value(self, dp: int | None = None) -> Any:
        """Get value for a specific data point, with zone support and state caching."""
        data_point = dp if dp is not None else self._dp

        # If this entity has a zone, use zone-aware data point extraction
        if self._zone is not None:
            return self._get_zone_data_point_value_cached(data_point, self._zone)

        if not self.coordinator.data:
            _LOGGER.debug(f"Entity {self._attr_unique_id}: No coordinator data available, using cached value")
            return self._dp_cache.get(data_point)

        value = self._raw_dp_value(data_point)

        if value is None:
            # DP not available in current update - use its cached value instead of None
            _LOGGER.debug(
                f"Entity {self._attr_unique_id}: DP {data_point} not in current update. "
                f"Using cached value: {self._dp_cache.get(data_point)}"
            )
            return self._dp_cache.get(data_point)

        self._dp_cache[data_point] = value
        self._last_update_time = datetime.now()
        _LOGGER.debug(f"Entity {self._attr_unique_id}: DP {data_point} = {value} (type: {type(value)}) - cached")
        return value

    def _get_zone_data_point_value_cached(self, dp: int, zone: int | None = None) -> Any:
        """Get value for a zone-specific data point with bitfield extraction and caching."""
        zone_number = zone if zone is not None else self._zone
        if zone_number is None or not self.coordinator.data:
            return self._dp_cache.get(dp)

        value = self._decode_zone_value(self._raw_dp_value(dp), dp, zone_number)
        if value is None:
            # DP not reported (or undecodable) - keep the last known value
            return self._dp_cache.get(dp)

        self._dp_cache[dp] = value
        self._last_update_time = datetime.now()
        return value

    def _get_zone_data_point_value(self, dp: int, zone: int | None = None) -> Any:
        """Get value for a zone-specific data point with bitfield extraction."""
        raw_value = self._raw_dp_value(dp)
        zone_number = zone if zone is not None else self._zone
        if raw_value is None or zone_number is None:
            return raw_value
        return self._decode_zone_value(raw_value, dp, zone_number)

    def _decode_zone_value(self, raw_value: Any, dp: int, zone_number: int) -> Any:
        """Extract one zone's value from a raw zone bitfield DP (None if impossible)."""
        if raw_value is None:
            return None

        # Use bitfield_utils for Base64 RAW data extraction
        if isinstance(raw_value, str):
            from .bitfield_utils import extract_zone_value_from_bitfield

            try:
                return extract_zone_value_from_bitfield(raw_value, zone_number)
            except Exception as e:
                _LOGGER.error(f"Failed to extract zone {zone_number} from DP {dp}: {e}")
                return None

        # Integer bitfield: one bit per zone
        if isinstance(raw_value, int):
            return bool(raw_value & (1 << (zone_number - 1)))

        # Byte arrays: one bit per zone
        if isinstance(raw_value, (bytes, bytearray)):
            byte_index = (zone_number - 1) // 8
            bit_index = (zone_number - 1) % 8
            if byte_index < len(raw_value):
                return bool(raw_value[byte_index] & (1 << bit_index))

        return None

    async def _async_set_data_point(self, dp: int, value: Any) -> None:
        """Write a data point and show it at once in every entity of the device.

        The write is recorded as pending on the coordinator before it is sent,
        so this entity and all others deriving from the DP (power switch, fan
        and light all read DP 1) repaint immediately and a stale poll cannot
        snap them back (Issue #6). If the write fails, the pending entry is
        rolled back and the entities show the reported state again.
        """
        pending = self._pending_writes
        previous = pending.set(dp, value)
        self._async_publish_device_state()
        try:
            await self.coordinator.async_set_data_point(dp, value)
            _LOGGER.debug("Set data point %d to %s for %s", dp, value, self._attr_unique_id)
        except Exception as exc:
            pending.restore(dp, previous)
            self._async_publish_device_state()
            _LOGGER.error("Failed to set data point %d to %s for %s: %s", dp, value, self._attr_unique_id, exc)
            raise

    @callback
    def _async_publish_device_state(self) -> None:
        """Re-derive this entity and every other entity of the device."""
        self._update_cached_state()
        if not self.hass:
            return
        self.async_write_ha_state()
        update_listeners = getattr(self.coordinator, "async_update_listeners", None)
        if callable(update_listeners):
            update_listeners()

    async def _async_suppress_fan_auto_start(self) -> None:
        """Suppress fan auto-start after hood power-on.

        When a hood is freshly powered on, the firmware automatically starts
        the fan. This method sends a fan-off command to prevent that behavior
        when the user only wants the light or power switch.

        Active by default for hood devices. Can be disabled via the
        'disable_fan_auto_start' option (set to False to disable).
        """
        if not self._entry.options.get("disable_fan_auto_start", True):
            return

        # Lazy imports (existing pattern from _build_device_info)
        from .const import CATEGORY_HOOD
        from .device_types import KNOWN_DEVICES
        from .device_types import get_device_entity_config

        # Same lookup the platforms use: the device type resolved during setup
        # (runtime_data) wins over the raw entry data, which may still say "auto".
        device_type = self._runtime_attr("device_type") or self._entry.data.get("device_type", "")
        product_name = self._runtime_attr("product_name") or self._entry.data.get("product_name", "")
        lookup_key = device_type if device_type not in ("auto", None, "") else product_name

        # Verify this is a hood device
        device_info = KNOWN_DEVICES.get(lookup_key)
        if not device_info or device_info.get("category") != CATEGORY_HOOD:
            return

        # Get fan entity config to determine the correct DP and value type
        fan_config = get_device_entity_config(lookup_key, "fan")
        if not fan_config:
            return

        fan_dp = fan_config.get("dp")
        if fan_dp is None:
            return

        # Send fan-off: enum mode uses "off", numeric mode uses 0
        off_value: int | str = 0 if fan_config.get("numeric", False) else "off"

        _LOGGER.info("Suppressing fan auto-start: sending DP %d = %s for %s", fan_dp, off_value, self._attr_unique_id)
        await self._async_set_data_point(fan_dp, off_value)

    def _log_entity_state(self, action: str, additional_info: str = "") -> None:
        """Log entity state changes for debugging."""
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(
                "%s: %s %s (DP: %d, Zone: %s) %s",
                action,
                self._platform,
                self._name,
                self._dp,
                self._zone if self._zone else "N/A",
                additional_info,
            )


class KKTZoneBaseEntity(KKTBaseEntity):
    """Base entity for zone-specific KKT Kolbe entities."""

    def __init__(
        self,
        coordinator: KKTCoordinator,
        entry: ConfigEntry,
        config: dict[str, Any],
        platform: str,
    ) -> None:
        """Initialize the zone base entity."""
        zone = config.get("zone")
        if zone is None:
            raise ValueError("Zone configuration missing for zone entity")

        super().__init__(coordinator, entry, config, platform, zone)

        # Zone entities are typically diagnostic
        from homeassistant.const import EntityCategory

        if not hasattr(self, "_attr_entity_category"):
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            "zone": self._zone,
            "data_point": self._dp,
            "device_id": self._entry.data.get("device_id", "unknown")[:8],
        }
