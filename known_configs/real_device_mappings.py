"""Real device data point mappings from curl examples."""

# HERMES & STYLE Hood - Real API codes
HERMES_STYLE_REAL_CODES = [
    "switch",           # Main power
    "light",           # Main light
    "switch_lamp",     # Light strip
    "fan_speed_enum",  # Fan speed
    "countdown",       # Timer
    "RGB",             # RGB lighting (new!)
]

# IND7705HC Cooktop - Real OEM codes
IND7705HC_REAL_CODES = [
    "user_device_power_switch",     # Main power
    "user_device_pause_switch",     # Pause/Resume
    "user_device_lock_switch",      # Child lock
    "user_device_cur_max_level",    # Current max level
    "oem_hob_error_num",           # Error number
    "oem_device_chef_level",       # Chef function level
    "oem_hob_bbq_timer",           # BBQ timer
    "oem_device_confirm",          # Confirm button
    "oem_device_timer_num",        # Timer number
    "oem_device_old_people",       # Senior mode
    "oem_hob_1_quick_level",       # Zone 1 quick level
    "oem_hob_2_quick_level",       # Zone 2 quick level
    "oem_hob_3_quick_level",       # Zone 3 quick level
    "oem_hob_4_quick_level",       # Zone 4 quick level
    "oem_hob_5_quick_level",       # Zone 5 quick level
    "oem_device_save_level",       # Save level
    "oem_device_set_level",        # Set level
    "oem_device_power_limit",      # Power limit
    "oem_hob_selected_switch",     # Selected zone switch
    "oem_hob_level_num",           # Level number
    "oem_hob_boost_switch",        # Boost function
    "oem_hob_warm_switch",         # Keep warm
    "oem_hob_flex_switch",         # Flex zone
    "oem_hob_bbq_switch",          # BBQ mode
    "oem_hob_timer_num",           # Timer value
    "oem_hob_set_core_sensor",     # Core sensor setting
    "oem_hob_disp_coresensor",     # Core sensor display
]

# Mapping from real codes to friendly names
REAL_CODE_MAPPINGS = {
    # HERMES & STYLE
    "RGB": {"name": "RGB Lighting", "entity_type": "light", "icon": "mdi:palette"},

    # IND7705HC specific mappings
    "user_device_power_switch": {"name": "Power", "entity_type": "switch", "icon": "mdi:power"},
    "user_device_pause_switch": {"name": "Pause/Resume", "entity_type": "switch", "icon": "mdi:pause"},
    "user_device_lock_switch": {"name": "Child Lock", "entity_type": "switch", "icon": "mdi:lock"},
    "oem_device_chef_level": {"name": "Chef Function Level", "entity_type": "number", "icon": "mdi:chef-hat"},
    "oem_hob_bbq_timer": {"name": "BBQ Timer", "entity_type": "number", "icon": "mdi:timer"},
    "oem_hob_1_quick_level": {"name": "Zone 1 Level", "entity_type": "number", "icon": "mdi:numeric-1-circle"},
    "oem_hob_2_quick_level": {"name": "Zone 2 Level", "entity_type": "number", "icon": "mdi:numeric-2-circle"},
    "oem_hob_3_quick_level": {"name": "Zone 3 Level", "entity_type": "number", "icon": "mdi:numeric-3-circle"},
    "oem_hob_4_quick_level": {"name": "Zone 4 Level", "entity_type": "number", "icon": "mdi:numeric-4-circle"},
    "oem_hob_5_quick_level": {"name": "Zone 5 Level", "entity_type": "number", "icon": "mdi:numeric-5-circle"},
    "oem_hob_boost_switch": {"name": "Boost Function", "entity_type": "switch", "icon": "mdi:flash"},
    "oem_hob_warm_switch": {"name": "Keep Warm", "entity_type": "switch", "icon": "mdi:thermometer"},
    "oem_hob_flex_switch": {"name": "Flex Zone", "entity_type": "switch", "icon": "mdi:arrow-expand-horizontal"},
    "oem_hob_bbq_switch": {"name": "BBQ Mode", "entity_type": "switch", "icon": "mdi:grill"},
}

# Device-specific code lists for optimized API calls
DEVICE_CODE_MAPPINGS = {
    "hermes_style": HERMES_STYLE_REAL_CODES,
    "ind7705hc": IND7705HC_REAL_CODES,
}