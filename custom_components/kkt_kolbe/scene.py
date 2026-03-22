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

if TYPE_CHECKING:
    from .data import KKTKolbeConfigEntry

PARALLEL_UPDATES = 0
POWER_ON_DELAY = 0.5  # seconds to wait after powering on before sending commands

_LOGGER = logging.getLogger(__name__)


# RGB color names for numeric modes (0=off, 1-9=colors)
RGB_COLOR_NAMES = [
    ("Aus", 0, "mdi:lightbulb-off"),
    ("Weiss", 1, "mdi:lightbulb-on"),
    ("Rot", 2, "mdi:lightbulb-on"),
    ("Gruen", 3, "mdi:lightbulb-on"),
    ("Blau", 4, "mdi:lightbulb-on"),
    ("Gelb", 5, "mdi:lightbulb-on"),
    ("Lila", 6, "mdi:lightbulb-on"),
    ("Orange", 7, "mdi:lightbulb-on"),
    ("Cyan", 8, "mdi:lightbulb-on"),
    ("Gruen hell", 9, "mdi:lightbulb-on"),
]

# HCM work mode names
HCM_MODE_NAMES = [
    ("Weiss", "white", "mdi:lightbulb-on"),
    ("Farbe", "colour", "mdi:palette"),
    ("Szene", "scene", "mdi:movie-open"),
    ("Musik", "music", "mdi:music"),
]

# Common scenes for all hoods (power/light control)
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


def _build_rgb_scenes_numeric(effect_dp: int) -> list[dict[str, Any]]:
    """Build RGB scenes for numeric effect DP (HERMES/EASY family)."""
    scenes = []
    for name, value, icon in RGB_COLOR_NAMES:
        if value == 0:
            # "Aus" does not need power-on
            scenes.append({"name": f"RGB {name}", "icon": icon, "actions": [("dp", effect_dp, 0)]})
        else:
            scenes.append(
                {
                    "name": f"RGB {name}",
                    "icon": icon,
                    "actions": [("power_on",), ("suppress_fan",), ("dp", effect_dp, value)],
                }
            )
    return scenes


def _build_rgb_scenes_hcm(work_mode_dp: int) -> list[dict[str, Any]]:
    """Build RGB scenes for HCM work_mode DP."""
    return [
        {
            "name": f"RGB {name}",
            "icon": icon,
            "actions": [("power_on",), ("suppress_fan",), ("dp", work_mode_dp, value)],
        }
        for name, value, icon in HCM_MODE_NAMES
    ]


def _get_scene_definitions(device_key: str) -> list[dict[str, Any]]:
    """Get scene definitions for a device type.

    Dynamically generates RGB scenes based on the device's actual effect_dp,
    so it works for both HERMES (DP 101), EASY (DP 102), and HCM (DP 108).
    """
    device_info = KNOWN_DEVICES.get(device_key)
    if not device_info:
        return []

    # Start with common scenes for all hoods
    scenes: list[dict[str, Any]] = list(COMMON_HOOD_SCENES)

    # Find the RGB effect DP from the light configuration
    entities = device_info.get("entities", {})
    light_configs = entities.get("light", [])

    for light_config in light_configs:
        if not isinstance(light_config, dict):
            continue
        effect_dp = light_config.get("effect_dp")
        if effect_dp is None:
            continue

        if light_config.get("effect_numeric"):
            # Numeric RGB mode (HERMES DP 101, EASY DP 102)
            scenes.extend(_build_rgb_scenes_numeric(effect_dp))
        else:
            # String-based work_mode (HCM DP 108)
            scenes.extend(_build_rgb_scenes_hcm(effect_dp))
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

    entities = [KKTKolbeHoodScene(coordinator, entry, scene_def, light_dp) for scene_def in scene_defs]

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
    ) -> None:
        """Initialize the scene."""
        config = {
            "dp": light_dp,  # Used for unique_id generation
            "name": scene_def["name"],
            "icon": scene_def.get("icon", "mdi:palette"),
        }
        super().__init__(coordinator, entry, config, "scene")

        self._actions = scene_def["actions"]
        self._light_dp = light_dp
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
                if hood_was_off:
                    await self._async_suppress_fan_auto_start()

            elif cmd == "light_on":
                await self._async_set_data_point(self._light_dp, True)

            elif cmd == "light_off":
                await self._async_set_data_point(self._light_dp, False)

            elif cmd == "dp":
                dp_id = action[1]
                value = action[2]
                if not self._is_hood_on():
                    hood_was_off = True
                    await self._async_set_data_point(1, True)
                    await asyncio.sleep(POWER_ON_DELAY)
                    await self._async_suppress_fan_auto_start()
                await self._async_set_data_point(dp_id, value)

        _LOGGER.debug("Scene '%s' activated", self._name)
