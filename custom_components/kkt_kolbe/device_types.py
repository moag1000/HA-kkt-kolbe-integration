"""Device type specific configurations for KKT Kolbe devices."""

from .const import CATEGORY_HOOD, CATEGORY_COOKTOP


# Hood (Dunstabzugshaube) Data Points
HOOD_DPS = {
    1: "switch",           # Main power
    4: "light",           # Light on/off
    6: "switch_lamp",     # Filter cleaning reminder
    10: "fan_speed_enum", # Fan speed
    13: "countdown",      # Timer (0-60 min)
    101: "RGB",           # RGB light mode (0-9)
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
    # HERMES & STYLE Hood
    "hermes_style_hood": {
        "model_id": "e1k6i0zo",
        "category": CATEGORY_HOOD,
        "name": "HERMES & STYLE Hood",
        "product_names": ["ypaixllljc2dcpae"],
        "device_ids": ["bf735dfe2ad64fba7cpyhn"],
        "device_id_patterns": ["bf735dfe2ad64fba7c"],
        "platforms": ["fan", "light", "switch", "sensor", "select", "number"],
        "data_points": HOOD_DPS,
        "entities": {
            "fan": {
                "dp": 10,  # fan_speed_enum
                "speeds": ["off", "low", "middle", "high", "strong"]
            },
            "light": {
                "dp": 4,  # light on/off
                "rgb_dp": 101  # RGB mode
            },
            "switch": [
                {"dp": 1, "name": "Power", "device_class": "switch"},
                {"dp": 6, "name": "Filter Reminder", "device_class": "switch"}
            ],
            "sensor": [
                {"dp": 6, "name": "Filter Status", "device_class": "problem"}
            ],
            "select": [
                {"dp": 101, "name": "RGB Mode", "options": list(range(10))}
            ],
            "number": [
                {"dp": 13, "name": "Timer", "min": 0, "max": 60, "unit": "min"}
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
                {"dp": 134, "name": "General Timer", "min": 0, "max": 99, "unit": "min"},
                {"dp": 162, "name": "Zone 1 Power", "min": 0, "max": 25, "zone": 1},
                {"dp": 162, "name": "Zone 2 Power", "min": 0, "max": 25, "zone": 2},
                {"dp": 162, "name": "Zone 3 Power", "min": 0, "max": 25, "zone": 3},
                {"dp": 162, "name": "Zone 4 Power", "min": 0, "max": 25, "zone": 4},
                {"dp": 162, "name": "Zone 5 Power", "min": 0, "max": 25, "zone": 5},
                {"dp": 167, "name": "Zone 1 Timer", "min": 0, "max": 255, "unit": "min", "zone": 1},
                {"dp": 167, "name": "Zone 2 Timer", "min": 0, "max": 255, "unit": "min", "zone": 2},
                {"dp": 167, "name": "Zone 3 Timer", "min": 0, "max": 255, "unit": "min", "zone": 3},
                {"dp": 167, "name": "Zone 4 Timer", "min": 0, "max": 255, "unit": "min", "zone": 4},
                {"dp": 167, "name": "Zone 5 Timer", "min": 0, "max": 255, "unit": "min", "zone": 5},
                {"dp": 168, "name": "Zone 1 Core Temp", "min": 0, "max": 300, "unit": "°C", "zone": 1},
                {"dp": 168, "name": "Zone 2 Core Temp", "min": 0, "max": 300, "unit": "°C", "zone": 2},
                {"dp": 168, "name": "Zone 3 Core Temp", "min": 0, "max": 300, "unit": "°C", "zone": 3},
                {"dp": 168, "name": "Zone 4 Core Temp", "min": 0, "max": 300, "unit": "°C", "zone": 4},
                {"dp": 168, "name": "Zone 5 Core Temp", "min": 0, "max": 300, "unit": "°C", "zone": 5}
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
                {"dp": 169, "name": "Zone 1 Core Temp Display", "unit": "°C", "zone": 1},
                {"dp": 169, "name": "Zone 2 Core Temp Display", "unit": "°C", "zone": 2},
                {"dp": 169, "name": "Zone 3 Core Temp Display", "unit": "°C", "zone": 3},
                {"dp": 169, "name": "Zone 4 Core Temp Display", "unit": "°C", "zone": 4},
                {"dp": 169, "name": "Zone 5 Core Temp Display", "unit": "°C", "zone": 5}
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
                {"dp": 165, "name": "Flex Zone Left", "device_class": "running"},
                {"dp": 165, "name": "Flex Zone Right", "device_class": "running"},
                {"dp": 166, "name": "BBQ Mode Left", "device_class": "running"},
                {"dp": 166, "name": "BBQ Mode Right", "device_class": "running"}
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