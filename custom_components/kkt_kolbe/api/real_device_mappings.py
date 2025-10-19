"""Real device data point mappings based on actual API responses."""
import logging
from typing import Dict, List, Optional

_LOGGER = logging.getLogger(__name__)


class RealDeviceMappings:
    """Manages real device data point mappings from actual API calls."""

    def __init__(self):
        """Initialize with real device mappings."""
        self._device_mappings = self._load_real_mappings()

    def _load_real_mappings(self) -> Dict[str, Dict]:
        """Load real device mappings from actual API responses."""
        return {
            # HERMES & STYLE Hood - Real API data points
            "hermes_style": {
                "device_type": "hood",
                "category": "yyj",
                "codes": [
                    "switch",           # Main power
                    "light",            # Main light
                    "switch_lamp",      # Light strip
                    "fan_speed_enum",   # Fan speed (off/low/middle/high/strong)
                    "countdown",        # Timer
                    "RGB"               # RGB lighting control
                ],
                "entities": {
                    "switch": {
                        "type": "switch",
                        "name": "Power",
                        "icon": "mdi:power",
                        "read_write": True
                    },
                    "light": {
                        "type": "switch",
                        "name": "Main Light",
                        "icon": "mdi:lightbulb",
                        "read_write": True
                    },
                    "switch_lamp": {
                        "type": "switch",
                        "name": "Light Strip",
                        "icon": "mdi:led-strip",
                        "read_write": True
                    },
                    "fan_speed_enum": {
                        "type": "select",
                        "name": "Fan Speed",
                        "icon": "mdi:fan",
                        "options": ["off", "low", "middle", "high", "strong"],
                        "read_write": True
                    },
                    "countdown": {
                        "type": "number",
                        "name": "Timer",
                        "icon": "mdi:timer",
                        "unit": "min",
                        "min": 0,
                        "max": 100,
                        "read_write": True
                    },
                    "RGB": {
                        "type": "light",  # Special RGB light entity
                        "name": "RGB Lighting",
                        "icon": "mdi:palette",
                        "supports_color": True,
                        "read_write": True
                    }
                }
            },

            # IND7705HC Cooktop - Real API data points
            "ind7705hc": {
                "device_type": "cooktop",
                "category": "dcl",
                "codes": [
                    # Core controls
                    "user_device_power_switch",     # Main power
                    "user_device_pause_switch",     # Pause/Resume
                    "user_device_lock_switch",      # Child lock

                    # Zone controls (5 zones)
                    "oem_hob_1_quick_level",        # Zone 1 quick level
                    "oem_hob_2_quick_level",        # Zone 2 quick level
                    "oem_hob_3_quick_level",        # Zone 3 quick level
                    "oem_hob_4_quick_level",        # Zone 4 quick level
                    "oem_hob_5_quick_level",        # Zone 5 quick level

                    # Advanced features
                    "oem_device_chef_level",        # Chef function level
                    "oem_hob_bbq_timer",           # BBQ timer
                    "oem_hob_bbq_switch",          # BBQ mode
                    "oem_hob_flex_switch",         # Flex zone
                    "oem_hob_boost_switch",        # Boost function
                    "oem_hob_warm_switch",         # Keep warm

                    # Status and monitoring
                    "user_device_cur_max_level",   # Current max level
                    "oem_hob_error_num",           # Error number
                    "oem_device_timer_num",        # Timer number
                    "oem_hob_timer_num",           # Hob timer
                    "oem_hob_level_num",           # Current level
                    "oem_hob_selected_switch",     # Selected zone

                    # Settings
                    "oem_device_old_people",       # Senior mode
                    "oem_device_save_level",       # Saved level
                    "oem_device_set_level",        # Set level
                    "oem_device_power_limit",      # Power limit
                    "oem_device_confirm",          # Confirmation

                    # Core sensor features
                    "oem_hob_set_core_sensor",     # Core sensor setting
                    "oem_hob_disp_coresensor",     # Core sensor display
                ],
                "entities": {
                    # Main controls
                    "user_device_power_switch": {
                        "type": "switch",
                        "name": "Power",
                        "icon": "mdi:power",
                        "read_write": True
                    },
                    "user_device_pause_switch": {
                        "type": "switch",
                        "name": "Pause",
                        "icon": "mdi:pause",
                        "read_write": True
                    },
                    "user_device_lock_switch": {
                        "type": "switch",
                        "name": "Child Lock",
                        "icon": "mdi:lock",
                        "read_write": True
                    },

                    # Zone controls
                    "oem_hob_1_quick_level": {
                        "type": "number",
                        "name": "Zone 1 Level",
                        "icon": "mdi:numeric-1-circle",
                        "min": 0,
                        "max": 9,
                        "read_write": True
                    },
                    "oem_hob_2_quick_level": {
                        "type": "number",
                        "name": "Zone 2 Level",
                        "icon": "mdi:numeric-2-circle",
                        "min": 0,
                        "max": 9,
                        "read_write": True
                    },
                    "oem_hob_3_quick_level": {
                        "type": "number",
                        "name": "Zone 3 Level",
                        "icon": "mdi:numeric-3-circle",
                        "min": 0,
                        "max": 9,
                        "read_write": True
                    },
                    "oem_hob_4_quick_level": {
                        "type": "number",
                        "name": "Zone 4 Level",
                        "icon": "mdi:numeric-4-circle",
                        "min": 0,
                        "max": 9,
                        "read_write": True
                    },
                    "oem_hob_5_quick_level": {
                        "type": "number",
                        "name": "Zone 5 Level",
                        "icon": "mdi:numeric-5-circle",
                        "min": 0,
                        "max": 9,
                        "read_write": True
                    },

                    # Advanced features
                    "oem_device_chef_level": {
                        "type": "number",
                        "name": "Chef Level",
                        "icon": "mdi:chef-hat",
                        "min": 0,
                        "max": 9,
                        "read_write": True
                    },
                    "oem_hob_bbq_timer": {
                        "type": "number",
                        "name": "BBQ Timer",
                        "icon": "mdi:timer",
                        "unit": "min",
                        "min": 0,
                        "max": 255,
                        "read_write": True
                    },
                    "oem_hob_bbq_switch": {
                        "type": "switch",
                        "name": "BBQ Mode",
                        "icon": "mdi:grill",
                        "read_write": True
                    },
                    "oem_hob_flex_switch": {
                        "type": "switch",
                        "name": "Flex Zone",
                        "icon": "mdi:vector-combine",
                        "read_write": True
                    },
                    "oem_hob_boost_switch": {
                        "type": "switch",
                        "name": "Boost",
                        "icon": "mdi:rocket-launch",
                        "read_write": True
                    },
                    "oem_hob_warm_switch": {
                        "type": "switch",
                        "name": "Keep Warm",
                        "icon": "mdi:thermometer",
                        "read_write": True
                    },

                    # Status sensors (read-only)
                    "user_device_cur_max_level": {
                        "type": "sensor",
                        "name": "Current Max Level",
                        "icon": "mdi:speedometer",
                        "read_write": False
                    },
                    "oem_hob_error_num": {
                        "type": "sensor",
                        "name": "Error Code",
                        "icon": "mdi:alert-circle",
                        "read_write": False
                    },
                    "oem_hob_selected_switch": {
                        "type": "sensor",
                        "name": "Selected Zone",
                        "icon": "mdi:target",
                        "read_write": False
                    },
                    "oem_hob_level_num": {
                        "type": "sensor",
                        "name": "Current Level",
                        "icon": "mdi:speedometer",
                        "read_write": False
                    }
                }
            }
        }

    def get_device_codes(self, device_type: str) -> Optional[List[str]]:
        """Get device codes for real-time API calls."""
        mapping = self._device_mappings.get(device_type)
        return mapping.get("codes") if mapping else None

    def get_device_entities(self, device_type: str) -> Optional[Dict]:
        """Get device entity mappings."""
        mapping = self._device_mappings.get(device_type)
        return mapping.get("entities") if mapping else None

    def get_device_category(self, device_type: str) -> Optional[str]:
        """Get device category."""
        mapping = self._device_mappings.get(device_type)
        return mapping.get("category") if mapping else None

    def is_supported_device(self, device_type: str) -> bool:
        """Check if device type is supported with real mappings."""
        return device_type in self._device_mappings

    def get_supported_devices(self) -> List[str]:
        """Get list of supported device types."""
        return list(self._device_mappings.keys())

    def get_optimized_codes_for_polling(self, device_type: str) -> Optional[List[str]]:
        """Get optimized codes for real-time polling (exclude write-only)."""
        entities = self.get_device_entities(device_type)
        if not entities:
            return None

        # Only include readable codes for polling
        readable_codes = []
        for code, config in entities.items():
            # Include if it's readable (read_write=True or sensor)
            if config.get("read_write", False) or config.get("type") == "sensor":
                readable_codes.append(code)

        return readable_codes

    def get_writable_codes(self, device_type: str) -> Optional[List[str]]:
        """Get codes that can be written to (for commands)."""
        entities = self.get_device_entities(device_type)
        if not entities:
            return None

        writable_codes = []
        for code, config in entities.items():
            if config.get("read_write", False):
                writable_codes.append(code)

        return writable_codes