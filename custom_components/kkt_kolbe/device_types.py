"""Device type specific configurations for KKT Kolbe devices."""

from .const import CATEGORY_HOOD, CATEGORY_COOKTOP

# Product Name to Model ID mapping (discovered dynamically)
PRODUCT_MODEL_MAPPING = {
    "ypaixllljc2dcpae": {
        "model_id": "e1k6i0zo",
        "category": CATEGORY_HOOD,
        "name": "HERMES & STYLE Hood"
    },
    "p8volecsgzdyun29": {
        "model_id": "e1kc5q64",
        "category": CATEGORY_COOKTOP,
        "name": "IND7705HC Induction Cooktop"
    }
}

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

def get_device_dps(category: str) -> dict:
    """Get data points for device category."""
    if category == CATEGORY_HOOD:
        return HOOD_DPS
    elif category == CATEGORY_COOKTOP:
        return COOKTOP_DPS
    else:
        return {}

def get_device_info_by_product_name(product_name: str) -> dict:
    """Get device information based on product name from discovery."""
    if product_name in PRODUCT_MODEL_MAPPING:
        return PRODUCT_MODEL_MAPPING[product_name]

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
    if category == CATEGORY_HOOD:
        return ["fan", "light", "switch", "sensor", "select", "number"]
    elif category == CATEGORY_COOKTOP:
        return ["switch", "number", "sensor", "binary_sensor"]
    else:
        return ["switch", "sensor"]