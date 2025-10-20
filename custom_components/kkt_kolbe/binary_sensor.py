"""Binary Sensor platform for KKT Kolbe devices."""
import logging
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base_entity import KKTBaseEntity, KKTZoneBaseEntity
from .const import DOMAIN
from .device_types import get_device_entities
from .bitfield_utils import get_zone_value_from_coordinator, BITFIELD_CONFIG

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KKT Kolbe binary sensor entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    product_name = hass.data[DOMAIN][entry.entry_id].get("product_name", "unknown")

    # Get binary sensor configurations for this device
    entity_configs = get_device_entities(product_name, "binary_sensor")

    if entity_configs:
        entities = []
        for config in entity_configs:
            if "zone" in config:
                entities.append(KKTKolbeZoneBinarySensor(coordinator, entry, config))
            else:
                entities.append(KKTKolbeBinarySensor(coordinator, entry, config))

        if entities:
            async_add_entities(entities)


class KKTKolbeBinarySensor(KKTBaseEntity, BinarySensorEntity):
    """Binary sensor for KKT Kolbe devices."""

    def __init__(self, coordinator, entry: ConfigEntry, config: dict):
        """Initialize the binary sensor."""
        super().__init__(coordinator, entry, config, "binary_sensor")
        self._attr_icon = self._get_icon()
        self._cached_state = None

        # Initialize state from coordinator data
        self._update_cached_state()

    def _get_icon(self) -> str:
        """Get appropriate icon for the binary sensor."""
        name_lower = self._name.lower()
        device_class = self._attr_device_class

        if device_class == BinarySensorDeviceClass.RUNNING:
            if "boost" in name_lower:
                return "mdi:rocket-launch"
            elif "warm" in name_lower:
                return "mdi:heat-wave"
            elif "flex" in name_lower:
                return "mdi:resize"
            elif "bbq" in name_lower:
                return "mdi:grill"
            elif "selected" in name_lower:
                return "mdi:circle-slice-8"
            return "mdi:play-circle"

        return "mdi:circle"

    def _update_cached_state(self) -> None:
        """Update the cached state from coordinator data."""
        value = self._get_data_point_value()
        if value is None:
            self._cached_state = None
        elif isinstance(value, bool):
            self._cached_state = value
        elif isinstance(value, int):
            self._cached_state = bool(value)
        else:
            self._cached_state = False

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self._cached_state


class KKTKolbeZoneBinarySensor(KKTZoneBaseEntity, BinarySensorEntity):
    """Zone-specific binary sensor for KKT Kolbe devices."""

    def __init__(self, coordinator, entry: ConfigEntry, config: dict):
        """Initialize the zone binary sensor."""
        super().__init__(coordinator, entry, config, "binary_sensor")

        # Override device class for zone sensors
        if not self._attr_device_class:
            self._attr_device_class = BinarySensorDeviceClass.RUNNING

        self._attr_icon = self._get_icon()
        self._cached_state = None

        # Initialize state from coordinator data
        self._update_cached_state()

    def _get_icon(self) -> str:
        """Get appropriate icon for the zone binary sensor."""
        name_lower = self._name.lower()

        if "boost" in name_lower:
            return "mdi:rocket-launch"
        elif "warm" in name_lower:
            return "mdi:heat-wave"
        elif "flex" in name_lower:
            return "mdi:resize"
        elif "bbq" in name_lower:
            return "mdi:grill"
        elif "selected" in name_lower:
            return "mdi:circle-slice-8"

        return "mdi:play-circle"

    def _update_cached_state(self) -> None:
        """Update the cached state from coordinator data."""
        # Check if this DP uses bitfield encoding
        if self._dp in BITFIELD_CONFIG and BITFIELD_CONFIG[self._dp]["type"] == "bit":
            # Use bitfield utilities for Base64-encoded RAW data
            value = get_zone_value_from_coordinator(self.coordinator, self._dp, self._zone)
            self._cached_state = bool(value) if value is not None else None
        else:
            # Fallback to legacy zone handling
            self._cached_state = self._get_zone_data_point_value(self._dp, self._zone)

    @property
    def is_on(self) -> bool | None:
        """Return true if the zone binary sensor is on."""
        return self._cached_state