"""Scene platform for KKT Kolbe devices.

Provides pre-built scenes for common hood operations, automatically created
for devices with RGB lighting. Exposed to HomeKit/Siri for voice control.

Example Siri commands:
    "Hey Siri, Dunstabzug Licht An"
    "Hey Siri, Dunstabzug RGB Rot"
    "Hey Siri, Dunstabzug Aus"
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING
from typing import Any

from homeassistant.components.scene import Scene
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base_entity import KKTBaseEntity
from .device_types import KNOWN_DEVICES
from .device_types import get_device_entity_config

if TYPE_CHECKING:
    from . import KKTKolbeConfigEntry

PARALLEL_UPDATES = 0
POWER_ON_DELAY = 0.5  # seconds to wait after powering on before sending commands

_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Scene definitions
# ---------------------------------------------------------------------------

# Common scenes for all hoods (power/light control)
# These use "actions" - a list of (dp, value) tuples executed in sequence
COMMON_HOOD_SCENES = [
    {
        "name": "Licht An",
        "icon": "mdi:lightbulb-on",
        "actions": [("power_on",), ("suppress_fan",), ("light_on",)],
    },
    {
        "name": "Licht Aus",
        "icon": "mdi:lightbulb-off",
        "actions": [("light_off",)],
    },
    {
        "name": "Haube Aus",
        "icon": "mdi:power-off",
        "actions": [("power_off",)],
    },
]

# RGB scenes for HERMES-family hoods (DP 101, numeric 0-9)
HERMES_RGB_SCENES = [
    {"name": "RGB Aus", "icon": "mdi:lightbulb-off", "actions": [("dp", 101, 0)]},
    {"name": "RGB Weiss", "icon": "mdi:lightbulb-on", "actions": [("power_on",), ("suppress_fan",), ("dp", 101, 1)]},
    {"name": "RGB Rot", "icon": "mdi:lightbulb-on", "actions": [("power_on",), ("suppress_fan",), ("dp", 101, 2)]},
    {"name": "RGB Gruen", "icon": "mdi:lightbulb-on", "actions": [("power_on",), ("suppress_fan",), ("dp", 101, 3)]},
    {"name": "RGB Blau", "icon": "mdi:lightbulb-on", "actions": [("power_on",), ("suppress_fan",), ("dp", 101, 4)]},
    {"name": "RGB Gelb", "icon": "mdi:lightbulb-on", "actions": [("power_on",), ("suppress_fan",), ("dp", 101, 5)]},
    {"name": "RGB Lila", "icon": "mdi:lightbulb-on", "actions": [("power_on",), ("suppress_fan",), ("dp", 101, 6)]},
    {"name": "RGB Orange", "icon": "mdi:lightbulb-on", "actions": [("power_on",), ("suppress_fan",), ("dp", 101, 7)]},
    {"name": "RGB Cyan", "icon": "mdi:lightbulb-on", "actions": [("power_on",), ("suppress_fan",), ("dp", 101, 8)]},
    {
        "name": "RGB Gruen hell",
        "icon": "mdi:lightbulb-on",
        "actions": [("power_on",), ("suppress_fan",), ("dp", 101, 9)],
    },
]

# RGB scenes for HCM-family hoods (DP 108, string modes)
HCM_RGB_SCENES = [
    {
        "name": "RGB Weiss",
        "icon": "mdi:lightbulb-on",
        "actions": [("power_on",), ("suppress_fan",), ("dp", 108, "white")],
    },
    {"name": "RGB Farbe", "icon": "mdi:palette", "actions": [("power_on",), ("suppress_fan",), ("dp", 108, "colour")]},
    {
        "name": "RGB Szene",
        "icon": "mdi:movie-open",
        "actions": [("power_on",), ("suppress_fan",), ("dp", 108, "scene")],
    },
    {"name": "RGB Musik", "icon": "mdi:music", "actions": [("power_on",), ("suppress_fan",), ("dp", 108, "music")]},
]


def _get_scene_definitions(device_key: str) -> list[dict[str, Any]]:
    """Get scene definitions for a device type."""
    device_info = KNOWN_DEVICES.get(device_key)
    if not device_info:
        return []

    # Start with common scenes for all hoods
    scenes: list[dict[str, Any]] = list(COMMON_HOOD_SCENES)

    # Add RGB-specific scenes based on device type
    entities = device_info.get("entities", {})
    light_configs = entities.get("light", [])

    for light_config in light_configs:
        if not isinstance(light_config, dict):
            continue
        effect_dp = light_config.get("effect_dp")
        if effect_dp is None:
            continue

        # HERMES family: numeric effect_dp 101
        if effect_dp == 101 and light_config.get("effect_numeric"):
            scenes.extend(HERMES_RGB_SCENES)
            break

        # HCM family: string-based work_mode DP 108
        if effect_dp == 108 and not light_config.get("effect_numeric", True):
            scenes.extend(HCM_RGB_SCENES)
            break

    return scenes


def _get_light_dp(device_key: str) -> int:
    """Get the light DP for a device. Default 4."""
    device_info = KNOWN_DEVICES.get(device_key)
    if not device_info:
        return 4
    light_configs = device_info.get("entities", {}).get("light", [])
    if light_configs and isinstance(light_configs[0], dict):
        return light_configs[0].get("dp", 4)
    return 4


def _get_fan_off_value(device_key: str) -> tuple[int, Any]:
    """Get the fan DP and off value for a device."""
    fan_config = get_device_entity_config(device_key, "fan")
    if not fan_config:
        return (10, "off")
    dp = fan_config.get("dp", 10)
    if fan_config.get("numeric", False):
        return (dp, 0)
    return (dp, "off")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KKTKolbeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KKT Kolbe scene entities."""
    runtime_data = entry.runtime_data
    coordinator = runtime_data.coordinator
    device_type = runtime_data.device_type
    product_name = runtime_data.product_name

    lookup_key = device_type if device_type not in ("auto", None, "") else product_name

    scene_defs = _get_scene_definitions(lookup_key)
    if not scene_defs:
        _LOGGER.debug("No scene definitions for %s", lookup_key)
        return

    light_dp = _get_light_dp(lookup_key)
    fan_dp, fan_off_value = _get_fan_off_value(lookup_key)

    entities = [
        KKTKolbeHoodScene(coordinator, entry, scene_def, light_dp, fan_dp, fan_off_value) for scene_def in scene_defs
    ]

    if entities:
        _LOGGER.info(
            "Setting up %d scenes for %s (device_type=%s)",
            len(entities),
            lookup_key,
            device_type,
        )
        async_add_entities(entities)


class KKTKolbeHoodScene(KKTBaseEntity, Scene):
    """Pre-built scene for KKT Kolbe hood operations.

    Each scene executes a sequence of actions (power on, suppress fan, set DP).
    The fan suppression uses the same mechanism as the light and fan platforms:
    when the hood firmware auto-starts the fan on power-on, a fan-off command
    is sent immediately after to prevent unwanted fan operation.
    """

    def __init__(
        self,
        coordinator: Any,
        entry: Any,
        scene_def: dict[str, Any],
        light_dp: int,
        fan_dp: int,
        fan_off_value: Any,
    ) -> None:
        """Initialize the scene."""
        config = {
            "dp": scene_def.get("dp", light_dp),
            "name": scene_def["name"],
            "icon": scene_def.get("icon", "mdi:palette"),
        }
        # Use light_dp as fallback dp for unique_id generation on common scenes
        if "dp" not in scene_def:
            config["dp"] = light_dp
        super().__init__(coordinator, entry, config, "scene")

        self._actions = scene_def["actions"]
        self._light_dp = light_dp
        self._fan_dp = fan_dp
        self._fan_off_value = fan_off_value
        self._attr_icon = scene_def.get("icon", "mdi:palette")

    def _is_hood_on(self) -> bool:
        """Check if hood main power (DP 1) is on."""
        value = self._get_data_point_value(1)
        if value is None:
            return False
        return bool(value)

    async def async_activate(self, **kwargs: Any) -> None:
        """Activate the scene by executing the action sequence."""
        _LOGGER.debug("Activating scene '%s' with %d actions", self._name, len(self._actions))

        hood_was_off = False

        for action in self._actions:
            cmd = action[0]

            if cmd == "power_on":
                if not self._is_hood_on():
                    hood_was_off = True
                    await self._async_set_data_point(1, True)
                    await asyncio.sleep(POWER_ON_DELAY)

            elif cmd == "power_off":
                await self._async_set_data_point(1, False)

            elif cmd == "suppress_fan":
                # Only suppress if hood was just turned on (firmware auto-starts fan)
                # Respects the disable_fan_auto_start config option
                if hood_was_off:
                    await self._async_suppress_fan_auto_start()

            elif cmd == "light_on":
                await self._async_set_data_point(self._light_dp, True)

            elif cmd == "light_off":
                await self._async_set_data_point(self._light_dp, False)

            elif cmd == "dp":
                # Direct DP set: ("dp", dp_id, value)
                dp_id = action[1]
                value = action[2]
                # If hood is off and we need to set a DP, power on first
                if not self._is_hood_on():
                    hood_was_off = True
                    await self._async_set_data_point(1, True)
                    await asyncio.sleep(POWER_ON_DELAY)
                    await self._async_suppress_fan_auto_start()
                await self._async_set_data_point(dp_id, value)

        _LOGGER.debug("Scene '%s' activated", self._name)
