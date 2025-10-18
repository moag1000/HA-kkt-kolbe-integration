"""Device type specific configurations for KKT Kolbe devices."""

from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfSoundPressure,
)

from .const import CATEGORY_HOOD, CATEGORY_COOKTOP


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
            1: "switch",              # Main power
            4: "light",               # Light on/off
            6: "switch_lamp",         # Filter cleaning reminder
            10: "fan_speed_enum",     # Fan speed
            13: "countdown",          # Timer
            101: "RGB"                # RGB lighting modes
        },
        "entities": {
            "fan": {
                "dp": 10,  # fan_speed_enum includes "off" state
                "speeds": ["off", "low", "middle", "high", "strong"]
            },
            "light": {
                "dp": 4,  # light on/off
                "rgb_dp": 101  # RGB mode (0-9)
            },
            "switch": [
                {"dp": 1, "name": "Power", "device_class": "outlet", "icon": "mdi:power"},
                {"dp": 6, "name": "Filter Cleaning Reminder", "device_class": "switch"}
            ],
            "sensor": [
                {"dp": 10, "name": "Fan Speed", "device_class": "enum", "options": ["off", "low", "middle", "high", "strong"]},
                {"dp": 6, "name": "Filter Status", "device_class": "problem"}
            ],
            "number": [
                {"dp": 13, "name": "Timer", "min": 0, "max": 60, "unit": UnitOfTime.MINUTES},
                {"dp": 101, "name": "RGB Mode", "min": 0, "max": 9, "step": 1}
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
        "platforms": ["fan", "light", "switch", "sensor", "number"],
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
            "light": {
                "dp": 4  # light on/off only (no RGB support)
            },
            "switch": [
                {"dp": 1, "name": "Power", "device_class": "outlet", "icon": "mdi:power"},
                {"dp": 6, "name": "Filter Cleaning Reminder", "device_class": "switch"}
            ],
            "sensor": [
                {"dp": 10, "name": "Fan Speed", "device_class": "enum", "options": ["off", "low", "middle", "high", "strong"]},
                {"dp": 6, "name": "Filter Status", "device_class": "problem"}
            ],
            "number": [
                {"dp": 13, "name": "Timer", "min": 0, "max": 60, "unit": UnitOfTime.MINUTES}
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
            "light": {
                "dp": 4,  # light on/off
                "brightness_dp": 5,  # light brightness
                "rgb_dp": 101,  # RGB mode
                "rgb_brightness_dp": 102  # RGB brightness
            },
            "switch": [
                {"dp": 1, "name": "Power", "device_class": "switch"},
                {"dp": 2, "name": "Delay Shutdown", "device_class": "switch"},
                {"dp": 3, "name": "Auto Mode", "device_class": "switch"},
                {"dp": 6, "name": "Filter Reminder", "device_class": "switch"},
                {"dp": 12, "name": "Auto Clean", "device_class": "switch"},
                {"dp": 15, "name": "Filter Reset", "device_class": "switch"},
                {"dp": 17, "name": "Eco Mode", "device_class": "switch"}
            ],
            "sensor": [
                {"dp": 6, "name": "Filter Status", "device_class": "problem"},
                {"dp": 7, "name": "Temperature", "unit": UnitOfTemperature.CELSIUS, "device_class": "temperature"},
                {"dp": 8, "name": "Humidity", "unit": PERCENTAGE, "device_class": "humidity"},
                {"dp": 9, "name": "Air Quality", "device_class": "aqi"},
                {"dp": 10, "name": "Fan Speed", "device_class": "enum", "options": ["off", "low", "middle", "high", "strong"]},
                {"dp": 14, "name": "Filter Hours", "unit": UnitOfTime.HOURS, "device_class": "duration"},
                {"dp": 16, "name": "Noise Level", "unit": UnitOfSoundPressure.DECIBEL},
                {"dp": 5, "name": "Light Brightness", "unit": PERCENTAGE},
                {"dp": 102, "name": "RGB Brightness", "unit": PERCENTAGE},
                {"dp": 103, "name": "Color Temperature", "unit": "K"}
            ],
            "select": [
                {"dp": 101, "name": "RGB Mode", "options": list(range(10))},
                {"dp": 11, "name": "Fan Speed Setting", "options": ["off", "low", "middle", "high", "strong"]},
                {"dp": 16, "name": "Noise Level", "options": ["silent", "low", "normal", "high"]},
                {"dp": 103, "name": "Color Temperature", "options": ["warm", "neutral", "cool"]}
            ],
            "number": [
                {"dp": 13, "name": "Countdown Timer", "min": 0, "max": 60, "unit": UnitOfTime.MINUTES},
                {"dp": 5, "name": "Light Brightness Level", "min": 0, "max": 255, "unit": PERCENTAGE},
                {"dp": 102, "name": "RGB Brightness Level", "min": 0, "max": 255, "unit": PERCENTAGE},
                {"dp": 103, "name": "Color Temperature Level", "min": 2700, "max": 6500, "unit": "K"}
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
                "dp": 102,  # fan_speed (0-9)
                "speeds": ["off", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
            },
            "light": {
                "dp": 4,  # main light on/off
                "brightness_dp": None,  # No dedicated brightness
                "rgb_dp": 107,  # RGB color data
                "rgb_mode_dp": 108  # RGB work mode
            },
            "switch": [
                {"dp": 1, "name": "Power", "device_class": "switch"},
                {"dp": 6, "name": "RGB Light", "device_class": "switch"},
                {"dp": 7, "name": "Wash Mode", "device_class": "switch"},
                {"dp": 104, "name": "LED Light", "device_class": "switch"},
                {"dp": 106, "name": "Confirm", "device_class": "switch"}
            ],
            "sensor": [
                {"dp": 102, "name": "Fan Speed", "device_class": "enum", "options": ["off", "1", "2", "3", "4", "5", "6", "7", "8", "9"]},
                {"dp": 103, "name": "Carbon Filter Usage", "unit": "days", "device_class": "duration"},
                {"dp": 109, "name": "Metal Filter Usage", "unit": "days", "device_class": "duration"}
            ],
            "select": [
                {"dp": 108, "name": "RGB Mode", "options": ["white", "colour", "scene", "music"]},
                {"dp": 102, "name": "Fan Speed Level", "options": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]}
            ],
            "number": [
                {"dp": 105, "name": "Timer", "min": 0, "max": 60, "unit": UnitOfTime.MINUTES},
                {"dp": 103, "name": "Carbon Filter Reset", "min": 0, "max": 250, "unit": "days"},
                {"dp": 109, "name": "Metal Filter Reset", "min": 0, "max": 40, "unit": "days"}
            ]
        }
    },

    # IND7705HC Induction Cooktop
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
                {"dp": 101, "name": "Power", "device_class": "switch"},
                {"dp": 102, "name": "Pause", "device_class": "switch"},
                {"dp": 103, "name": "Child Lock", "device_class": "switch"},
                {"dp": 145, "name": "Senior Mode", "device_class": "switch"},
                {"dp": 108, "name": "Confirm Action", "device_class": "switch"}
            ],
            "number": [
                {"dp": 104, "name": "Max Power Level", "min": 0, "max": 25},
                {"dp": 134, "name": "General Timer", "min": 0, "max": 99, "unit": UnitOfTime.MINUTES},
                {"dp": 162, "name": "Zone 1 Power", "min": 0, "max": 25, "zone": 1},
                {"dp": 162, "name": "Zone 2 Power", "min": 0, "max": 25, "zone": 2},
                {"dp": 162, "name": "Zone 3 Power", "min": 0, "max": 25, "zone": 3},
                {"dp": 162, "name": "Zone 4 Power", "min": 0, "max": 25, "zone": 4},
                {"dp": 162, "name": "Zone 5 Power", "min": 0, "max": 25, "zone": 5},
                {"dp": 167, "name": "Zone 1 Timer", "min": 0, "max": 255, "unit": UnitOfTime.MINUTES, "zone": 1},
                {"dp": 167, "name": "Zone 2 Timer", "min": 0, "max": 255, "unit": UnitOfTime.MINUTES, "zone": 2},
                {"dp": 167, "name": "Zone 3 Timer", "min": 0, "max": 255, "unit": UnitOfTime.MINUTES, "zone": 3},
                {"dp": 167, "name": "Zone 4 Timer", "min": 0, "max": 255, "unit": UnitOfTime.MINUTES, "zone": 4},
                {"dp": 167, "name": "Zone 5 Timer", "min": 0, "max": 255, "unit": UnitOfTime.MINUTES, "zone": 5},
                {"dp": 168, "name": "Zone 1 Core Temp", "min": 0, "max": 300, "unit": UnitOfTemperature.CELSIUS, "zone": 1},
                {"dp": 168, "name": "Zone 2 Core Temp", "min": 0, "max": 300, "unit": UnitOfTemperature.CELSIUS, "zone": 2},
                {"dp": 168, "name": "Zone 3 Core Temp", "min": 0, "max": 300, "unit": UnitOfTemperature.CELSIUS, "zone": 3},
                {"dp": 168, "name": "Zone 4 Core Temp", "min": 0, "max": 300, "unit": UnitOfTemperature.CELSIUS, "zone": 4},
                {"dp": 168, "name": "Zone 5 Core Temp", "min": 0, "max": 300, "unit": UnitOfTemperature.CELSIUS, "zone": 5}
            ],
            "select": [
                {"dp": 148, "name": "Zone 1 Quick Level", "options": QUICK_LEVELS},
                {"dp": 149, "name": "Zone 2 Quick Level", "options": QUICK_LEVELS},
                {"dp": 150, "name": "Zone 3 Quick Level", "options": QUICK_LEVELS},
                {"dp": 151, "name": "Zone 4 Quick Level", "options": QUICK_LEVELS},
                {"dp": 152, "name": "Zone 5 Quick Level", "options": QUICK_LEVELS},
                {"dp": 153, "name": "Save Zone Level", "options": ["save_hob1", "save_hob2", "save_hob3", "save_hob4", "save_hob5"]},
                {"dp": 154, "name": "Set Zone Level", "options": ["set_hob1", "set_hob2", "set_hob3", "set_hob4", "set_hob5"]},
                {"dp": 155, "name": "Power Limit", "options": ["power_limit_1", "power_limit_2", "power_limit_3", "power_limit_4", "power_limit_5"]}
            ],
            "sensor": [
                {"dp": 105, "name": "Zone 1 Error", "device_class": "problem", "zone": 1},
                {"dp": 105, "name": "Zone 2 Error", "device_class": "problem", "zone": 2},
                {"dp": 105, "name": "Zone 3 Error", "device_class": "problem", "zone": 3},
                {"dp": 105, "name": "Zone 4 Error", "device_class": "problem", "zone": 4},
                {"dp": 105, "name": "Zone 5 Error", "device_class": "problem", "zone": 5},
                {"dp": 169, "name": "Zone 1 Core Temp Display", "unit": UnitOfTemperature.CELSIUS, "zone": 1},
                {"dp": 169, "name": "Zone 2 Core Temp Display", "unit": UnitOfTemperature.CELSIUS, "zone": 2},
                {"dp": 169, "name": "Zone 3 Core Temp Display", "unit": UnitOfTemperature.CELSIUS, "zone": 3},
                {"dp": 169, "name": "Zone 4 Core Temp Display", "unit": UnitOfTemperature.CELSIUS, "zone": 4},
                {"dp": 169, "name": "Zone 5 Core Temp Display", "unit": UnitOfTemperature.CELSIUS, "zone": 5}
            ],
            "binary_sensor": [
                {"dp": 161, "name": "Zone 1 Selected", "device_class": "running", "zone": 1},
                {"dp": 161, "name": "Zone 2 Selected", "device_class": "running", "zone": 2},
                {"dp": 161, "name": "Zone 3 Selected", "device_class": "running", "zone": 3},
                {"dp": 161, "name": "Zone 4 Selected", "device_class": "running", "zone": 4},
                {"dp": 161, "name": "Zone 5 Selected", "device_class": "running", "zone": 5},
                {"dp": 163, "name": "Zone 1 Boost", "device_class": "running", "zone": 1},
                {"dp": 163, "name": "Zone 2 Boost", "device_class": "running", "zone": 2},
                {"dp": 163, "name": "Zone 3 Boost", "device_class": "running", "zone": 3},
                {"dp": 163, "name": "Zone 4 Boost", "device_class": "running", "zone": 4},
                {"dp": 163, "name": "Zone 5 Boost", "device_class": "running", "zone": 5},
                {"dp": 164, "name": "Zone 1 Keep Warm", "device_class": "running", "zone": 1},
                {"dp": 164, "name": "Zone 2 Keep Warm", "device_class": "running", "zone": 2},
                {"dp": 164, "name": "Zone 3 Keep Warm", "device_class": "running", "zone": 3},
                {"dp": 164, "name": "Zone 4 Keep Warm", "device_class": "running", "zone": 4},
                {"dp": 164, "name": "Zone 5 Keep Warm", "device_class": "running", "zone": 5},
                {"dp": 165, "name": "Flex Zone Left", "device_class": "running", "zone": 1},
                {"dp": 165, "name": "Flex Zone Right", "device_class": "running", "zone": 2},
                {"dp": 166, "name": "BBQ Mode Left", "device_class": "running", "zone": 1},
                {"dp": 166, "name": "BBQ Mode Right", "device_class": "running", "zone": 2}
            ]
        }
    }
}

def find_device_by_product_name(product_name: str) -> dict:
    """Find device in central database by product name."""
    for device_key, device_info in KNOWN_DEVICES.items():
        if product_name in device_info["product_names"]:
            return device_info
    return None

def find_device_by_device_id(device_id: str) -> dict:
    """Find device in central database by device ID."""
    for device_key, device_info in KNOWN_DEVICES.items():
        # Exact match
        if device_id in device_info["device_ids"]:
            return device_info
        # Pattern match
        for pattern in device_info["device_id_patterns"]:
            if device_id.startswith(pattern):
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

def get_device_info_by_device_id(device_id: str) -> dict:
    """Get device information based on device ID (for manual setup)."""
    device_info = find_device_by_device_id(device_id)
    if device_info:
        return {
            "model_id": device_info["model_id"],
            "category": device_info["category"],
            "name": device_info["name"],
            "product_name": device_info["product_names"][0]  # Use first product name
        }
    return None

def get_product_name_by_device_id(device_id: str) -> str:
    """Get product name by device ID - for automatic device type detection."""
    device_info = find_device_by_device_id(device_id)
    if device_info:
        return device_info["product_names"][0]  # Return the primary product name
    return None

def auto_detect_device_config(device_id: str = None, provided_product_name: str = None) -> dict:
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
    """Get device information based on product name from discovery."""
    # Check central database first
    device_info = find_device_by_product_name(product_name)
    if device_info:
        return {
            "model_id": device_info["model_id"],
            "category": device_info["category"],
            "name": device_info["name"]
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

def get_device_platforms(category: str) -> list:
    """Get required platforms for device category."""
    # Try to find specific device platforms first
    for device_key, device_info in KNOWN_DEVICES.items():
        if device_info["category"] == category:
            return device_info["platforms"]

    # Fallback to category-based platforms
    if category == CATEGORY_HOOD:
        return ["fan", "light", "switch", "sensor", "select", "number"]
    elif category == CATEGORY_COOKTOP:
        return ["switch", "number", "sensor", "binary_sensor"]
    else:
        # Generic fallback: Load all platforms for unknown devices
        # This ensures manual setup always works
        return ["fan", "light", "switch", "sensor", "select", "number", "binary_sensor"]

def get_device_platforms_by_product_name(product_name: str) -> list:
    """Get platforms directly by product name (most efficient)."""
    device_info = find_device_by_product_name(product_name)
    if device_info:
        return device_info["platforms"]

    # Fallback to category-based lookup
    device_type_info = get_device_info_by_product_name(product_name)
    return get_device_platforms(device_type_info["category"])

def get_device_entities(product_name: str, platform: str) -> list:
    """Get entity configurations for a specific product and platform."""
    device_info = find_device_by_product_name(product_name)
    if device_info and "entities" in device_info:
        entities_config = device_info["entities"]
        if platform in entities_config:
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
        return KNOWN_DEVICES[device_choice]["product_names"][0]
    elif device_choice == "generic_hood":
        return "manual_hood"
    elif device_choice == "generic_cooktop":
        return "manual_cooktop"
    else:
        return "unknown"