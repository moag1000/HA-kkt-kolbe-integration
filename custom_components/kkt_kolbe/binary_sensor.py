"""Binary Sensor platform for KKT Kolbe devices."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.core import callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .base_entity import KKTBaseEntity
from .base_entity import KKTZoneBaseEntity
from .bitfield_utils import BITFIELD_CONFIG
from .bitfield_utils import get_zone_value_from_coordinator
from .const import DOMAIN
from .const import MANUFACTURER
from .device_types import get_device_entities

if TYPE_CHECKING:
    from . import KKTKolbeConfigEntry

# Limit parallel updates - 0 means unlimited (coordinator-based entities)
PARALLEL_UPDATES = 0

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KKTKolbeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KKT Kolbe binary sensor entities."""
    runtime_data = entry.runtime_data
    coordinator = runtime_data.coordinator
    device_type = runtime_data.device_type
    product_name = runtime_data.product_name

    # Check if advanced entities are enabled (default: True)
    enable_advanced = entry.options.get("enable_advanced_entities", True)

    # Prefer device_type (KNOWN_DEVICES key) over product_name (Tuya product ID)
    lookup_key = device_type if device_type not in ("auto", None, "") else product_name

    entities: list[BinarySensorEntity] = []

    # Always add connection status sensors (like Dyson integration)
    entities.append(KKTKolbeConnectionSensor(coordinator, entry))

    # Add API status sensor if API is enabled
    if runtime_data.api_client is not None:
        entities.append(KKTKolbeAPIStatusSensor(coordinator, entry))

    # Get binary sensor configurations for this device
    entity_configs = get_device_entities(lookup_key, "binary_sensor")

    if entity_configs:
        for config in entity_configs:
            # Skip advanced entities if not enabled
            if config.get("advanced", False) and not enable_advanced:
                continue
            if "zone" in config:
                entities.append(KKTKolbeZoneBinarySensor(coordinator, entry, config))
            else:
                entities.append(KKTKolbeBinarySensor(coordinator, entry, config))

    if entities:
        async_add_entities(entities)


class KKTKolbeBinarySensor(KKTBaseEntity, BinarySensorEntity):
    """Binary sensor for KKT Kolbe devices."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict[str, Any]],
        entry: ConfigEntry,
        config: dict[str, Any],
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, entry, config, "binary_sensor")
        self._attr_icon = self._get_icon()
        self._cached_state: bool | None = None

        # Note: entity_category is now handled in base_entity.py from device_types.py config

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

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict[str, Any]],
        entry: ConfigEntry,
        config: dict[str, Any],
    ) -> None:
        """Initialize the zone binary sensor."""
        super().__init__(coordinator, entry, config, "binary_sensor")

        # Override device class for zone sensors
        if not getattr(self, "_attr_device_class", None):
            self._attr_device_class = BinarySensorDeviceClass.RUNNING

        self._attr_icon = self._get_icon()
        self._cached_state: bool | None = None

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
        if self._zone is not None and self._dp in BITFIELD_CONFIG and BITFIELD_CONFIG[self._dp]["type"] == "bit":
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


class KKTKolbeConnectionSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor showing device connection status (like Dyson integration).

    This sensor shows whether the local device is connected and responding.
    Useful for monitoring device availability and debugging connection issues.
    """

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _attr_translation_key = "device_connected"

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict[str, Any]],
        entry: KKTKolbeConfigEntry,
    ) -> None:
        """Initialize the connection sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._device_id = entry.data.get("device_id", "unknown")

        # Set unique ID
        self._attr_unique_id = f"{self._device_id}_connection_status"
        self._attr_name = "Device Connected"

        # Device info for device registry
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": entry.runtime_data.device_info.get("name", "KKT Kolbe Device"),
            "manufacturer": MANUFACTURER,
            "model": entry.runtime_data.device_info.get("name", "Unknown"),
        }

    @property
    def is_on(self) -> bool:
        """Return true if device is connected."""
        # Check coordinator update success
        if not self.coordinator.last_update_success:
            return False

        # Check if device has is_connected property
        runtime_data = self._entry.runtime_data
        if runtime_data.device and hasattr(runtime_data.device, "is_connected"):
            return bool(runtime_data.device.is_connected)

        # Fallback: Check if we have data
        return bool(self.coordinator.data)

    @property
    def icon(self) -> str:
        """Return the icon based on connection state."""
        return "mdi:lan-connect" if self.is_on else "mdi:lan-disconnect"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        runtime_data = self._entry.runtime_data
        attrs = {
            "integration_mode": runtime_data.integration_mode,
            "device_type": runtime_data.device_type,
        }

        # Add device-specific attributes if available
        if runtime_data.device:
            if hasattr(runtime_data.device, "ip_address"):
                attrs["ip_address"] = runtime_data.device.ip_address
            if hasattr(runtime_data.device, "version"):
                attrs["protocol_version"] = runtime_data.device.version

        # Add coordinator info
        if self.coordinator.last_update_success_time:
            attrs["last_successful_update"] = self.coordinator.last_update_success_time.isoformat()

        return attrs


class KKTKolbeAPIStatusSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor showing Tuya Cloud API connection status (like Dyson integration).

    This sensor shows whether the Tuya Cloud API is authenticated and working.
    Only created when API credentials are configured.
    """

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _attr_translation_key = "api_connected"

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict[str, Any]],
        entry: KKTKolbeConfigEntry,
    ) -> None:
        """Initialize the API status sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._device_id = entry.data.get("device_id", "unknown")
        self._api_status: bool = False
        self._last_check_error: str | None = None

        # Set unique ID
        self._attr_unique_id = f"{self._device_id}_api_status"
        self._attr_name = "Cloud API Connected"

        # Device info for device registry
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": entry.runtime_data.device_info.get("name", "KKT Kolbe Device"),
            "manufacturer": MANUFACTURER,
            "model": entry.runtime_data.device_info.get("name", "Unknown"),
        }

    @property
    def is_on(self) -> bool:
        """Return true if API is connected and authenticated."""
        runtime_data = self._entry.runtime_data
        if not runtime_data.api_client:
            return False

        # Check if API client has authentication status
        if hasattr(runtime_data.api_client, "is_authenticated"):
            return bool(runtime_data.api_client.is_authenticated)

        # Check if API client has token
        if hasattr(runtime_data.api_client, "_access_token"):
            return bool(runtime_data.api_client._access_token)

        # Fallback: assume connected if client exists and coordinator works
        return bool(self.coordinator.last_update_success)

    @property
    def icon(self) -> str:
        """Return the icon based on API status."""
        return "mdi:cloud-check" if self.is_on else "mdi:cloud-off-outline"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        runtime_data = self._entry.runtime_data
        attrs: dict[str, Any] = {
            "api_enabled": runtime_data.api_client is not None,
        }

        if runtime_data.api_client:
            # Add endpoint info (redacted for security)
            endpoint = self._entry.data.get("api_endpoint", "unknown")
            attrs["api_endpoint"] = endpoint

            # Add token expiry if available
            if hasattr(runtime_data.api_client, "_token_expires_at"):
                expires_at = runtime_data.api_client._token_expires_at
                if expires_at:
                    attrs["token_expires_at"] = expires_at.isoformat() if hasattr(expires_at, "isoformat") else str(expires_at)

        if self._last_check_error:
            attrs["last_error"] = self._last_check_error

        return attrs

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Clear error on successful update
        if self.coordinator.last_update_success:
            self._last_check_error = None
        self.async_write_ha_state()
