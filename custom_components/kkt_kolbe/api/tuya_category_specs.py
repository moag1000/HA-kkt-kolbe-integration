"""Tuya category specifications for automatic device configuration."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

_LOGGER = logging.getLogger(__name__)


class TuyaCategorySpecs:
    """Manages Tuya category specifications for device configuration."""

    def __init__(self):
        """Initialize with known category specifications."""
        self._specs: dict[str, dict] = {}
        self._load_known_specs()

    def _load_known_specs(self) -> None:
        """Load known category specifications."""
        specs_dir = Path(__file__).parent.parent / "known_configs"

        # Load all available category specifications
        categories = {
            "yyj": ("yyj_category_info.json", self._load_embedded_yyj_spec),
            "dcl": ("dcl_category_info.json", self._load_embedded_dcl_spec),
            "xfj": ("xfj_category_info.json", self._load_embedded_xfj_spec),
        }

        for category, (filename, fallback_func) in categories.items():
            try:
                category_file = specs_dir / filename

                if category_file.exists():
                    with open(category_file, encoding='utf-8') as f:
                        category_data = json.load(f)
                        if category_data.get("success") and "result" in category_data:
                            self._specs[category] = category_data["result"]
                            _LOGGER.info("Loaded %s category specification from file", category.upper())
                        else:
                            _LOGGER.warning("Invalid %s spec format, using fallback", category.upper())
                            fallback_func()
                else:
                    # Fallback to embedded specification
                    fallback_func()

            except Exception as err:
                _LOGGER.warning("Failed to load %s spec from file, using embedded: %s", category.upper(), err)
                fallback_func()

    def _load_embedded_yyj_spec(self) -> None:
        """Load embedded YYJ specification as fallback."""
        self._specs["yyj"] = {
            "category": "yyj",
            "status_list": [
                {
                    "code": "fan_speed_enum",
                    "name": "风速",
                    "type": "Enum",
                    "values": "{\"range\":[\"off\",\"low\",\"middle\",\"high\",\"strong\"]}"
                },
                {
                    "code": "switch_lamp",
                    "name": "灯带开关",
                    "type": "Boolean",
                    "values": "{}"
                },
                {
                    "code": "light",
                    "name": "灯光",
                    "type": "Boolean",
                    "values": "{}"
                },
                {
                    "code": "countdown",
                    "name": "倒计时",
                    "type": "Integer",
                    "values": "{\"unit\":\"min\",\"min\":0,\"max\":100,\"scale\":0,\"step\":1}"
                },
                {
                    "code": "countdown_left",
                    "name": "倒计时剩余时间",
                    "type": "Integer",
                    "values": "{\"unit\":\"min\",\"min\":0,\"max\":100,\"scale\":0,\"step\":1}"
                },
                {
                    "code": "disinfection",
                    "name": "消毒",
                    "type": "Boolean",
                    "values": "{}"
                },
                {
                    "code": "anion",
                    "name": "负离子",
                    "type": "Boolean",
                    "values": "{}"
                },
                {
                    "code": "switch_wash",
                    "name": "清洗开关",
                    "type": "Boolean",
                    "values": "{}"
                },
                {
                    "code": "switch",
                    "name": "开关",
                    "type": "Boolean",
                    "values": "{}"
                },
                {
                    "code": "warm",
                    "name": "保温",
                    "type": "Boolean",
                    "values": "{}"
                },
                {
                    "code": "drying",
                    "name": "烘干",
                    "type": "Boolean",
                    "values": "{}"
                },
                {
                    "code": "fault",
                    "name": "故障告警",
                    "type": "Bitmap",
                    "values": "{\"label\":[\"e1\",\"e2\",\"e3\"]}"
                },
                {
                    "code": "status",
                    "name": "设备状态",
                    "type": "Enum",
                    "values": "{\"range\":[\"standby\",\"working\",\"sleeping\"]}"
                },
                {
                    "code": "total_runtime",
                    "name": "累计工作时间",
                    "type": "Integer",
                    "values": "{\"unit\":\"hour\",\"min\":0,\"max\":1000000,\"scale\":0,\"step\":1}"
                }
            ]
        }
        _LOGGER.info("Loaded embedded YYJ category specification")

    def _load_embedded_dcl_spec(self) -> None:
        """Load embedded DCL (Cooktop) specification as fallback."""
        self._specs["dcl"] = {
            "category": "dcl",
            "status_list": [
                {
                    "code": "work_mode",
                    "name": "工作模式",
                    "type": "Enum",
                    "values": "{\"range\":[\"chips\",\"drumsticks\",\"shrimp\",\"fish\",\"ribs\",\"meat\"]}"
                },
                {
                    "code": "appointment_time",
                    "name": "预约时间",
                    "type": "Integer",
                    "values": "{\"unit\":\"min\",\"min\":1,\"max\":360,\"scale\":0,\"step\":1}"
                },
                {
                    "code": "cook_temperature",
                    "name": "烹饪温度",
                    "type": "Integer",
                    "values": "{\"unit\":\"℃\",\"min\":0,\"max\":500,\"scale\":0,\"step\":1}"
                },
                {
                    "code": "current_temperature",
                    "name": "当前温度",
                    "type": "Integer",
                    "values": "{\"unit\":\"℃\",\"min\":0,\"max\":500,\"scale\":0,\"step\":1}"
                },
                {
                    "code": "cook_power",
                    "name": "烹饪功率",
                    "type": "Integer",
                    "values": "{\"unit\":\"w\",\"min\":0,\"max\":5000,\"scale\":0,\"step\":1}"
                },
                {
                    "code": "switch",
                    "name": "开关",
                    "type": "Boolean",
                    "values": "{}"
                },
                {
                    "code": "pause",
                    "name": "暂停/继续",
                    "type": "Boolean",
                    "values": "{}"
                },
                {
                    "code": "work_status",
                    "name": "工作状态",
                    "type": "Enum",
                    "values": "{\"range\":[\"standby\",\"appointment\",\"cooking\",\"done\"]}"
                },
                {
                    "code": "start",
                    "name": "启动",
                    "type": "Boolean",
                    "values": "{}"
                },
                {
                    "code": "cook_time",
                    "name": "烹饪时间",
                    "type": "Integer",
                    "values": "{\"unit\":\"min\",\"min\":1,\"max\":360,\"scale\":0,\"step\":1}"
                },
                {
                    "code": "remaining_time",
                    "name": "剩余时间",
                    "type": "Integer",
                    "values": "{\"unit\":\"min\",\"min\":0,\"max\":360,\"scale\":0,\"step\":1}"
                }
            ]
        }
        _LOGGER.info("Loaded embedded DCL category specification")

    def _load_embedded_xfj_spec(self) -> None:
        """Load embedded XFJ (Ventilation) specification as fallback."""
        self._specs["xfj"] = {
            "category": "xfj",
            "status_list": [
                # Core controls
                {
                    "code": "switch",
                    "name": "开关",
                    "type": "Boolean",
                    "values": "{}"
                },
                {
                    "code": "mode",
                    "name": "工作模式",
                    "type": "Enum",
                    "values": "{\"range\":[\"auto\",\"sleep\",\"manual\"]}"
                },
                {
                    "code": "fan_speed_enum",
                    "name": "风速",
                    "type": "Enum",
                    "values": "{\"range\":[\"low\",\"mid\",\"high\",\"sleep\"]}"
                },
                # Air flow controls
                {
                    "code": "supply_fan_speed",
                    "name": "送风风速",
                    "type": "Enum",
                    "values": "{\"range\":[\"off\",\"low\",\"mid\",\"high\"]}"
                },
                {
                    "code": "exhaust_fan_speed",
                    "name": "排风风速",
                    "type": "Enum",
                    "values": "{\"range\":[\"off\",\"low\",\"mid\",\"high\"]}"
                },
                {
                    "code": "loop_mode",
                    "name": "循环模式",
                    "type": "Enum",
                    "values": "{\"range\":[\"auto\",\"indoor_loop\",\"outdoor_loop\"]}"
                },
                # Environmental sensors
                {
                    "code": "temp_indoor",
                    "name": "室内温度",
                    "type": "Integer",
                    "values": "{\"unit\":\"℃\",\"min\":0,\"max\":50,\"scale\":0,\"step\":1}"
                },
                {
                    "code": "humidity_indoor",
                    "name": "室内湿度",
                    "type": "Integer",
                    "values": "{\"unit\":\"%\",\"min\":0,\"max\":100,\"scale\":0,\"step\":1}"
                },
                {
                    "code": "pm25",
                    "name": "PM2.5",
                    "type": "Integer",
                    "values": "{\"min\":0,\"max\":999,\"scale\":0,\"step\":1}"
                },
                {
                    "code": "air_quality",
                    "name": "空气质量",
                    "type": "Enum",
                    "values": "{\"range\":[\"great\",\"good\",\"mild\",\"medium\",\"bad\"]}"
                },
                # Filter management
                {
                    "code": "primary_filter_life",
                    "name": "初效滤网剩余/寿命",
                    "type": "Integer",
                    "values": "{\"unit\":\"%\",\"min\":0,\"max\":100,\"scale\":0,\"step\":1}"
                },
                {
                    "code": "filter_reset",
                    "name": "滤芯复位",
                    "type": "Boolean",
                    "values": "{}"
                },
                # Air purification
                {
                    "code": "purification",
                    "name": "净化/除尘",
                    "type": "Boolean",
                    "values": "{}"
                },
                {
                    "code": "anion",
                    "name": "负离子",
                    "type": "Boolean",
                    "values": "{}"
                },
                {
                    "code": "sterilize",
                    "name": "杀菌",
                    "type": "Boolean",
                    "values": "{}"
                }
            ]
        }
        _LOGGER.info("Loaded embedded XFJ category specification")

    def get_category_spec(self, category: str) -> dict | None:
        """Get specification for a category."""
        return self._specs.get(category)

    def has_category(self, category: str) -> bool:
        """Check if category specification is available."""
        return category in self._specs

    def get_supported_categories(self) -> list[str]:
        """Get list of supported categories."""
        return list(self._specs.keys())

    def map_status_to_entity_config(self, status_item: dict[str, Any], dp_id: int | None = None) -> dict | None:
        """Map a Tuya status item to entity configuration."""
        try:
            code = status_item.get("code")
            name = status_item.get("name", code)
            data_type = status_item.get("type")
            values_str = status_item.get("values", "{}")

            if not code or not data_type:
                return None

            # Parse values JSON
            try:
                values = json.loads(values_str) if values_str else {}
            except json.JSONDecodeError:
                values = {}

            # Map Tuya types to Home Assistant entity types
            entity_mapping = {
                "Boolean": {"entity_type": "switch", "data_type": "bool"},
                "Integer": {"entity_type": "number", "data_type": "value"},
                "Enum": {"entity_type": "select", "data_type": "enum"},
                "String": {"entity_type": "sensor", "data_type": "string"},
                "Bitmap": {"entity_type": "sensor", "data_type": "string"},  # Will be formatted as text
            }

            mapping = entity_mapping.get(data_type)
            if not mapping:
                _LOGGER.warning("Unknown Tuya type: %s for code: %s", data_type, code)
                return None

            # Generate friendly names for common codes
            friendly_names = {
                # YYJ - Range Hood
                "fan_speed_enum": "Fan Speed",
                "switch_lamp": "Light Strip",
                "light": "Light",
                "countdown": "Timer",
                "countdown_left": "Timer Remaining",
                "disinfection": "Disinfection",
                "anion": "Anion",
                "switch_wash": "Wash Mode",
                "switch": "Power",
                "warm": "Warm",
                "drying": "Drying",
                "fault": "Fault Status",
                "status": "Device Status",
                "total_runtime": "Total Runtime",

                # DCL - Cooktop
                "work_mode": "Cooking Mode",
                "appointment_time": "Appointment Time",
                "cook_temperature": "Cooking Temperature",
                "current_temperature": "Current Temperature",
                "cook_power": "Cooking Power",
                "pause": "Pause/Resume",
                "work_status": "Work Status",
                "start": "Start",
                "cook_time": "Cooking Time",
                "remaining_time": "Remaining Time",

                # XFJ - Ventilation
                "mode": "Work Mode",
                "air_volume": "Air Volume",
                "loop_mode": "Loop Mode",
                "supply_fan_speed": "Supply Fan Speed",
                "exhaust_fan_speed": "Exhaust Fan Speed",
                "fresh_air_valve": "Fresh Air Valve",
                "air_exhaust_fan": "Air Exhaust Fan",
                "primary_filter_reset": "Primary Filter Reset",
                "medium_filter_reset": "Medium Filter Reset",
                "high_filter_reset": "High Filter Reset",
                "sterilize": "Sterilize",
                "bypass_function": "Bypass Function",
                "heat": "Electric Heating",
                "pm25_set": "PM2.5 Setting",
                "eco2_set": "eCO2 Setting",
                "temp_set": "Temperature Setting",
                "humidity_set": "Humidity Setting",
                "tvoc_set": "TVOC Setting",
                "air_conditioning": "Air Conditioning",
                "backlight": "Backlight Brightness",
                "purify_mode": "Purify Mode",
                "purification": "Purification",
                "dehumidifier": "Dehumidifier",
                "defrost": "Defrost",
                "countdown_set": "Countdown Setting",
                "factory_reset": "Factory Reset",
                "child_lock": "Child Lock",
                "filter_reset": "Filter Reset",
                "uv_light": "UV Light",
                "pm10_set": "PM10 Setting",
                "pm10": "PM10",
                "humidity_outdoor": "Outdoor Humidity",
                "temp_outdoor": "Outdoor Temperature",
                "air_quality": "Air Quality",
                "supply_temp": "Supply Temperature",
                "exhaust_temp": "Exhaust Temperature",
                "supply_air_vol": "Supply Air Volume",
                "exhaust_air_vol": "Exhaust Air Volume",
                "primary_filter_life": "Primary Filter Life",
                "medium_filter_life": "Medium Filter Life",
                "high_filter_life": "High Filter Life",
                "filter_life": "Filter Life",
                "uv_life": "UV Life",
                "temp_indoor": "Indoor Temperature",
                "humidity_indoor": "Indoor Humidity",
                "tvoc": "TVOC",
                "eco2": "eCO2",
                "pm25": "PM2.5",
                "hcho_sensor_value": "HCHO Level",
            }

            # Generate icon for common codes
            icons = {
                # YYJ - Range Hood
                "fan_speed_enum": "mdi:fan",
                "switch_lamp": "mdi:lightbulb",
                "light": "mdi:lightbulb",
                "countdown": "mdi:timer",
                "countdown_left": "mdi:timer-sand",
                "disinfection": "mdi:spray-bottle",
                "anion": "mdi:air-filter",
                "switch_wash": "mdi:washing-machine",
                "switch": "mdi:power",
                "warm": "mdi:thermometer",
                "drying": "mdi:air-filter",
                "fault": "mdi:alert-circle",
                "status": "mdi:information",
                "total_runtime": "mdi:clock-time-eight",

                # DCL - Cooktop
                "work_mode": "mdi:chef-hat",
                "appointment_time": "mdi:clock-outline",
                "cook_temperature": "mdi:thermometer",
                "current_temperature": "mdi:thermometer",
                "cook_power": "mdi:flash",
                "pause": "mdi:pause",
                "work_status": "mdi:stove",
                "start": "mdi:play",
                "cook_time": "mdi:timer",
                "remaining_time": "mdi:timer-sand",

                # XFJ - Ventilation
                "mode": "mdi:cog",
                "air_volume": "mdi:weather-windy",
                "loop_mode": "mdi:sync",
                "supply_fan_speed": "mdi:fan",
                "exhaust_fan_speed": "mdi:fan",
                "fresh_air_valve": "mdi:valve",
                "air_exhaust_fan": "mdi:fan",
                "primary_filter_reset": "mdi:filter",
                "medium_filter_reset": "mdi:filter",
                "high_filter_reset": "mdi:filter",
                "sterilize": "mdi:spray-bottle",
                "bypass_function": "mdi:swap-horizontal",
                "heat": "mdi:radiator",
                "pm25_set": "mdi:air-filter",
                "eco2_set": "mdi:molecule-co2",
                "temp_set": "mdi:thermometer",
                "humidity_set": "mdi:water-percent",
                "tvoc_set": "mdi:chemical-weapon",
                "air_conditioning": "mdi:air-conditioner",
                "backlight": "mdi:brightness-6",
                "purify_mode": "mdi:air-purifier",
                "purification": "mdi:air-purifier",
                "dehumidifier": "mdi:air-humidifier-off",
                "defrost": "mdi:snowflake-melt",
                "countdown_set": "mdi:timer-cog",
                "factory_reset": "mdi:factory",
                "child_lock": "mdi:lock",
                "filter_reset": "mdi:filter-check",
                "uv_light": "mdi:lightbulb-fluorescent-tube",
                "pm10_set": "mdi:air-filter",
                "pm10": "mdi:air-filter",
                "humidity_outdoor": "mdi:water-percent",
                "temp_outdoor": "mdi:thermometer",
                "air_quality": "mdi:air-purifier",
                "supply_temp": "mdi:thermometer-plus",
                "exhaust_temp": "mdi:thermometer-minus",
                "supply_air_vol": "mdi:weather-windy",
                "exhaust_air_vol": "mdi:weather-windy",
                "primary_filter_life": "mdi:filter-check",
                "medium_filter_life": "mdi:filter-check",
                "high_filter_life": "mdi:filter-check",
                "filter_life": "mdi:filter-check",
                "uv_life": "mdi:lightbulb-fluorescent-tube",
                "temp_indoor": "mdi:home-thermometer",
                "humidity_indoor": "mdi:home-thermometer",
                "tvoc": "mdi:chemical-weapon",
                "eco2": "mdi:molecule-co2",
                "pm25": "mdi:air-filter",
                "hcho_sensor_value": "mdi:chemical-weapon",
            }

            config = {
                "dp_id": dp_id,
                "property_code": code,
                "entity_type": mapping["entity_type"],
                "name": friendly_names.get(code, name),
                "data_type": mapping["data_type"],
                "description": f"Tuya {data_type} property: {name}",
                "icon": icons.get(code),
            }

            # Add range data for value/enum types
            if values:
                config["range_data"] = values

            # Special handling for read-only properties
            readonly_codes = [
                # YYJ - Range Hood
                "countdown_left", "fault", "status", "total_runtime",
                # DCL - Cooktop
                "current_temperature", "work_status", "remaining_time",
                # XFJ - Ventilation (sensors/monitoring)
                "temp_indoor", "humidity_indoor", "temp_outdoor", "humidity_outdoor",
                "pm25", "pm10", "tvoc", "eco2", "air_quality", "hcho_sensor_value",
                "supply_temp", "exhaust_temp", "supply_air_vol", "exhaust_air_vol",
                "primary_filter_life", "medium_filter_life", "high_filter_life",
                "filter_life", "uv_life", "countdown_left"
            ]
            if code in readonly_codes and mapping["entity_type"] != "sensor":
                config["entity_type"] = "sensor"

            return config

        except Exception as err:
            _LOGGER.error("Failed to map status item %s: %s", status_item, err)
            return None

    def generate_device_config_from_category(
        self,
        device_id: str,
        category: str,
        device_name: str | None = None,
        model_id: str | None = None
    ) -> list[dict] | None:
        """Generate complete device configuration from category specification."""
        spec = self.get_category_spec(category)
        if not spec:
            _LOGGER.warning("No specification available for category: %s", category)
            return None

        status_list = spec.get("status_list", [])
        if not status_list:
            _LOGGER.warning("No status list in category specification: %s", category)
            return None

        entities = []
        for i, status_item in enumerate(status_list):
            # Use index as DP ID if not provided (will be mapped later)
            entity_config = self.map_status_to_entity_config(status_item, dp_id=i + 1)
            if entity_config:
                entities.append(entity_config)

        if not entities:
            _LOGGER.warning("No entities generated from category: %s", category)
            return None

        _LOGGER.info("Generated %d entities from category %s for device %s",
                    len(entities), category, device_id[:8])

        return entities
