"""Sensor platform for KKT Kolbe devices."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor import SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .base_entity import KKTBaseEntity
from .base_entity import KKTZoneBaseEntity
from .bitfield_utils import BITFIELD_CONFIG
from .bitfield_utils import get_zone_value_from_coordinator
from .device_types import get_device_entities

if TYPE_CHECKING:
    from . import KKTKolbeConfigEntry

# Limit parallel updates - 0 means unlimited (coordinator-based entities)
PARALLEL_UPDATES = 0

# Estimated watt per power level for induction cooktops
# Level 0 = 0W, Level 25 = ~2500W per zone (typical for 7kW 5-zone cooktop)
WATTS_PER_LEVEL = 100  # ~100W per level is a reasonable estimate

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KKTKolbeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KKT Kolbe sensor entities."""
    runtime_data = entry.runtime_data
    coordinator = runtime_data.coordinator
    device_type = runtime_data.device_type
    product_name = runtime_data.product_name

    # Check if advanced entities are enabled (default: True)
    enable_advanced = entry.options.get("enable_advanced_entities", True)

    # Prefer device_type (KNOWN_DEVICES key) over product_name (Tuya product ID)
    lookup_key = device_type if device_type not in ("auto", None, "") else product_name

    entities = []
    sensor_configs = get_device_entities(lookup_key, "sensor")

    for config in sensor_configs:
        # Skip advanced entities if not enabled
        if config.get("advanced", False) and not enable_advanced:
            continue
        sensor_type = config.get("sensor_type", "standard")

        if sensor_type == "calculated_power":
            # Calculated power sensor (estimates watts from zone levels)
            entities.append(KKTKolbeCalculatedPowerSensor(coordinator, entry, config))
        elif sensor_type == "total_level":
            # Total power level sensor (sum of all zones)
            entities.append(KKTKolbeTotalLevelSensor(coordinator, entry, config))
        elif sensor_type == "active_zones":
            # Active zones counter
            entities.append(KKTKolbeActiveZonesSensor(coordinator, entry, config))
        elif "zone" in config:
            # Zone-specific sensor
            entities.append(KKTKolbeZoneSensor(coordinator, entry, config))
        else:
            # Regular sensor
            entities.append(KKTKolbeSensor(coordinator, entry, config))

    # Add connection mode sensor for HybridCoordinator
    from .hybrid_coordinator import KKTKolbeHybridCoordinator
    if isinstance(coordinator, KKTKolbeHybridCoordinator):
        entities.append(KKTKolbeConnectionSensor(coordinator, entry))

    # Add SmartLife info sensor if extended info is available
    from .const import DOMAIN
    entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    smartlife_extended_info = entry_data.get("smartlife_extended_info", {})
    if smartlife_extended_info and smartlife_extended_info.get("uuid"):
        entities.append(
            KKTKolbeSmartLifeInfoSensor(coordinator, entry, smartlife_extended_info)
        )
        _LOGGER.info(
            "Added SmartLife info sensor for device %s (UUID: %s)",
            entry.data.get("device_id", "unknown")[:8],
            smartlife_extended_info.get("uuid"),
        )

    if entities:
        async_add_entities(entities)


class KKTKolbeSensor(KKTBaseEntity, SensorEntity):
    """Representation of a KKT Kolbe sensor."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict[str, Any]],
        entry: ConfigEntry,
        config: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, config, "sensor")
        self._cached_value: int | float | None = None

        # Initialize state from coordinator data
        self._update_cached_state()

        # Set sensor-specific attributes
        self._attr_state_class = config.get("state_class")
        self._attr_native_unit_of_measurement = config.get("unit_of_measurement")
        self._attr_icon = self._get_icon()

        # Set display precision based on sensor type (HA 2025.1+)
        self._attr_suggested_display_precision = self._get_display_precision()

        # Note: entity_category is now handled in base_entity.py from device_types.py config

    def _get_display_precision(self) -> int:
        """Determine display precision based on sensor type."""
        name_lower = self._name.lower()
        device_class = self._attr_device_class

        # Temperature sensors: 1 decimal
        if device_class == SensorDeviceClass.TEMPERATURE:
            return 1
        # Timer, filter, level: whole numbers
        if any(kw in name_lower for kw in ["timer", "filter", "level", "hours", "days"]):
            return 0
        # Default: no decimals
        return 0

    def _get_icon(self) -> str:
        """Get appropriate icon for the sensor."""
        name_lower = self._name.lower()
        device_class = self._attr_device_class

        if device_class == SensorDeviceClass.TEMPERATURE:
            return "mdi:thermometer"
        elif "timer" in name_lower:
            return "mdi:timer-outline"
        elif "filter" in name_lower:
            return "mdi:air-filter"
        elif "status" in name_lower:
            return "mdi:information-outline"
        elif "error" in name_lower:
            return "mdi:alert-circle-outline"

        return "mdi:gauge"

    def _update_cached_state(self) -> None:
        """Update the cached state from coordinator data."""
        value = self._get_data_point_value()
        if value is None:
            self._cached_value = None
            return

        # Convert temperature values if needed
        if self._attr_device_class == SensorDeviceClass.TEMPERATURE:
            if isinstance(value, (int, float)):
                # Assuming device reports in Celsius
                self._cached_value = value
            else:
                self._cached_value = None
        else:
            self._cached_value = value

    @property
    def native_value(self) -> Any | None:
        """Return the state of the sensor."""
        return self._cached_value


class KKTKolbeZoneSensor(KKTZoneBaseEntity, SensorEntity):
    """Zone-specific sensor for KKT Kolbe devices."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict[str, Any]],
        entry: ConfigEntry,
        config: dict[str, Any],
    ) -> None:
        """Initialize the zone sensor."""
        super().__init__(coordinator, entry, config, "sensor")

        # Set sensor-specific attributes
        self._attr_state_class = config.get("state_class")
        self._attr_native_unit_of_measurement = config.get("unit_of_measurement")
        self._attr_icon = self._get_icon()
        self._cached_value = None

        # Zone sensors are typically integers (HA 2025.1+)
        self._attr_suggested_display_precision = 0

        # Note: entity_category is now handled in base_entity.py from device_types.py config
        # No need to check DIAGNOSTIC_DPS here

        # Initialize state from coordinator data
        self._update_cached_state()

    def _get_icon(self) -> str:
        """Get appropriate icon for the zone sensor."""
        name_lower = self._name.lower()

        if "temperature" in name_lower:
            return "mdi:thermometer"
        elif "timer" in name_lower:
            return "mdi:timer"
        elif "power" in name_lower:
            return "mdi:lightning-bolt"
        elif "level" in name_lower:
            return "mdi:gauge"

        return "mdi:circle-slice-8"

    def _update_cached_state(self) -> None:
        """Update the cached state from coordinator data."""
        # Check if this DP uses bitfield encoding
        if self._zone is not None and self._dp in BITFIELD_CONFIG and BITFIELD_CONFIG[self._dp]["type"] == "value":
            # Use bitfield utilities for Base64-encoded RAW data
            value = get_zone_value_from_coordinator(self.coordinator, self._dp, self._zone)
            self._cached_value = value
            return

        # Fallback to legacy integer bitfield handling
        raw_value = self._get_data_point_value()
        if raw_value is None:
            self._cached_value = None
            return

        # For zone-specific values, extract from bitfield if needed
        if self._zone is not None and isinstance(raw_value, int) and raw_value > 255:
            # Likely a bitfield, extract zone-specific value
            # This depends on the specific data point structure
            zone_offset = (self._zone - 1) * 8  # Assuming 8 bits per zone
            zone_mask = 0xFF << zone_offset
            zone_value = (raw_value & zone_mask) >> zone_offset
            self._cached_value = zone_value
        else:
            self._cached_value = raw_value

    @property
    def native_value(self) -> Any | None:
        """Return the state of the zone sensor."""
        return self._cached_value


class KKTKolbeCalculatedPowerSensor(KKTBaseEntity, SensorEntity):
    """Calculated power sensor that estimates watts from zone power levels."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict[str, Any]],
        entry: ConfigEntry,
        config: dict[str, Any],
    ) -> None:
        """Initialize the calculated power sensor."""
        super().__init__(coordinator, entry, config, "sensor")
        self._zones_dp = config.get("zones_dp", 162)  # DP for zone levels
        self._num_zones = config.get("num_zones", 5)
        self._watts_per_level = config.get("watts_per_level", WATTS_PER_LEVEL)
        self._cached_value: int | None = None

        # Set sensor attributes
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_icon = "mdi:lightning-bolt"
        self._attr_suggested_display_precision = 0  # Whole watts (HA 2025.1+)

        self._update_cached_state()

    def _update_cached_state(self) -> None:
        """Calculate estimated power from all zone levels."""
        total_power = 0

        for zone in range(1, self._num_zones + 1):
            # Get zone level using bitfield utilities
            level = get_zone_value_from_coordinator(
                self.coordinator, self._zones_dp, zone
            )
            if level is not None and isinstance(level, (int, float)):
                # Estimate watts: level * watts_per_level
                total_power += int(level) * self._watts_per_level

        self._cached_value = total_power

    @property
    def native_value(self) -> int | None:
        """Return the estimated power in watts."""
        return self._cached_value


class KKTKolbeTotalLevelSensor(KKTBaseEntity, SensorEntity):
    """Sensor that shows the sum of all zone power levels."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict[str, Any]],
        entry: ConfigEntry,
        config: dict[str, Any],
    ) -> None:
        """Initialize the total level sensor."""
        super().__init__(coordinator, entry, config, "sensor")
        self._zones_dp = config.get("zones_dp", 162)
        self._num_zones = config.get("num_zones", 5)
        self._cached_value: int | None = None

        # Set sensor attributes
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:gauge"
        self._attr_suggested_display_precision = 0  # Whole numbers (HA 2025.1+)

        self._update_cached_state()

    def _update_cached_state(self) -> None:
        """Calculate total power level from all zones."""
        total_level = 0

        for zone in range(1, self._num_zones + 1):
            level = get_zone_value_from_coordinator(
                self.coordinator, self._zones_dp, zone
            )
            if level is not None and isinstance(level, (int, float)):
                total_level += int(level)

        self._cached_value = total_level

    @property
    def native_value(self) -> int | None:
        """Return the total power level."""
        return self._cached_value


class KKTKolbeActiveZonesSensor(KKTBaseEntity, SensorEntity):
    """Sensor that counts active cooking zones."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict[str, Any]],
        entry: ConfigEntry,
        config: dict[str, Any],
    ) -> None:
        """Initialize the active zones sensor."""
        super().__init__(coordinator, entry, config, "sensor")
        self._zones_dp = config.get("zones_dp", 162)
        self._num_zones = config.get("num_zones", 5)
        self._cached_value: int | None = None

        # Set sensor attributes
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:stove"
        self._attr_suggested_display_precision = 0  # Whole numbers (HA 2025.1+)

        self._update_cached_state()

    def _update_cached_state(self) -> None:
        """Count zones with power level > 0."""
        active_count = 0

        for zone in range(1, self._num_zones + 1):
            level = get_zone_value_from_coordinator(
                self.coordinator, self._zones_dp, zone
            )
            if level is not None and isinstance(level, (int, float)) and int(level) > 0:
                active_count += 1

        self._cached_value = active_count

    @property
    def native_value(self) -> int | None:
        """Return the number of active zones."""
        return self._cached_value


class KKTKolbeConnectionSensor(SensorEntity):
    """Sensor that shows the current connection mode (local/api/smartlife)."""

    # Attributes that change frequently - don't record in database
    _unrecorded_attributes = frozenset({
        "last_update_timestamp",
        "token_expires_in_seconds",
        "local_errors",
        "api_errors",
    })

    def __init__(
        self,
        coordinator: Any,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the connection sensor."""
        from homeassistant.helpers.entity import EntityCategory

        self.coordinator = coordinator
        self._entry = entry
        self._attr_has_entity_name = True
        self._attr_translation_key = "connection_mode"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_icon = "mdi:connection"

        # Unique ID based on entry
        device_id = entry.data.get("device_id", entry.entry_id)
        self._attr_unique_id = f"{entry.entry_id}_connection_mode"

        # Device info
        from .const import DOMAIN
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device_id)},
        }

    @property
    def native_value(self) -> str | None:
        """Return the current connection mode."""
        if hasattr(self.coordinator, "current_mode"):
            mode = self.coordinator.current_mode
            # Translate to user-friendly names
            mode_names = {
                "local": "Local (LAN)",
                "api": "Cloud (IoT API)",
                "smartlife": "Cloud (SmartLife)",
            }
            return mode_names.get(mode, mode)
        return "Unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional connection details."""
        attrs = {}

        if hasattr(self.coordinator, "local_available"):
            attrs["local_available"] = self.coordinator.local_available
        if hasattr(self.coordinator, "api_available"):
            attrs["api_available"] = self.coordinator.api_available
        if hasattr(self.coordinator, "smartlife_available"):
            attrs["smartlife_available"] = self.coordinator.smartlife_available
        if hasattr(self.coordinator, "local_consecutive_errors"):
            attrs["local_errors"] = self.coordinator.local_consecutive_errors
        if hasattr(self.coordinator, "api_consecutive_errors"):
            attrs["api_errors"] = self.coordinator.api_consecutive_errors
        if hasattr(self.coordinator, "prefer_local"):
            attrs["prefer_local"] = self.coordinator.prefer_local

        # SmartLife specific attributes
        if hasattr(self.coordinator, "data") and self.coordinator.data:
            data = self.coordinator.data
            # Show raw SmartLife property codes if available
            if "raw_smartlife_status" in data:
                raw_status = data["raw_smartlife_status"]
                if isinstance(raw_status, list):
                    codes = [item.get("code") for item in raw_status if isinstance(item, dict)]
                    attrs["smartlife_property_codes"] = codes
                    attrs["smartlife_properties_count"] = len(codes)
            # Show source of last update
            if "source" in data:
                attrs["last_update_source"] = data["source"]
            # Show timestamp
            if "timestamp" in data:
                attrs["last_update_timestamp"] = data["timestamp"]

        # Token status from SmartLife client
        if hasattr(self.coordinator, "smartlife_client") and self.coordinator.smartlife_client:
            client = self.coordinator.smartlife_client
            if hasattr(client, "is_authenticated"):
                attrs["smartlife_authenticated"] = client.is_authenticated
            if hasattr(client, "_token_info") and client._token_info:
                token_info = client._token_info
                if "expire_time" in token_info:
                    import time
                    expire_time = token_info["expire_time"]
                    now = int(time.time())
                    attrs["token_expires_in_seconds"] = max(0, expire_time - now)
                    attrs["token_valid"] = expire_time > now

        # Tuya IoT Platform API specific attributes
        if hasattr(self.coordinator, "api_client") and self.coordinator.api_client:
            api_client = self.coordinator.api_client
            attrs["api_connected"] = True
            # Show raw API status if available
            if hasattr(self.coordinator, "data") and self.coordinator.data:
                if "raw_api_status" in self.coordinator.data:
                    raw_api = self.coordinator.data["raw_api_status"]
                    if isinstance(raw_api, list):
                        api_codes = [item.get("code") for item in raw_api if isinstance(item, dict)]
                        attrs["api_property_codes"] = api_codes
                        attrs["api_properties_count"] = len(api_codes)
            # API endpoint info
            if hasattr(api_client, "endpoint"):
                attrs["api_endpoint"] = api_client.endpoint
            if hasattr(api_client, "client_id"):
                # Only show first 8 chars for security
                attrs["api_client_id"] = api_client.client_id[:8] + "..." if api_client.client_id else None

        return attrs

    @property
    def available(self) -> bool:
        """Return True if entity is available.

        The connection sensor should be more resilient than regular entities.
        It shows connection status info which is still useful even if the
        last coordinator update failed. Only mark unavailable if the
        coordinator has no data at all.
        """
        # More resilient: available if coordinator exists and has any data
        # Even if last_update_success is False, we can still show connection status
        if self.coordinator is None:
            return False
        # Available if we have any data or if we can read connection mode
        if hasattr(self.coordinator, "current_mode") and self.coordinator.current_mode:
            return True
        if hasattr(self.coordinator, "data") and self.coordinator.data:
            return True
        return self.coordinator.last_update_success


class KKTKolbeSmartLifeInfoSensor(SensorEntity):
    """Sensor that exposes extended SmartLife device information.

    Shows device info like UUID, creation time, active time, update time,
    timezone, and icon URL that were retrieved from the SmartLife API.
    """

    # These attributes change very rarely - avoid recording every update
    _unrecorded_attributes = frozenset({
        "create_time",
        "active_time",
        "update_time",
        "time_zone",
        "icon_url",
    })

    def __init__(
        self,
        coordinator: Any,
        entry: ConfigEntry,
        extended_info: dict[str, Any],
    ) -> None:
        """Initialize the SmartLife info sensor."""
        from homeassistant.helpers.entity import EntityCategory

        self.coordinator = coordinator
        self._entry = entry
        self._extended_info = extended_info
        self._attr_has_entity_name = True
        self._attr_translation_key = "smartlife_device_info"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_icon = "mdi:cloud-check-outline"

        # Unique ID based on entry
        device_id = entry.data.get("device_id", entry.entry_id)
        self._device_id = device_id
        self._attr_unique_id = f"{entry.entry_id}_smartlife_info"

        # Device info
        from .const import DOMAIN
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device_id)},
        }

    @property
    def entity_picture(self) -> str | None:
        """Return the device icon as entity picture.

        Uses the icon downloaded from Tuya Cloud, stored locally
        in www/kkt_kolbe/icons/{device_id}.png
        """
        # Only return picture if we have an icon URL (means download was attempted)
        if self._extended_info.get("icon"):
            return f"/local/kkt_kolbe/icons/{self._device_id}.png"
        return None

    @property
    def native_value(self) -> str | None:
        """Return the device UUID as the main state."""
        return self._extended_info.get("uuid")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extended SmartLife device info as attributes."""
        attrs = {}

        # Creation time (when device was added to SmartLife)
        create_time = self._extended_info.get("create_time")
        if create_time:
            # Convert Unix timestamp to ISO datetime
            try:
                from datetime import datetime
                from datetime import timezone
                dt = datetime.fromtimestamp(create_time, tz=timezone.utc)
                attrs["create_time"] = dt.isoformat()
            except (ValueError, TypeError):
                attrs["create_time"] = create_time

        # Active time (last time device was active)
        active_time = self._extended_info.get("active_time")
        if active_time:
            try:
                from datetime import datetime
                from datetime import timezone
                dt = datetime.fromtimestamp(active_time, tz=timezone.utc)
                attrs["active_time"] = dt.isoformat()
            except (ValueError, TypeError):
                attrs["active_time"] = active_time

        # Update time (last status update)
        update_time = self._extended_info.get("update_time")
        if update_time:
            try:
                from datetime import datetime
                from datetime import timezone
                dt = datetime.fromtimestamp(update_time, tz=timezone.utc)
                attrs["update_time"] = dt.isoformat()
            except (ValueError, TypeError):
                attrs["update_time"] = update_time

        # Time zone
        time_zone = self._extended_info.get("time_zone")
        if time_zone:
            attrs["time_zone"] = time_zone

        # Icon URL
        icon = self._extended_info.get("icon")
        if icon:
            attrs["icon_url"] = icon

        return attrs

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # Always available if extended info was retrieved
        return bool(self._extended_info)
