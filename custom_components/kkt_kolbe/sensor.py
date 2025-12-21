"""Sensor platform for KKT Kolbe devices."""
from __future__ import annotations

import logging
from typing import Any, Union

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature, UnitOfPower
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .base_entity import KKTBaseEntity, KKTZoneBaseEntity
from .const import DOMAIN
from .device_types import get_device_entities
from .bitfield_utils import get_zone_value_from_coordinator, BITFIELD_CONFIG

# Estimated watt per power level for induction cooktops
# Level 0 = 0W, Level 25 = ~2500W per zone (typical for 7kW 5-zone cooktop)
WATTS_PER_LEVEL = 100  # ~100W per level is a reasonable estimate

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KKT Kolbe sensor entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    device_type = hass.data[DOMAIN][entry.entry_id].get("device_type", "auto")
    product_name = hass.data[DOMAIN][entry.entry_id].get("product_name", "unknown")

    # Prefer device_type (KNOWN_DEVICES key) over product_name (Tuya product ID)
    lookup_key = device_type if device_type not in ("auto", None, "") else product_name

    entities = []
    sensor_configs = get_device_entities(lookup_key, "sensor")

    for config in sensor_configs:
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
        self._cached_value = None

        # Initialize state from coordinator data
        self._update_cached_state()

        # Set sensor-specific attributes
        self._attr_state_class = config.get("state_class")
        self._attr_native_unit_of_measurement = config.get("unit_of_measurement")
        self._attr_icon = self._get_icon()

        # Note: entity_category is now handled in base_entity.py from device_types.py config

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
        if self._dp in BITFIELD_CONFIG and BITFIELD_CONFIG[self._dp]["type"] == "value":
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
        if isinstance(raw_value, int) and raw_value > 255:
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
        self._cached_value = None

        # Set sensor attributes
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_icon = "mdi:lightning-bolt"

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
        self._cached_value = None

        # Set sensor attributes
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:gauge"

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
        self._cached_value = None

        # Set sensor attributes
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:stove"

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