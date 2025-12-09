"""Dynamic device factory for creating configurations from API data."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

_LOGGER = logging.getLogger(__name__)


@dataclass
class EntityConfig:
    """Configuration for a single entity."""
    dp_id: int
    property_code: str
    entity_type: str  # switch, sensor, number, select, etc.
    name: str
    data_type: str  # bool, value, enum, string
    description: str = ""
    range_data: Dict | None = None  # For value/enum types
    unit: str | None = None
    icon: str | None = None


@dataclass
class DeviceConfig:
    """Complete device configuration."""
    device_id: str
    model_id: str
    device_type: str  # hood, cooktop, unknown
    name: str
    manufacturer: str = "KKT Kolbe"
    entities: list[EntityConfig] = None

    def __post_init__(self):
        if self.entities is None:
            self.entities = []


class DynamicDeviceFactory:
    """Erstellt Gerätekonfigurationen basierend auf API-Daten."""

    # Known KKT Kolbe device type patterns
    DEVICE_TYPE_PATTERNS = {
        "hood": ["hood", "abzug", "dunst", "extractor"],
        "cooktop": ["cooktop", "hob", "kochfeld", "stove"],
    }

    # Data point mapping for entity types
    DP_ENTITY_MAPPING = {
        # Switches (boolean controls)
        "switch": "switch",
        "light": "light",
        "switch_lamp": "switch",
        "switch_wash": "switch",
        "switch_led": "switch",
        "switch_led_1": "light",

        # Fan speed (special handling)
        "fan_speed": "fan",
        "fan_speed_enum": "fan",

        # Numbers (value inputs)
        "countdown": "number",
        "countdown_1": "number",
        "day": "number",
        "day_1": "number",

        # Selects (enum choices)
        "work_mode": "select",
        "RGB": "select",

        # Special handling for color data
        "colour_data": "light",  # RGB color control
    }

    # Icon mapping for different property codes
    ICON_MAPPING = {
        "switch": "mdi:power",
        "light": "mdi:lightbulb",
        "switch_lamp": "mdi:lightbulb-outline",
        "switch_wash": "mdi:washing-machine",
        "fan_speed": "mdi:fan",
        "countdown": "mdi:timer",
        "day": "mdi:calendar-clock",
        "work_mode": "mdi:palette",
        "colour_data": "mdi:palette",
        "RGB": "mdi:palette",
    }

    async def analyze_device_properties(self, api_data: Dict) -> DeviceConfig:
        """Analyze API response and create device configuration."""
        _LOGGER.debug("Analyzing device properties from API data")

        # Extract basic device info
        device_info = self._extract_device_info(api_data)

        # Parse the model data (JSON string in API response)
        model_data = self._parse_model_data(api_data.get("result", {}).get("model", "{}"))

        # Create device config
        device_config = DeviceConfig(
            device_id=device_info.get("device_id", "unknown"),
            model_id=device_info.get("model_id", "unknown"),
            device_type=await self.detect_device_type(model_data),
            name=device_info.get("name", "KKT Kolbe Device"),
        )

        # Create entity configurations
        device_config.entities = await self.create_entity_configurations(model_data)

        _LOGGER.info(f"Created device config with {len(device_config.entities)} entities")
        return device_config

    def _extract_device_info(self, api_data: Dict) -> Dict:
        """Extract basic device information from API response."""
        result = api_data.get("result", {})

        return {
            "device_id": result.get("device_id", "unknown"),
            "model_id": result.get("model_id", "unknown"),
            "name": result.get("name", "KKT Kolbe Device"),
        }

    def _parse_model_data(self, model_json: str) -> Dict:
        """Parse the nested JSON model data from API response."""
        try:
            import json
            model_data = json.loads(model_json)
            return model_data
        except (json.JSONDecodeError, TypeError) as err:
            _LOGGER.warning(f"Failed to parse model data: {err}")
            return {}

    async def detect_device_type(self, model_data: Dict) -> str:
        """Detect device type from model data."""
        model_id = model_data.get("modelId", "").lower()

        # Check known patterns
        for device_type, patterns in self.DEVICE_TYPE_PATTERNS.items():
            if any(pattern in model_id for pattern in patterns):
                _LOGGER.debug(f"Detected device type '{device_type}' from model ID '{model_id}'")
                return device_type

        # Analyze properties for clues
        services = model_data.get("services", [])
        if services:
            properties = services[0].get("properties", [])
            property_codes = [prop.get("code", "") for prop in properties]

            # Hood indicators
            if any(code in ["fan_speed", "switch_wash", "countdown"] for code in property_codes):
                return "hood"

            # Cooktop indicators
            if any(code in ["temp", "timer", "burner"] for code in property_codes):
                return "cooktop"

        _LOGGER.debug(f"Could not detect device type for model '{model_id}', using 'unknown'")
        return "unknown"

    async def create_entity_configurations(self, model_data: Dict) -> list[EntityConfig]:
        """Create entity configurations from model data."""
        entities = []

        services = model_data.get("services", [])
        if not services:
            _LOGGER.warning("No services found in model data")
            return entities

        # Process properties from the first service (default service)
        properties = services[0].get("properties", [])

        for prop in properties:
            entity_config = await self._create_entity_from_property(prop)
            if entity_config:
                entities.append(entity_config)

        _LOGGER.debug(f"Created {len(entities)} entity configurations")
        return entities

    async def _create_entity_from_property(self, property_data: Dict) -> EntityConfig | None:
        """Create entity configuration from a single property."""
        code = property_data.get("code")
        ability_id = property_data.get("abilityId")
        name = property_data.get("name", code)
        type_spec = property_data.get("typeSpec", {})

        if not code or ability_id is None:
            _LOGGER.warning(f"Property missing required fields: {property_data}")
            return None

        # Determine entity type
        entity_type = self.DP_ENTITY_MAPPING.get(code, "sensor")

        # Determine data type
        data_type = type_spec.get("type", "unknown")

        # Extract range data for value/enum types
        range_data = None
        if data_type == "value":
            range_data = {
                "min": type_spec.get("min", 0),
                "max": type_spec.get("max", 100),
                "step": type_spec.get("step", 1),
                "scale": type_spec.get("scale", 0),
            }
        elif data_type == "enum":
            range_data = {
                "options": type_spec.get("range", [])
            }

        # Get unit and icon
        unit = type_spec.get("unit")
        icon = self.ICON_MAPPING.get(code)

        entity_config = EntityConfig(
            dp_id=ability_id,
            property_code=code,
            entity_type=entity_type,
            name=name,
            data_type=data_type,
            description=property_data.get("description", ""),
            range_data=range_data,
            unit=unit,
            icon=icon,
        )

        _LOGGER.debug(f"Created entity config: DP{ability_id} ({code}) -> {entity_type}")
        return entity_config

    async def map_data_points_to_entities(self, device_config: DeviceConfig) -> Dict:
        """Map data points to entity configurations for integration use."""
        data_points = {}

        for entity in device_config.entities:
            data_points[entity.dp_id] = entity.property_code

        _LOGGER.debug(f"Mapped {len(data_points)} data points for device")
        return data_points

    async def get_device_types_config(self, device_config: DeviceConfig) -> Dict:
        """Generate device_types.py compatible configuration."""
        config = {
            f"{device_config.model_id}_{device_config.device_type}": {
                "name": device_config.name,
                "model_id": device_config.model_id,
                "category": device_config.device_type,
                "data_points": await self.map_data_points_to_entities(device_config),
            }
        }

        return config