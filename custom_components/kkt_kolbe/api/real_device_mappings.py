"""Real device data point mappings based on actual API responses."""
from __future__ import annotations

import logging

_LOGGER = logging.getLogger(__name__)


class RealDeviceMappings:
    """Manages real device data point mappings from actual API calls."""

    # Constant for default hood identifier
    DEFAULT_HOOD_ID = "default_hood"

    def __init__(self):
        """Initialize with real device mappings."""
        self._device_mappings = self._load_real_mappings()

    def _load_real_mappings(self) -> dict[str, dict]:
        """Load real device mappings from actual API responses."""
        return {
            # DEFAULT HOOD - Standard YYJ category DPs that work with most range hoods
            # Use this when the specific device model is unknown or not fully supported
            "default_hood": {
                "device_type": "hood",
                "category": "yyj",
                "display_name": "Default Hood - Generic Range Hood",
                "description": "Standard range hood controls (use if your specific model is not listed)",
                "codes": [
                    "switch",           # Main power (DP 1)
                    "fan_speed_enum",   # Fan speed (DP 3)
                    "light",            # Main light (DP 101)
                    "countdown",        # Timer (DP 6)
                    "countdown_left",   # Timer remaining (DP 7)
                ],
                "entities": {
                    "switch": {
                        "type": "switch",
                        "name": "Power",
                        "icon": "mdi:power",
                        "read_write": True
                    },
                    "fan_speed_enum": {
                        "type": "select",
                        "name": "Fan Speed",
                        "icon": "mdi:fan",
                        "options": ["off", "low", "middle", "high"],
                        "read_write": True
                    },
                    "light": {
                        "type": "switch",
                        "name": "Light",
                        "icon": "mdi:lightbulb",
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
                    "countdown_left": {
                        "type": "sensor",
                        "name": "Timer Remaining",
                        "icon": "mdi:timer-sand",
                        "unit": "min",
                        "read_write": False
                    }
                }
            },

            # HERMES & STYLE Hood - Real API data points
            "hermes_style": {
                "device_type": "hood",
                "category": "yyj",
                "display_name": "HERMES & STYLE (Range Hood)",
                "description": "KKT Kolbe HERMES & STYLE with RGB lighting",
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
                "display_name": "IND7705HC (Induction Cooktop)",
                "description": "KKT Kolbe 5-zone induction cooktop",
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

    def get_device_codes(self, device_type: str) -> list[str | None]:
        """Get device codes for real-time API calls."""
        mapping = self._device_mappings.get(device_type)
        return mapping.get("codes") if mapping else None

    def get_device_entities(self, device_type: str) -> dict | None:
        """Get device entity mappings."""
        mapping = self._device_mappings.get(device_type)
        return mapping.get("entities") if mapping else None

    def get_device_category(self, device_type: str) -> str | None:
        """Get device category."""
        mapping = self._device_mappings.get(device_type)
        return mapping.get("category") if mapping else None

    def is_supported_device(self, device_type: str) -> bool:
        """Check if device type is supported with real mappings."""
        return device_type in self._device_mappings

    def get_supported_devices(self) -> list[str]:
        """Get list of supported device types."""
        return list(self._device_mappings.keys())

    def get_optimized_codes_for_polling(self, device_type: str) -> list[str | None]:
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

    def get_writable_codes(self, device_type: str) -> list[str | None]:
        """Get codes that can be written to (for commands)."""
        entities = self.get_device_entities(device_type)
        if not entities:
            return None

        writable_codes = []
        for code, config in entities.items():
            if config.get("read_write", False):
                writable_codes.append(code)

        return writable_codes

    def get_device_display_info(self, device_type: str) -> dict | None:
        """Get display info for a device type (for UI selection)."""
        mapping = self._device_mappings.get(device_type)
        if not mapping:
            return None

        return {
            "id": device_type,
            "display_name": mapping.get("display_name", device_type.replace("_", " ").title()),
            "description": mapping.get("description", ""),
            "device_type": mapping.get("device_type", "unknown"),
            "category": mapping.get("category", "unknown"),
        }

    def get_hood_devices_for_selection(self) -> list[dict]:
        """Get all hood device types formatted for UI selection.

        Returns devices in order: specific models first, then default hood last.
        """
        hoods = []
        default_hood = None

        for device_id, mapping in self._device_mappings.items():
            if mapping.get("device_type") == "hood":
                info = self.get_device_display_info(device_id)
                if info:
                    if device_id == self.DEFAULT_HOOD_ID:
                        default_hood = info
                    else:
                        hoods.append(info)

        # Sort specific hoods alphabetically, then add default at the end
        hoods.sort(key=lambda x: x["display_name"])
        if default_hood:
            hoods.append(default_hood)

        return hoods

    def get_all_devices_for_selection(self) -> list[dict]:
        """Get all device types formatted for UI selection.

        Returns devices grouped by type: specific hoods first, then cooktops,
        then default/generic options at the very end.
        """
        hoods = []
        cooktops = []
        others = []
        defaults = []

        for device_id, mapping in self._device_mappings.items():
            info = self.get_device_display_info(device_id)
            if not info:
                continue

            device_type = mapping.get("device_type")
            # Check if this is a default/generic device
            if self.is_default_device(device_id):
                defaults.append(info)
            elif device_type == "hood":
                hoods.append(info)
            elif device_type == "cooktop":
                cooktops.append(info)
            else:
                others.append(info)

        # Sort each group alphabetically
        hoods.sort(key=lambda x: x["display_name"])
        cooktops.sort(key=lambda x: x["display_name"])
        others.sort(key=lambda x: x["display_name"])
        defaults.sort(key=lambda x: x["display_name"])

        # Return: specific hoods, cooktops, others, then defaults at the very end
        return hoods + cooktops + others + defaults

    def is_default_device(self, device_type: str) -> bool:
        """Check if this is a default/generic device type."""
        return device_type == self.DEFAULT_HOOD_ID