"""Device type specific configurations for KKT Kolbe devices."""
from __future__ import annotations

from homeassistant.const import UnitOfTemperature
from homeassistant.const import UnitOfTime

from .const import CATEGORY_COOKTOP
from .const import CATEGORY_HOOD

# Hood (Dunstabzugshaube) Data Points
HOOD_DPS = {
    1: "switch",           # Main power
    2: "delay_switch",     # Delay shutdown
    3: "auto_mode",        # Auto mode on/off
    4: "light",           # Light on/off
    5: "light_brightness", # Light brightness (0-255) - Common for hoods
    6: "switch_lamp",     # Filter cleaning reminder
    7: "temperature",     # Temperature sensor
    8: "humidity",        # Humidity sensor
    9: "air_quality",     # Air quality sensor
    10: "fan_speed_enum", # Fan speed
    11: "fan_speed_set",  # Fan speed setting (0-4) - For direct control
    12: "auto_clean",     # Auto cleaning mode
    13: "countdown",      # Timer (0-60 min)
    14: "filter_hours",   # Filter usage hours - Common monitoring
    15: "filter_reset",   # Filter reset switch
    16: "noise_level",    # Noise level setting
    17: "eco_mode",       # Eco mode on/off
    101: "RGB",           # RGB light mode (0-9)
    102: "rgb_brightness", # RGB brightness (0-255)
    103: "color_temp",    # Color temperature (warm/cold)
}

# KKT IND7705HC Induction Cooktop Data Points (Model ID: e1kc5q64)
COOKTOP_DPS = {
    101: "user_device_power_switch",    # Main power on/off
    102: "user_device_pause_switch",    # Start/Pause
    103: "user_device_lock_switch",     # Child lock
    104: "user_device_cur_max_level",   # Max power level (0-25)
    105: "oem_hob_error_num",           # Error codes (raw bitfield)
    106: "oem_device_chef_level",       # Chef function levels (raw bitfield)
    107: "oem_hob_bbq_timer",           # BBQ timer (raw bitfield)
    108: "oem_device_confirm",          # Confirm action
    134: "oem_device_timer_num",        # General timer (0-99 min)
    145: "oem_device_old_people",       # Senior mode
    148: "oem_hob_1_quick_level",       # Zone 1 quick level (enum)
    149: "oem_hob_2_quick_level",       # Zone 2 quick level (enum)
    150: "oem_hob_3_quick_level",       # Zone 3 quick level (enum)
    151: "oem_hob_4_quick_level",       # Zone 4 quick level (enum)
    152: "oem_hob_5_quick_level",       # Zone 5 quick level (enum)
    153: "oem_device_save_level",       # Save zone level
    154: "oem_device_set_level",        # Set zone level
    155: "oem_device_power_limit",      # Power limit mode
    161: "oem_hob_selected_switch",     # Zone selection (raw bitfield)
    162: "oem_hob_level_num",           # Zone power levels (raw bitfield)
    163: "oem_hob_boost_switch",        # Boost per zone (raw bitfield)
    164: "oem_hob_warm_switch",         # Keep warm per zone (raw bitfield)
    165: "oem_hob_flex_switch",         # Flex zone (raw bitfield)
    166: "oem_hob_bbq_switch",          # BBQ mode (raw bitfield)
    167: "oem_hob_timer_num",           # Timer per zone (raw bitfield)
    168: "oem_hob_set_core_sensor",     # Core temp sensor (raw bitfield)
    169: "oem_hob_disp_coresensor",     # Display core temp (raw bitfield)
}

# Quick level presets
QUICK_LEVELS = [
    "set_quick_level_1",
    "set_quick_level_2",
    "set_quick_level_3",
    "set_quick_level_4",
    "set_quick_level_5",
]

# CENTRAL DEVICE DATABASE - Single source of truth for all devices
# Add new devices only here!
KNOWN_DEVICES = {
    # HERMES & STYLE Hood - Corrected based on actual data model
    "hermes_style_hood": {
        "model_id": "e1k6i0zo",
        "category": CATEGORY_HOOD,
        "name": "HERMES & STYLE Hood",
        "product_names": ["ypaixllljc2dcpae"],
        "device_ids": ["bf735dfe2ad64fba7cpyhn"],
        "device_id_patterns": ["bf735dfe2ad64fba7c"],
        "platforms": ["fan", "light", "switch", "sensor", "select", "number"],
        "data_points": {
            # Active DPs (verified working)
            1: "switch",              # Main power
            4: "light",               # Light on/off
            6: "switch_lamp",         # Filter cleaning reminder
            10: "fan_speed_enum",     # Fan speed
            13: "countdown",          # Timer
            101: "RGB",               # RGB lighting modes
            # Experimental DPs (from API v2.0 Things Data Model, disabled by default)
            2: "delay_switch",        # Delayed shutdown (afterrun)
            5: "light_brightness",    # Light brightness (0-255)
            14: "filter_hours",       # Filter usage hours
            15: "filter_reset",       # Reset filter counter
            17: "eco_mode",           # Eco mode
            102: "rgb_brightness",    # RGB brightness (0-255)
            103: "color_temp"         # Color temperature
        },
        "entities": {
            "fan": {
                "dp": 10,  # fan_speed_enum - used for HomeKit/Siri integration
                "speeds": ["off", "low", "middle", "high", "strong"]
            },
            "light": [
                # Main light with RGB color effects for HomeKit/Siri
                {
                    "dp": 4,
                    "name": "Light",
                    "icon": "mdi:lightbulb",
                    "effect_dp": 101,
                    "effect_numeric": True,
                    "effect_offset": 1,  # Device uses 0=off, 1=Weiß, 2=Rot, etc.
                    "effects": ["Weiß", "Rot", "Grün", "Blau", "Gelb", "Lila", "Orange", "Cyan", "Grasgrün"]
                }
            ],
            "switch": [
                {"dp": 1, "name": "Power", "device_class": "switch", "icon": "mdi:power"},
                {"dp": 6, "name": "Filter Cleaning Reminder", "icon": "mdi:air-filter", "advanced": True, "entity_category": "diagnostic"},
                # Experimental switches
                {"dp": 2, "name": "Delayed Shutdown", "icon": "mdi:timer-off", "advanced": True, "entity_category": "config"},
                {"dp": 17, "name": "Eco Mode", "icon": "mdi:leaf", "advanced": True, "entity_category": "config"}
            ],
            "number": [
                # RGB Mode as number (backup, advanced) - use Light effects instead
                {"dp": 101, "name": "RGB Mode", "min": 0, "max": 8, "step": 1, "icon": "mdi:palette", "advanced": True, "entity_category": "config"},
                {"dp": 13, "name": "Timer", "min": 0, "max": 60, "unit": UnitOfTime.MINUTES, "device_class": "duration", "icon": "mdi:timer"},
                # Experimental numbers
                {"dp": 5, "name": "Light Brightness", "min": 0, "max": 255, "step": 1, "icon": "mdi:brightness-6", "advanced": True},
                {"dp": 102, "name": "RGB Brightness", "min": 0, "max": 255, "step": 1, "icon": "mdi:brightness-5", "advanced": True}
            ],
            "sensor": [
                {"dp": 6, "name": "Filter Status", "icon": "mdi:air-filter", "advanced": True, "entity_category": "diagnostic"},
                # Experimental sensors
                {"dp": 14, "name": "Filter Hours", "unit": "h", "device_class": "duration", "icon": "mdi:clock-outline", "advanced": True, "entity_category": "diagnostic"}
            ],
            "select": [
                # RGB Mode select - maps numeric values 0-8 to color names
                {
                    "dp": 101,
                    "name": "RGB Mode",
                    "options": ["Aus", "Weiß", "Rot", "Grün", "Blau", "Gelb", "Lila", "Orange", "Cyan", "Grasgrün"],
                    "options_map": {"Aus": 0, "Weiß": 1, "Rot": 2, "Grün": 3, "Blau": 4, "Gelb": 5, "Lila": 6, "Orange": 7, "Cyan": 8, "Grasgrün": 9},
                    "icon": "mdi:palette"
                },
                # Fan Speed select marked as advanced to avoid HomeKit showing both fan and select
                {"dp": 10, "name": "Fan Speed", "options": ["off", "low", "middle", "high", "strong"], "icon": "mdi:fan", "advanced": True, "entity_category": "config"},
                # Experimental select
                {"dp": 103, "name": "Color Temperature", "options": ["warm", "neutral", "cold"], "icon": "mdi:thermometer", "advanced": True}
            ]
        }
    },

    # KKT Kolbe FLAT Hood - Simplified version without RGB lighting
    "flat_hood": {
        "model_id": "luoxakxm2vm9azwu",
        "category": CATEGORY_HOOD,
        "name": "KKT Kolbe FLAT Hood",
        "product_names": ["luoxakxm2vm9azwu", "KKT Kolbe FLAT"],
        "device_ids": ["bff904d332b57484da1twc"],
        "device_id_patterns": ["bff904d332b57484da"],
        "platforms": ["fan", "light", "switch", "sensor", "select", "number"],
        "data_points": {
            1: "switch",              # Main power
            4: "light",               # Light on/off (no RGB)
            6: "switch_lamp",         # Filter cleaning reminder
            10: "fan_speed_enum",     # Fan speed
            13: "countdown"           # Timer
        },
        "entities": {
            "fan": {
                "dp": 10,  # fan_speed_enum includes "off" state
                "speeds": ["off", "low", "middle", "high", "strong"]
            },
            "light": [
                # Main light as light entity for HomeKit/Siri
                {"dp": 4, "name": "Light", "icon": "mdi:lightbulb"}
            ],
            "switch": [
                {"dp": 1, "name": "Power", "device_class": "switch", "icon": "mdi:power"},
                {"dp": 6, "name": "Filter Cleaning Reminder", "icon": "mdi:air-filter", "advanced": True, "entity_category": "diagnostic"}
            ],
            "number": [
                {"dp": 13, "name": "Timer", "min": 0, "max": 60, "unit": UnitOfTime.MINUTES, "device_class": "duration", "icon": "mdi:timer"}
            ],
            "select": [
                # Fan Speed select marked as advanced to avoid HomeKit showing both fan and select
                {"dp": 10, "name": "Fan Speed", "options": ["off", "low", "middle", "high", "strong"], "advanced": True, "entity_category": "config"}
            ],
            "sensor": [
                {"dp": 6, "name": "Filter Status", "icon": "mdi:air-filter", "advanced": True, "entity_category": "diagnostic"}
            ]
        }
    },

    # KKT HERMES Hood (Schwestermodell ohne "& Style")
    "hermes_hood": {
        "model_id": "0fcj8kha86svfmve",
        "category": CATEGORY_HOOD,
        "name": "KKT HERMES Hood",
        "product_names": ["0fcj8kha86svfmve", "KKT Kolbe HERMES"],
        "device_ids": [],  # Will be filled when users report
        "device_id_patterns": [],
        "platforms": ["fan", "light", "switch", "sensor", "select", "number"],
        "data_points": HOOD_DPS,
        "entities": {
            "fan": {
                "dp": 10,  # fan_speed_enum
                "speeds": ["off", "low", "middle", "high", "strong"]
            },
            "light": [
                # Main light with RGB color effects for HomeKit/Siri
                {
                    "dp": 4,
                    "name": "Light",
                    "icon": "mdi:lightbulb",
                    "effect_dp": 101,
                    "effect_numeric": True,
                    "effect_offset": 1,  # Device uses 0=off, 1=Weiß, 2=Rot, etc.
                    "effects": ["Weiß", "Rot", "Grün", "Blau", "Gelb", "Lila", "Orange", "Cyan", "Grasgrün"]
                }
            ],
            "switch": [
                {"dp": 1, "name": "Power", "device_class": "switch", "icon": "mdi:power"},
                {"dp": 6, "name": "Filter Cleaning Reminder", "icon": "mdi:air-filter", "advanced": True, "entity_category": "diagnostic"}
            ],
            "select": [
                # Fan Speed select marked as advanced to avoid HomeKit showing both fan and select
                {"dp": 10, "name": "Fan Speed", "options": ["off", "low", "middle", "high", "strong"], "advanced": True, "entity_category": "config"}
            ],
            "number": [
                # RGB Mode as number (backup, advanced) - use Light effects instead
                {"dp": 101, "name": "RGB Mode", "min": 0, "max": 8, "step": 1, "icon": "mdi:palette", "advanced": True, "entity_category": "config"},
                {"dp": 13, "name": "Timer", "min": 0, "max": 60, "unit": UnitOfTime.MINUTES, "device_class": "duration", "icon": "mdi:timer"}
            ],
            "sensor": [
                {"dp": 6, "name": "Filter Status", "icon": "mdi:air-filter", "advanced": True, "entity_category": "diagnostic"}
            ]
        }
    },

    # KKT Kolbe SOLO HCM Hood - Based on ECCO HCM structure (verified via Things Data Model)
    # Model ID: edjszs (similar to ECCO HCM edjsx0)
    # Features: 9 fan speeds (0-9), RGB lighting, dual filter monitoring, timer
    # Note: Some units respond to DP 4 for light, others to DP 104 - both are exposed
    "solo_hcm_hood": {
        "model_id": "edjszs",
        "category": CATEGORY_HOOD,
        "name": "KKT Kolbe SOLO HCM Hood",
        "product_names": ["bgvbvjwomgbisd8x", "KKT Kolbe SOLO HCM"],
        "device_ids": ["bf34515c4ab6ec7f9axqy8"],
        "device_id_patterns": ["bf34515c4ab6ec7f9a"],
        "platforms": ["fan", "light", "switch", "select", "number"],
        "data_points": {
            1: "switch",              # Main power (ON/OFF)
            4: "light",               # Main light on/off
            6: "switch_lamp",         # RGB switch trigger
            7: "switch_wash",         # Setting/Wash mode
            102: "fan_speed",         # Fan speed (0-9)
            103: "day",               # Carbon filter days remaining (0-250)
            104: "switch_led_1",      # LED light (alternative to DP 4)
            105: "countdown_1",       # Countdown timer (0-60 min)
            106: "switch_led",        # Confirm
            107: "colour_data",       # RGB color data (string, max 255)
            108: "work_mode",         # RGB work mode (white/colour/scene/music)
            109: "day_1",             # Metal filter days remaining (0-40)
        },
        "entities": {
            "fan": {
                "dp": 102,  # fan_speed numeric (0-9) - for HomeKit/Siri
                "speeds": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
                "numeric": True,  # Use numeric mode instead of enum
                "min": 0,
                "max": 9
            },
            "light": [
                # Main light with RGB mode effects for HomeKit/Siri
                # Auto-Work-Mode: Sets work_mode to "white" before turning on light
                {
                    "dp": 4,
                    "name": "Light",
                    "icon": "mdi:lightbulb",
                    "effect_dp": 108,
                    "effect_numeric": False,
                    "effects": ["white", "colour", "scene", "music"],
                    "work_mode_dp": 108,
                    "work_mode_default": "white"
                },
                # LED Light as alternative (some SOLO HCM units respond to DP 104 instead of DP 4)
                # Auto-Work-Mode: Sets work_mode to "white" before turning on light
                {
                    "dp": 104,
                    "name": "LED Light",
                    "icon": "mdi:led-strip",
                    "work_mode_dp": 108,
                    "work_mode_default": "white"
                }
            ],
            "switch": [
                {"dp": 1, "name": "Power", "device_class": "switch", "icon": "mdi:power"},
                # RGB light as switch
                {"dp": 6, "name": "RGB Light", "device_class": "switch", "icon": "mdi:palette", "advanced": True, "entity_category": "config"},
                {"dp": 7, "name": "Wash Mode", "device_class": "switch", "icon": "mdi:spray-bottle", "advanced": True, "entity_category": "config"},
                {"dp": 106, "name": "Confirm", "device_class": "switch", "icon": "mdi:check", "entity_category": "config", "advanced": True}
            ],
            "select": [
                # RGB Mode as select (backup, advanced) - use Light effects instead
                {"dp": 108, "name": "RGB Mode", "options": ["white", "colour", "scene", "music"], "icon": "mdi:palette", "advanced": True, "entity_category": "config"}
            ],
            "number": [
                # Fan Speed number marked as advanced to avoid HomeKit showing both fan and number
                {"dp": 102, "name": "Fan Speed", "min": 0, "max": 9, "step": 1, "icon": "mdi:fan", "advanced": True, "entity_category": "config"},
                {"dp": 105, "name": "Timer", "min": 0, "max": 60, "unit": UnitOfTime.MINUTES, "device_class": "duration", "icon": "mdi:timer"},
                {"dp": 103, "name": "Carbon Filter Remaining", "min": 0, "max": 250, "unit": "days", "icon": "mdi:air-filter", "entity_category": "diagnostic"},
                {"dp": 109, "name": "Metal Filter Remaining", "min": 0, "max": 40, "unit": "days", "icon": "mdi:air-filter", "entity_category": "diagnostic"}
            ]
        }
    },

    # KKT Kolbe ECCO HCM Hood
    "ecco_hcm_hood": {
        "model_id": "edjsx0",
        "category": CATEGORY_HOOD,
        "name": "KKT Kolbe ECCO HCM Hood",
        "product_names": ["gwdgkteknzvsattn"],
        "device_ids": ["bfd0c94cb36bf4f28epxcf"],
        "device_id_patterns": ["bfd0c94cb36bf4f28e"],
        "platforms": ["fan", "light", "switch", "sensor", "select", "number"],
        "data_points": {
            1: "switch",              # Main power
            4: "light",              # Main light on/off
            6: "switch_lamp",        # RGB switch trigger
            7: "switch_wash",        # Setting/Wash mode
            102: "fan_speed",        # Fan speed (0-9)
            103: "day",              # Carbon filter days (0-250)
            104: "switch_led_1",     # LED light
            105: "countdown_1",      # Countdown timer (0-60 min)
            106: "switch_led",       # Confirm
            107: "colour_data",      # RGB color data (string)
            108: "work_mode",        # RGB work mode (white/colour/scene/music)
            109: "day_1",            # Metal filter days (0-40)
        },
        "entities": {
            "fan": {
                "dp": 102,  # fan_speed numeric (0-9) - for HomeKit/Siri
                "speeds": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
                "numeric": True,  # Use numeric mode instead of enum
                "min": 0,
                "max": 9
            },
            "light": [
                # Main light with RGB mode effects for HomeKit/Siri
                # Auto-Work-Mode: Sets work_mode to "white" before turning on light
                {
                    "dp": 4,
                    "name": "Light",
                    "icon": "mdi:lightbulb",
                    "effect_dp": 108,
                    "effect_numeric": False,
                    "effects": ["white", "colour", "scene", "music"],
                    "work_mode_dp": 108,
                    "work_mode_default": "white"
                },
                # LED Light as alternative (some units respond to DP 104 instead of DP 4)
                # Auto-Work-Mode: Sets work_mode to "white" before turning on light
                {
                    "dp": 104,
                    "name": "LED Light",
                    "icon": "mdi:led-strip",
                    "work_mode_dp": 108,
                    "work_mode_default": "white"
                }
            ],
            "switch": [
                {"dp": 1, "name": "Power", "device_class": "switch", "icon": "mdi:power"},
                # RGB light as switch (use main Light entity for Siri)
                {"dp": 6, "name": "RGB Light", "device_class": "switch", "icon": "mdi:palette", "advanced": True, "entity_category": "config"},
                {"dp": 7, "name": "Wash Mode", "device_class": "switch", "icon": "mdi:spray-bottle", "advanced": True, "entity_category": "config"},
                {"dp": 106, "name": "Confirm", "device_class": "switch", "icon": "mdi:check", "entity_category": "config", "advanced": True}
            ],
            "select": [
                # RGB Mode as select (backup, advanced) - use Light effects instead
                {"dp": 108, "name": "RGB Mode", "options": ["white", "colour", "scene", "music"], "icon": "mdi:palette", "advanced": True, "entity_category": "config"}
            ],
            "number": [
                # Fan Speed number marked as advanced to avoid HomeKit showing both fan and number
                {"dp": 102, "name": "Fan Speed", "min": 0, "max": 9, "step": 1, "icon": "mdi:fan", "advanced": True, "entity_category": "config"},
                {"dp": 105, "name": "Timer", "min": 0, "max": 60, "unit": UnitOfTime.MINUTES, "device_class": "duration", "icon": "mdi:timer"},
                {"dp": 103, "name": "Carbon Filter Remaining", "min": 0, "max": 250, "unit": "days", "icon": "mdi:air-filter", "advanced": True, "entity_category": "diagnostic"},
                {"dp": 109, "name": "Metal Filter Remaining", "min": 0, "max": 40, "unit": "days", "icon": "mdi:air-filter", "advanced": True, "entity_category": "diagnostic"}
            ],
            "sensor": [
            ]
        }
    },

    # DEFAULT HOOD HERMES - Based on HERMES family for manual selection
    # Uses HERMES DPs with enum fan speed (off/low/middle/high/strong)
    "default_hood_hermes": {
        "model_id": "default_hood_hermes",
        "category": CATEGORY_HOOD,
        "name": "Default Hood (HERMES-based)",
        "product_names": ["default_hood_hermes"],
        "device_ids": [],
        "device_id_patterns": [],
        "platforms": ["fan", "light", "switch", "sensor", "select", "number"],
        "data_points": {
            1: "switch",              # Main power
            4: "light",               # Light on/off
            6: "switch_lamp",         # Filter cleaning reminder
            10: "fan_speed_enum",     # Fan speed (enum)
            13: "countdown",          # Timer
            101: "RGB",               # RGB lighting modes (0-8)
            2: "delay_switch",        # Delayed shutdown
            5: "light_brightness",    # Light brightness (0-255)
            14: "filter_hours",       # Filter usage hours
            17: "eco_mode",           # Eco mode
        },
        "entities": {
            "fan": {
                "dp": 10,  # fan_speed_enum
                "speeds": ["off", "low", "middle", "high", "strong"]
            },
            "light": [
                {
                    "dp": 4,
                    "name": "Light",
                    "icon": "mdi:lightbulb",
                    "effect_dp": 101,
                    "effect_numeric": True,
                    "effect_offset": 1,  # Device uses 0=off, 1=Weiß, 2=Rot, etc.
                    "effects": ["Weiß", "Rot", "Grün", "Blau", "Gelb", "Lila", "Orange", "Cyan", "Grasgrün"]
                }
            ],
            "switch": [
                {"dp": 1, "name": "Power", "device_class": "switch", "icon": "mdi:power"},
                {"dp": 6, "name": "Filter Cleaning Reminder", "icon": "mdi:air-filter", "advanced": True, "entity_category": "diagnostic"},
                {"dp": 2, "name": "Delayed Shutdown", "icon": "mdi:timer-off", "advanced": True, "entity_category": "config"},
                {"dp": 17, "name": "Eco Mode", "icon": "mdi:leaf", "advanced": True, "entity_category": "config"}
            ],
            "number": [
                {"dp": 101, "name": "RGB Mode", "min": 0, "max": 8, "step": 1, "icon": "mdi:palette", "advanced": True, "entity_category": "config"},
                {"dp": 13, "name": "Timer", "min": 0, "max": 60, "unit": UnitOfTime.MINUTES, "device_class": "duration", "icon": "mdi:timer"},
                {"dp": 5, "name": "Light Brightness", "min": 0, "max": 255, "step": 1, "icon": "mdi:brightness-6", "advanced": True}
            ],
            "sensor": [
                {"dp": 6, "name": "Filter Status", "icon": "mdi:air-filter", "advanced": True, "entity_category": "diagnostic"},
                {"dp": 14, "name": "Filter Hours", "unit": "h", "device_class": "duration", "icon": "mdi:clock-outline", "advanced": True, "entity_category": "diagnostic"}
            ],
            "select": [
                {"dp": 10, "name": "Fan Speed", "options": ["off", "low", "middle", "high", "strong"], "icon": "mdi:fan", "advanced": True, "entity_category": "config"}
            ]
        }
    },

    # DEFAULT HOOD HCM - Based on HCM family (SOLO/ECCO) as fallback
    # Uses HCM DPs which are the most complete configuration
    "default_hood": {
        "model_id": "default_hood",
        "category": CATEGORY_HOOD,
        "name": "Default Hood (HCM-based)",
        "product_names": ["default_hood"],
        "device_ids": [],  # Matches any device when selected manually
        "device_id_patterns": [],
        "platforms": ["fan", "light", "switch", "select", "number"],
        "data_points": {
            1: "switch",              # Main power (ON/OFF)
            4: "light",               # Main light on/off
            6: "switch_lamp",         # RGB switch trigger
            7: "switch_wash",         # Setting/Wash mode
            102: "fan_speed",         # Fan speed (0-9)
            103: "day",               # Carbon filter days remaining (0-250)
            104: "switch_led_1",      # LED light
            105: "countdown_1",       # Countdown timer (0-60 min)
            106: "switch_led",        # Confirm
            107: "colour_data",       # RGB color data (string, max 255)
            108: "work_mode",         # RGB work mode (white/colour/scene/music)
            109: "day_1",             # Metal filter days remaining (0-40)
        },
        "entities": {
            "fan": {
                "dp": 102,  # fan_speed numeric (0-9) - for HomeKit/Siri
                "speeds": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
                "numeric": True,  # Use numeric mode instead of enum
                "min": 0,
                "max": 9
            },
            "light": [
                # Main light with RGB mode effects for HomeKit/Siri
                {
                    "dp": 4,
                    "name": "Light",
                    "icon": "mdi:lightbulb",
                    "effect_dp": 108,
                    "effect_numeric": False,
                    "effects": ["white", "colour", "scene", "music"]
                }
            ],
            "switch": [
                {"dp": 1, "name": "Power", "device_class": "switch", "icon": "mdi:power"},
                {"dp": 6, "name": "RGB Light", "device_class": "switch", "icon": "mdi:palette", "advanced": True, "entity_category": "config"},
                {"dp": 7, "name": "Wash Mode", "device_class": "switch", "icon": "mdi:spray-bottle", "advanced": True, "entity_category": "config"},
                {"dp": 104, "name": "LED Light", "device_class": "switch", "icon": "mdi:led-strip", "advanced": True, "entity_category": "config"},
                {"dp": 106, "name": "Confirm", "device_class": "switch", "icon": "mdi:check", "entity_category": "config", "advanced": True}
            ],
            "select": [
                {"dp": 108, "name": "RGB Mode", "options": ["white", "colour", "scene", "music"], "icon": "mdi:palette", "advanced": True, "entity_category": "config"}
            ],
            "number": [
                {"dp": 102, "name": "Fan Speed", "min": 0, "max": 9, "step": 1, "icon": "mdi:fan", "advanced": True, "entity_category": "config"},
                {"dp": 105, "name": "Timer", "min": 0, "max": 60, "unit": UnitOfTime.MINUTES, "device_class": "duration", "icon": "mdi:timer"},
                {"dp": 103, "name": "Carbon Filter Remaining", "min": 0, "max": 250, "unit": "days", "icon": "mdi:air-filter", "entity_category": "diagnostic"},
                {"dp": 109, "name": "Metal Filter Remaining", "min": 0, "max": 40, "unit": "days", "icon": "mdi:air-filter", "entity_category": "diagnostic"}
            ]
        }
    },

    # IND7705HC Induction Cooktop - Complete configuration with bitfield decoding
    "ind7705hc_cooktop": {
        "model_id": "e1kc5q64",
        "category": CATEGORY_COOKTOP,
        "name": "IND7705HC Induction Cooktop",
        "product_names": ["p8volecsgzdyun29"],
        "device_ids": ["bf5592b47738c5b46evzff"],
        "device_id_patterns": ["bf5592b47738c5b46e"],
        "platforms": ["switch", "number", "sensor", "binary_sensor", "select"],
        "data_points": COOKTOP_DPS,
        "entities": {
            "switch": [
                {"dp": 101, "name": "Power", "device_class": "switch", "icon": "mdi:power"},
                {"dp": 102, "name": "Pause", "device_class": "switch", "icon": "mdi:pause"},
                {"dp": 103, "name": "Child Lock", "device_class": "switch", "icon": "mdi:lock", "entity_category": "diagnostic"},
                {"dp": 145, "name": "Senior Mode", "device_class": "switch", "icon": "mdi:account-supervisor", "entity_category": "diagnostic"},
                {"dp": 108, "name": "Confirm Action", "device_class": "switch", "entity_category": "config", "icon": "mdi:check"}
            ],
            "number": [
                # Global controls
                {"dp": 104, "name": "Max Power Level", "min": 0, "max": 25, "mode": "slider", "icon": "mdi:flash"},
                {"dp": 134, "name": "General Timer", "min": 0, "max": 99, "unit_of_measurement": UnitOfTime.MINUTES, "device_class": "duration", "mode": "slider", "icon": "mdi:timer"},

                # Zone-specific controls (bitfield-decoded)
                {"dp": 162, "name": "Zone 1: Power Level", "min": 0, "max": 25, "zone": 1, "mode": "slider", "icon": "mdi:numeric-1-circle"},
                {"dp": 162, "name": "Zone 2: Power Level", "min": 0, "max": 25, "zone": 2, "mode": "slider", "icon": "mdi:numeric-2-circle"},
                {"dp": 162, "name": "Zone 3: Power Level", "min": 0, "max": 25, "zone": 3, "mode": "slider", "icon": "mdi:numeric-3-circle"},
                {"dp": 162, "name": "Zone 4: Power Level", "min": 0, "max": 25, "zone": 4, "mode": "slider", "icon": "mdi:numeric-4-circle"},
                {"dp": 162, "name": "Zone 5: Power Level", "min": 0, "max": 25, "zone": 5, "mode": "slider", "icon": "mdi:numeric-5-circle"},

                {"dp": 167, "name": "Zone 1: Timer", "min": 0, "max": 255, "unit_of_measurement": UnitOfTime.MINUTES, "device_class": "duration", "zone": 1, "mode": "slider", "icon": "mdi:timer-outline", "advanced": True},
                {"dp": 167, "name": "Zone 2: Timer", "min": 0, "max": 255, "unit_of_measurement": UnitOfTime.MINUTES, "device_class": "duration", "zone": 2, "mode": "slider", "icon": "mdi:timer-outline", "advanced": True},
                {"dp": 167, "name": "Zone 3: Timer", "min": 0, "max": 255, "unit_of_measurement": UnitOfTime.MINUTES, "device_class": "duration", "zone": 3, "mode": "slider", "icon": "mdi:timer-outline", "advanced": True},
                {"dp": 167, "name": "Zone 4: Timer", "min": 0, "max": 255, "unit_of_measurement": UnitOfTime.MINUTES, "device_class": "duration", "zone": 4, "mode": "slider", "icon": "mdi:timer-outline", "advanced": True},
                {"dp": 167, "name": "Zone 5: Timer", "min": 0, "max": 255, "unit_of_measurement": UnitOfTime.MINUTES, "device_class": "duration", "zone": 5, "mode": "slider", "icon": "mdi:timer-outline", "advanced": True},

                {"dp": 168, "name": "Zone 1: Target Temp", "min": 0, "max": 300, "unit_of_measurement": UnitOfTemperature.CELSIUS, "device_class": "temperature", "zone": 1, "mode": "slider", "icon": "mdi:thermometer", "advanced": True},
                {"dp": 168, "name": "Zone 2: Target Temp", "min": 0, "max": 300, "unit_of_measurement": UnitOfTemperature.CELSIUS, "device_class": "temperature", "zone": 2, "mode": "slider", "icon": "mdi:thermometer", "advanced": True},
                {"dp": 168, "name": "Zone 3: Target Temp", "min": 0, "max": 300, "unit_of_measurement": UnitOfTemperature.CELSIUS, "device_class": "temperature", "zone": 3, "mode": "slider", "icon": "mdi:thermometer", "advanced": True},
                {"dp": 168, "name": "Zone 4: Target Temp", "min": 0, "max": 300, "unit_of_measurement": UnitOfTemperature.CELSIUS, "device_class": "temperature", "zone": 4, "mode": "slider", "icon": "mdi:thermometer", "advanced": True},
                {"dp": 168, "name": "Zone 5: Target Temp", "min": 0, "max": 300, "unit_of_measurement": UnitOfTemperature.CELSIUS, "device_class": "temperature", "zone": 5, "mode": "slider", "icon": "mdi:thermometer", "advanced": True}
            ],
            "select": [
                {"dp": 148, "name": "Zone 1: Quick Level", "options": QUICK_LEVELS, "icon": "mdi:numeric-1-circle-outline", "advanced": True},
                {"dp": 149, "name": "Zone 2: Quick Level", "options": QUICK_LEVELS, "icon": "mdi:numeric-2-circle-outline", "advanced": True},
                {"dp": 150, "name": "Zone 3: Quick Level", "options": QUICK_LEVELS, "icon": "mdi:numeric-3-circle-outline", "advanced": True},
                {"dp": 151, "name": "Zone 4: Quick Level", "options": QUICK_LEVELS, "icon": "mdi:numeric-4-circle-outline", "advanced": True},
                {"dp": 152, "name": "Zone 5: Quick Level", "options": QUICK_LEVELS, "icon": "mdi:numeric-5-circle-outline", "advanced": True},
                {"dp": 153, "name": "Save Zone Level", "options": ["save_hob1", "save_hob2", "save_hob3", "save_hob4", "save_hob5"], "entity_category": "config", "icon": "mdi:content-save"},
                {"dp": 154, "name": "Set Zone Level", "options": ["set_hob1", "set_hob2", "set_hob3", "set_hob4", "set_hob5"], "entity_category": "config", "icon": "mdi:cog"},
                {"dp": 155, "name": "Power Limit", "options": ["power_limit_1", "power_limit_2", "power_limit_3", "power_limit_4", "power_limit_5"], "icon": "mdi:flash-triangle"}
            ],
            "sensor": [
                # === CALCULATED SENSORS (für Automationen) ===
                # Geschätzter Stromverbrauch basierend auf Zonen-Levels (~100W pro Level)
                {
                    "dp": 162,
                    "name": "Estimated Power",
                    "sensor_type": "calculated_power",
                    "zones_dp": 162,
                    "num_zones": 5,
                    "watts_per_level": 100,
                    "icon": "mdi:lightning-bolt"
                },
                # Summe aller Zonen-Levels (0-125)
                {
                    "dp": 162,
                    "name": "Total Power Level",
                    "sensor_type": "total_level",
                    "zones_dp": 162,
                    "num_zones": 5,
                    "icon": "mdi:gauge"
                },
                # Anzahl aktiver Zonen (0-5)
                {
                    "dp": 162,
                    "name": "Active Zones",
                    "sensor_type": "active_zones",
                    "zones_dp": 162,
                    "num_zones": 5,
                    "icon": "mdi:stove"
                },

                # === ZONE TEMPERATURE SENSORS (bitfield-decoded) ===
                {"dp": 169, "name": "Zone 1: Current Temp", "unit_of_measurement": UnitOfTemperature.CELSIUS, "device_class": "temperature", "zone": 1, "icon": "mdi:thermometer"},
                {"dp": 169, "name": "Zone 2: Current Temp", "unit_of_measurement": UnitOfTemperature.CELSIUS, "device_class": "temperature", "zone": 2, "icon": "mdi:thermometer"},
                {"dp": 169, "name": "Zone 3: Current Temp", "unit_of_measurement": UnitOfTemperature.CELSIUS, "device_class": "temperature", "zone": 3, "icon": "mdi:thermometer"},
                {"dp": 169, "name": "Zone 4: Current Temp", "unit_of_measurement": UnitOfTemperature.CELSIUS, "device_class": "temperature", "zone": 4, "icon": "mdi:thermometer"},
                {"dp": 169, "name": "Zone 5: Current Temp", "unit_of_measurement": UnitOfTemperature.CELSIUS, "device_class": "temperature", "zone": 5, "icon": "mdi:thermometer"}
            ],
            "binary_sensor": [
                # Zone error status (bitfield-decoded) - Diagnostic
                {"dp": 105, "name": "Zone 1: Error", "device_class": "problem", "zone": 1, "icon": "mdi:alert-circle", "entity_category": "diagnostic"},
                {"dp": 105, "name": "Zone 2: Error", "device_class": "problem", "zone": 2, "icon": "mdi:alert-circle", "entity_category": "diagnostic"},
                {"dp": 105, "name": "Zone 3: Error", "device_class": "problem", "zone": 3, "icon": "mdi:alert-circle", "entity_category": "diagnostic"},
                {"dp": 105, "name": "Zone 4: Error", "device_class": "problem", "zone": 4, "icon": "mdi:alert-circle", "entity_category": "diagnostic"},
                {"dp": 105, "name": "Zone 5: Error", "device_class": "problem", "zone": 5, "icon": "mdi:alert-circle", "entity_category": "diagnostic"},

                # Zone selection status (bitfield-decoded) - Diagnostic
                {"dp": 161, "name": "Zone 1: Selected", "device_class": "running", "zone": 1, "icon": "mdi:radiobox-marked", "entity_category": "diagnostic"},
                {"dp": 161, "name": "Zone 2: Selected", "device_class": "running", "zone": 2, "icon": "mdi:radiobox-marked", "entity_category": "diagnostic"},
                {"dp": 161, "name": "Zone 3: Selected", "device_class": "running", "zone": 3, "icon": "mdi:radiobox-marked", "entity_category": "diagnostic"},
                {"dp": 161, "name": "Zone 4: Selected", "device_class": "running", "zone": 4, "icon": "mdi:radiobox-marked", "entity_category": "diagnostic"},
                {"dp": 161, "name": "Zone 5: Selected", "device_class": "running", "zone": 5, "icon": "mdi:radiobox-marked", "entity_category": "diagnostic"},

                # Zone boost status (bitfield-decoded)
                {"dp": 163, "name": "Zone 1: Boost Active", "device_class": "running", "zone": 1, "icon": "mdi:flash"},
                {"dp": 163, "name": "Zone 2: Boost Active", "device_class": "running", "zone": 2, "icon": "mdi:flash"},
                {"dp": 163, "name": "Zone 3: Boost Active", "device_class": "running", "zone": 3, "icon": "mdi:flash"},
                {"dp": 163, "name": "Zone 4: Boost Active", "device_class": "running", "zone": 4, "icon": "mdi:flash"},
                {"dp": 163, "name": "Zone 5: Boost Active", "device_class": "running", "zone": 5, "icon": "mdi:flash"},

                # Zone keep warm status (bitfield-decoded)
                {"dp": 164, "name": "Zone 1: Keep Warm", "device_class": "running", "zone": 1, "icon": "mdi:thermometer-low"},
                {"dp": 164, "name": "Zone 2: Keep Warm", "device_class": "running", "zone": 2, "icon": "mdi:thermometer-low"},
                {"dp": 164, "name": "Zone 3: Keep Warm", "device_class": "running", "zone": 3, "icon": "mdi:thermometer-low"},
                {"dp": 164, "name": "Zone 4: Keep Warm", "device_class": "running", "zone": 4, "icon": "mdi:thermometer-low"},
                {"dp": 164, "name": "Zone 5: Keep Warm", "device_class": "running", "zone": 5, "icon": "mdi:thermometer-low"},

                # Flex zone controls (special zones) - Advanced
                {"dp": 165, "name": "Flex Zone Left", "device_class": "running", "zone": 1, "icon": "mdi:arrow-expand-horizontal", "advanced": True},
                {"dp": 165, "name": "Flex Zone Right", "device_class": "running", "zone": 2, "icon": "mdi:arrow-expand-horizontal", "advanced": True},

                # BBQ mode controls (special zones) - Advanced
                {"dp": 166, "name": "BBQ Mode Left", "device_class": "running", "zone": 1, "icon": "mdi:grill", "advanced": True},
                {"dp": 166, "name": "BBQ Mode Right", "device_class": "running", "zone": 2, "icon": "mdi:grill", "advanced": True}
            ]
        }
    }
}

def find_device_by_product_name(product_name: str) -> dict | None:
    """Find device in central database by product name."""
    for _device_key, device_info in KNOWN_DEVICES.items():
        if product_name in device_info["product_names"]:
            return device_info
    return None

def find_device_by_device_id(device_id: str) -> dict | None:
    """Find device in central database by device ID."""
    for _device_key, device_info in KNOWN_DEVICES.items():
        # Exact match
        if device_id in device_info["device_ids"]:
            return device_info
        # Pattern match
        for pattern in device_info["device_id_patterns"]:
            if isinstance(pattern, str) and device_id.startswith(pattern):
                return device_info
    return None

def get_device_dps(category: str) -> dict:
    """Get data points for device category."""
    if category == CATEGORY_HOOD:
        return HOOD_DPS
    elif category == CATEGORY_COOKTOP:
        return COOKTOP_DPS
    else:
        return {}

def get_device_info_by_device_id(device_id: str) -> dict | None:
    """Get device information based on device ID (for manual setup)."""
    device_info = find_device_by_device_id(device_id)
    if device_info:
        product_names = device_info["product_names"]
        return {
            "model_id": device_info["model_id"],
            "category": device_info["category"],
            "name": device_info["name"],
            "product_name": product_names[0] if isinstance(product_names, list) and product_names else ""
        }
    return None

def get_product_name_by_device_id(device_id: str) -> str | None:
    """Get product name by device ID - for automatic device type detection."""
    device_info = find_device_by_device_id(device_id)
    if device_info:
        product_names = device_info["product_names"]
        if isinstance(product_names, list) and product_names:
            return str(product_names[0])  # Return the primary product name
    return None

def auto_detect_device_config(device_id: str | None = None, provided_product_name: str | None = None) -> dict | None:
    """Auto-detect device configuration from available information."""
    detected_product_name = None

    # Method 1: Use provided product name if available
    if provided_product_name and provided_product_name.strip():
        device_info = find_device_by_product_name(provided_product_name.strip())
        if device_info:
            detected_product_name = provided_product_name.strip()

    # Method 2: Look up product name by device ID
    if not detected_product_name and device_id:
        detected_product_name = get_product_name_by_device_id(device_id)

    # Return configuration
    if detected_product_name:
        device_info = find_device_by_product_name(detected_product_name)
        if device_info:
            return {
                "product_name": detected_product_name,
                "category": device_info["category"],
                "name": device_info["name"],
                "platforms": device_info["platforms"],
                "detected_method": "product_name" if provided_product_name else "device_id"
            }

    return None

def get_device_info_by_product_name(product_name: str) -> dict:
    """Get device information based on product name from discovery.

    Supports multiple lookup methods:
    1. Device key lookup (e.g., "ind7705hc_cooktop", "hermes_style_hood")
    2. Tuya product ID lookup (e.g., "p8volecsgzdyun29")
    3. Pattern matching fallback
    """
    # Method 1: Check if product_name is a device key in KNOWN_DEVICES
    if product_name in KNOWN_DEVICES:
        device_info = KNOWN_DEVICES[product_name]
        return {
            "model_id": device_info["model_id"],
            "category": device_info["category"],
            "name": device_info["name"]
        }

    # Method 2: Check central database by Tuya product ID
    found_device_info = find_device_by_product_name(product_name)
    if found_device_info:
        return {
            "model_id": found_device_info["model_id"],
            "category": found_device_info["category"],
            "name": found_device_info["name"]
        }

    # Handle manual setup device types
    if product_name == "manual_hood":
        return {
            "model_id": "manual_hood",
            "category": CATEGORY_HOOD,
            "name": "KKT Hood (Manual Setup)"
        }
    elif product_name == "manual_cooktop":
        return {
            "model_id": "manual_cooktop",
            "category": CATEGORY_COOKTOP,
            "name": "KKT Cooktop (Manual Setup)"
        }
    elif product_name == "default_hood":
        # Default Hood - Generic range hood with standard DPs
        return {
            "model_id": "default_hood",
            "category": CATEGORY_HOOD,
            "name": "Default Hood (Generic)"
        }

    # Fallback: Try to detect by known patterns
    if "hermes" in product_name.lower() or "style" in product_name.lower():
        return {
            "model_id": "unknown_hood",
            "category": CATEGORY_HOOD,
            "name": f"KKT Hood ({product_name})"
        }
    elif "ind" in product_name.lower():
        return {
            "model_id": "unknown_cooktop",
            "category": CATEGORY_COOKTOP,
            "name": f"KKT Cooktop ({product_name})"
        }

    # Generic fallback
    return {
        "model_id": "unknown",
        "category": "unknown",
        "name": f"KKT Device ({product_name})"
    }

def get_device_platforms(category: str) -> list[str]:
    """Get required platforms for device category."""
    # Try to find specific device platforms first
    for _device_key, device_info in KNOWN_DEVICES.items():
        if device_info["category"] == category:
            platforms = device_info["platforms"]
            if isinstance(platforms, list):
                return platforms

    # Fallback to category-based platforms
    if category == CATEGORY_HOOD:
        return ["fan", "light", "switch", "sensor", "select", "number"]
    elif category == CATEGORY_COOKTOP:
        return ["switch", "number", "sensor", "binary_sensor"]
    else:
        # Generic fallback: Load all platforms for unknown devices
        # This ensures manual setup always works
        return ["fan", "light", "switch", "sensor", "select", "number", "binary_sensor"]

def get_device_platforms_by_product_name(product_name: str) -> list[str]:
    """Get platforms directly by product name (most efficient).

    Supports:
    1. Device key lookup (e.g., "ind7705hc_cooktop")
    2. Tuya product ID lookup (e.g., "p8volecsgzdyun29")
    """
    # Method 1: Check if product_name is a device key
    if product_name in KNOWN_DEVICES:
        platforms = KNOWN_DEVICES[product_name]["platforms"]
        if isinstance(platforms, list):
            return platforms

    # Method 2: Try Tuya product ID lookup
    device_info = find_device_by_product_name(product_name)
    if device_info:
        platforms = device_info["platforms"]
        if isinstance(platforms, list):
            return platforms

    # Fallback to category-based lookup
    device_type_info = get_device_info_by_product_name(product_name)
    category = device_type_info.get("category", "unknown") if isinstance(device_type_info, dict) else "unknown"
    return get_device_platforms(str(category))

def get_device_entities(product_name: str, platform: str) -> list:
    """Get entity configurations for a specific product and platform.

    Supports:
    1. Device key lookup (e.g., "ind7705hc_cooktop")
    2. Tuya product ID lookup (e.g., "p8volecsgzdyun29")
    """
    device_info = None

    # Method 1: Check if product_name is a device key
    if product_name in KNOWN_DEVICES:
        device_info = KNOWN_DEVICES[product_name]
    else:
        # Method 2: Try Tuya product ID lookup
        device_info = find_device_by_product_name(product_name)

    if device_info and "entities" in device_info:
        entities_config = device_info["entities"]
        if isinstance(entities_config, dict) and platform in entities_config:
            entity_config = entities_config[platform]
            # Handle both single entity (dict) and multiple entities (list)
            if isinstance(entity_config, dict):
                return [entity_config]
            elif isinstance(entity_config, list):
                return entity_config
    return []

def get_device_entity_config(product_name: str, platform: str) -> dict:
    """Get the first entity config for a platform (for single-entity platforms like fan, light)."""
    entities = get_device_entities(product_name, platform)
    return entities[0] if entities else {}

def get_known_device_choices() -> dict:
    """Get user-friendly device choices for manual setup."""
    choices = {}

    for device_key, device_info in KNOWN_DEVICES.items():
        # Create user-friendly name
        device_name = device_info["name"]
        choices[device_key] = device_name

    # Add fallback options
    choices.update({
        "generic_hood": "Hood (Generic)",
        "generic_cooktop": "Cooktop (Generic)",
        "unknown": "Device type not listed"
    })

    return choices

def get_product_name_from_device_choice(device_choice: str) -> str:
    """Convert user device choice to internal product name."""
    if device_choice in KNOWN_DEVICES:
        # Known specific device
        product_names = KNOWN_DEVICES[device_choice]["product_names"]
        if isinstance(product_names, list) and product_names:
            return str(product_names[0])
    if device_choice == "generic_hood":
        return "manual_hood"
    if device_choice == "generic_cooktop":
        return "manual_cooktop"
    return "unknown"
