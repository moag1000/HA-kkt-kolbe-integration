"""Scene platform for KKT Kolbe devices.

Provides pre-built scenes for common RGB hood operations.
These scenes are automatically created for devices with RGB lighting
and are exposed to HomeKit/Siri for voice control.

Example Siri commands:
    "Hey Siri, Dunstabzug RGB Aus"
    "Hey Siri, Dunstabzug RGB Rot"
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from typing import Any

from homeassistant.components.scene import Scene
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base_entity import KKTBaseEntity
from .device_types import KNOWN_DEVICES

if TYPE_CHECKING:
    from . import KKTKolbeConfigEntry

PARALLEL_UPDATES = 0

_LOGGER = logging.getLogger(__name__)


# Scene definitions for HERMES-family hoods (DP 101, numeric 0-9)
HERMES_RGB_SCENES = [
    {"name": "RGB Aus", "dp": 101, "value": 0, "icon": "mdi:lightbulb-off"},
    {"name": "RGB Weiss", "dp": 101, "value": 1, "icon": "mdi:lightbulb-on"},
    {"name": "RGB Rot", "dp": 101, "value": 2, "icon": "mdi:lightbulb-on"},
    {"name": "RGB Gruen", "dp": 101, "value": 3, "icon": "mdi:lightbulb-on"},
    {"name": "RGB Blau", "dp": 101, "value": 4, "icon": "mdi:lightbulb-on"},
    {"name": "RGB Gelb", "dp": 101, "value": 5, "icon": "mdi:lightbulb-on"},
    {"name": "RGB Lila", "dp": 101, "value": 6, "icon": "mdi:lightbulb-on"},
    {"name": "RGB Orange", "dp": 101, "value": 7, "icon": "mdi:lightbulb-on"},
    {"name": "RGB Cyan", "dp": 101, "value": 8, "icon": "mdi:lightbulb-on"},
    {"name": "RGB Gruen hell", "dp": 101, "value": 9, "icon": "mdi:lightbulb-on"},
]

# Scene definitions for HCM-family hoods (DP 108, string modes)
HCM_RGB_SCENES = [
    {"name": "RGB Weiss", "dp": 108, "value": "white", "icon": "mdi:lightbulb-on"},
    {"name": "RGB Farbe", "dp": 108, "value": "colour", "icon": "mdi:palette"},
    {"name": "RGB Szene", "dp": 108, "value": "scene", "icon": "mdi:movie-open"},
    {"name": "RGB Musik", "dp": 108, "value": "music", "icon": "mdi:music"},
]


def _get_scene_definitions(device_key: str) -> list[dict[str, Any]]:
    """Get scene definitions for a device type."""
    device_info = KNOWN_DEVICES.get(device_key)
    if not device_info:
        return []

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
            return HERMES_RGB_SCENES

        # HCM family: string-based work_mode DP 108
        if effect_dp == 108 and not light_config.get("effect_numeric", True):
            return HCM_RGB_SCENES

    return []


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

    entities = [KKTKolbeRGBScene(coordinator, entry, scene_def) for scene_def in scene_defs]

    if entities:
        _LOGGER.info(
            "Setting up %d RGB scenes for %s (device_type=%s)",
            len(entities),
            lookup_key,
            device_type,
        )
        async_add_entities(entities)


class KKTKolbeRGBScene(KKTBaseEntity, Scene):
    """A pre-built scene for KKT Kolbe RGB hood operations.

    These scenes send a specific DP value to the device when activated.
    They are exposed to HomeKit/Siri for voice control.
    """

    def __init__(
        self,
        coordinator: Any,
        entry: Any,
        scene_def: dict[str, Any],
    ) -> None:
        """Initialize the scene."""
        config = {
            "dp": scene_def["dp"],
            "name": scene_def["name"],
            "icon": scene_def.get("icon", "mdi:palette"),
        }
        super().__init__(coordinator, entry, config, "scene")

        self._scene_dp = scene_def["dp"]
        self._scene_value = scene_def["value"]
        self._attr_icon = scene_def.get("icon", "mdi:palette")

    async def async_activate(self, **kwargs: Any) -> None:
        """Activate the scene by setting the RGB DP value."""
        _LOGGER.debug(
            "Activating scene '%s': DP %d = %s",
            self._name,
            self._scene_dp,
            self._scene_value,
        )

        # Ensure hood is powered on (DP 1) before setting RGB
        power_value = self._get_data_point_value(1)
        if not power_value:
            _LOGGER.info("Hood is off, turning on before activating RGB scene")
            await self._async_set_data_point(1, True)
            import asyncio

            await asyncio.sleep(0.5)

        await self._async_set_data_point(self._scene_dp, self._scene_value)
