"""Select platform for KKT Kolbe devices."""
import logging
from datetime import timedelta
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .device_types import get_device_entities

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KKT Kolbe select entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    device_info = hass.data[DOMAIN][entry.entry_id]["device_info"]
    product_name = hass.data[DOMAIN][entry.entry_id].get("product_name", "unknown")

    entities = []
    select_configs = get_device_entities(product_name, "select")

    for config in select_configs:
        entities.append(KKTKolbeSelect(coordinator, entry, config))

    if entities:
        async_add_entities(entities)

class KKTKolbeSelect(CoordinatorEntity, SelectEntity):
    """Generic select entity for KKT Kolbe devices."""

    def __init__(self, coordinator, entry: ConfigEntry, config: dict):
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._entry = entry
        self._config = config
        self._dp = config["dp"]
        self._name = config["name"]
        self._options = config["options"]

        # Set up entity attributes
        self._attr_unique_id = f"{entry.entry_id}_select_{self._name.lower().replace(' ', '_')}"
        self._attr_has_entity_name = True
        self._attr_name = self._name
        self._attr_options = self._options
        self._attr_icon = self._get_icon()

    def _get_icon(self) -> str:
        """Get appropriate icon for the select."""
        name_lower = self._name.lower()
        if "rgb" in name_lower or "color" in name_lower:
            return "mdi:palette"
        elif "speed" in name_lower:
            return "mdi:speedometer"
        elif "mode" in name_lower:
            return "mdi:format-list-bulleted"
        elif "level" in name_lower:
            return "mdi:format-list-numbered"
        elif "temp" in name_lower:
            return "mdi:thermometer"
        else:
            return "mdi:form-select"

    @property
    def current_option(self) -> str | None:
        """Return the selected entity option."""
        data = self.coordinator.data
        if not data:
            return None

        value = data.get(self._dp)
        if value is None:
            return None

        # Convert value to option
        if isinstance(value, int) and 0 <= value < len(self._options):
            return self._options[value]
        elif isinstance(value, str) and value in self._options:
            return value

        return None

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if option not in self._options:
            _LOGGER.error(f"Option {option} not valid for {self._name}")
            return

        # Convert option to value
        if option in self._options:
            value = self._options.index(option)
            await self.coordinator.async_set_data_point(self._dp, value)

    @property
    def device_info(self):
        """Return device information."""
        return self.coordinator.device_info