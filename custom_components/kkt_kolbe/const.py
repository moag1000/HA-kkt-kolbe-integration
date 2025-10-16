"""Constants for KKT Kolbe integration."""

DOMAIN = "kkt_kolbe"

MANUFACTURER = "KKT Kolbe"

# Device categories
CATEGORY_HOOD = "yyj"  # Dunstabzugshaube
CATEGORY_COOKTOP = "dcl"  # Induktionskochfeld

# Device models
MODELS = {
    "e1k6i0zo": {
        "name": "HERMES & STYLE",
        "category": CATEGORY_HOOD,
        "product_id": "ypaixllljc2dcpae",
    },
    "IND7705HC": {
        "name": "IND7705HC",
        "category": CATEGORY_COOKTOP,
        "product_id": "p8volecsgzdyun29",
    },
}

# Tuya Data Points (DPs) mapping based on device capabilities
DP_POWER = "switch"  # DP1: Main power
DP_LIGHT = "light"  # DP4: Light on/off
DP_FILTER_ALERT = "switch_lamp"  # DP6: Filter cleaning reminder
DP_FAN_SPEED = "fan_speed_enum"  # DP10: Fan speed (off, low, middle, high, strong)
DP_COUNTDOWN = "countdown"  # DP13: Timer (0-60 min)
DP_RGB_LIGHT = "RGB"  # DP101: RGB light mode (0-9)

# Fan speed mappings
FAN_SPEEDS = {
    "off": 0,
    "low": 25,
    "middle": 50,
    "high": 75,
    "strong": 100,
}

FAN_SPEED_TO_DP = {
    0: "off",
    25: "low",
    50: "middle",
    75: "high",
    100: "strong",
}

# RGB Light modes
RGB_MODES = {
    0: "Off",
    1: "White",
    2: "Warm White",
    3: "Cool White",
    4: "Red",
    5: "Green",
    6: "Blue",
    7: "Yellow",
    8: "Purple",
    9: "Rainbow",
}