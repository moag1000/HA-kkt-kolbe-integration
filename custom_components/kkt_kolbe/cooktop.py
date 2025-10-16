"""Induction cooktop specific entities for KKT IND7705HC.

IMPORTANT: Remote commands require manual confirmation at the device.
This is a Tuya API security feature, not a limitation of this integration.
A person must be present at the cooktop to press the confirmation button.
"""
import logging
from typing import Any
from homeassistant.components.number import NumberEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import CONF_TYPE

from .const import DOMAIN, CATEGORY_COOKTOP
from .cooktop_utils import (
    encode_zone_bitfield,
    decode_zone_bitfield,
    encode_zone_flags,
    decode_zone_flags,
    get_zone_power_level,
    set_zone_power_level,
)
from .device_types import QUICK_LEVELS

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry_number(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up cooktop number entities."""
    if entry.data.get(CONF_TYPE) != "cooktop":
        return

    device = hass.data[DOMAIN][entry.entry_id]["device"]
    entities = []

    # Create controls for each cooking zone (5 zones)
    for zone in range(1, 6):
        entities.append(CooktopZonePower(entry, device, zone))
        entities.append(CooktopZoneTimer(entry, device, zone))
        entities.append(CooktopZoneQuickLevel(entry, device, zone))

    # Add general timer
    entities.append(CooktopGeneralTimer(entry, device))

    async_add_entities(entities)

class CooktopZonePower(NumberEntity):
    """Power control for a cooking zone."""

    def __init__(self, entry: ConfigEntry, device, zone: int):
        """Initialize the zone power control."""
        self._entry = entry
        self._device = device
        self._zone = zone
        self._attr_unique_id = f"{entry.entry_id}_zone{zone}_power"
        self._attr_name = f"KKT Cooktop Zone {zone} Power"
        self._attr_icon = "mdi:stove"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 9
        self._attr_native_step = 1
        self._attr_native_unit_of_measurement = "level"

    @property
    def native_value(self) -> float:
        """Return the current power level."""
        # Get from DP 162 (oem_hob_level_num) bitfield
        raw_data = self._device._status.get("162", b'')
        if raw_data:
            levels = decode_zone_bitfield(raw_data)
            return float(get_zone_power_level(levels, self._zone))
        return 0.0

    async def async_set_native_value(self, value: float) -> None:
        """Set the power level."""
        # Get current levels
        raw_data = self._device._status.get("162", b'')
        levels = decode_zone_bitfield(raw_data) if raw_data else {i: 0 for i in range(1, 6)}

        # Update this zone's level
        levels = set_zone_power_level(levels, self._zone, int(value))

        # Encode and send
        encoded = encode_zone_bitfield(levels)
        self._device._device.set_value(162, encoded)
        self.async_write_ha_state()

class CooktopZoneTimer(NumberEntity):
    """Timer control for a cooking zone."""

    def __init__(self, entry: ConfigEntry, device, zone: int):
        """Initialize the zone timer."""
        self._entry = entry
        self._device = device
        self._zone = zone
        self._attr_unique_id = f"{entry.entry_id}_zone{zone}_timer"
        self._attr_name = f"KKT Cooktop Zone {zone} Timer"
        self._attr_icon = "mdi:timer"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 180
        self._attr_native_step = 1
        self._attr_native_unit_of_measurement = "min"

    @property
    def native_value(self) -> float:
        """Return the current timer value."""
        # Get from DP 167 (oem_hob_timer_num) bitfield
        raw_data = self._device._status.get("167", b'')
        if raw_data:
            timers = decode_zone_bitfield(raw_data)
            return float(timers.get(self._zone, 0))
        return 0.0

    async def async_set_native_value(self, value: float) -> None:
        """Set the timer."""
        # Get current timers
        raw_data = self._device._status.get("167", b'')
        timers = decode_zone_bitfield(raw_data) if raw_data else {i: 0 for i in range(1, 6)}

        # Update this zone's timer
        timers[self._zone] = int(value)

        # Encode and send
        encoded = encode_zone_bitfield(timers)
        self._device._device.set_value(167, encoded)
        self.async_write_ha_state()

async def async_setup_entry_switch(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up cooktop switch entities."""
    if entry.data.get(CONF_TYPE) != "cooktop":
        return

    device = hass.data[DOMAIN][entry.entry_id]["device"]
    entities = [
        CooktopMainSwitch(entry, device),
        CooktopChildLock(entry, device),
        CooktopPause(entry, device),
        CooktopSeniorMode(entry, device),
    ]

    # Add zone-specific switches
    for zone in range(1, 6):
        entities.append(CooktopZoneBoost(entry, device, zone))
        entities.append(CooktopZoneWarm(entry, device, zone))
    async_add_entities(entities)

class CooktopMainSwitch(SwitchEntity):
    """Main power switch for cooktop."""

    def __init__(self, entry: ConfigEntry, device):
        """Initialize the switch."""
        self._entry = entry
        self._device = device
        self._attr_unique_id = f"{entry.entry_id}_cooktop_power"
        self._attr_name = "KKT Cooktop Power"
        self._attr_icon = "mdi:power"

    @property
    def is_on(self) -> bool:
        """Return if cooktop is on."""
        return self._device._status.get("101", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on cooktop."""
        self._device._device.set_value(101, True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off cooktop."""
        self._device._device.set_value(101, False)
        self.async_write_ha_state()

class CooktopChildLock(SwitchEntity):
    """Child lock for cooktop."""

    def __init__(self, entry: ConfigEntry, device):
        """Initialize the switch."""
        self._entry = entry
        self._device = device
        self._attr_unique_id = f"{entry.entry_id}_child_lock"
        self._attr_name = "KKT Cooktop Child Lock"
        self._attr_icon = "mdi:lock-outline"

    @property
    def is_on(self) -> bool:
        """Return if child lock is on."""
        return self._device._status.get("103", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable child lock."""
        self._device._device.set_value(103, True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable child lock."""
        self._device._device.set_value(103, False)
        self.async_write_ha_state()

class CooktopPause(SwitchEntity):
    """Pause function for cooktop."""

    def __init__(self, entry: ConfigEntry, device):
        """Initialize the switch."""
        self._entry = entry
        self._device = device
        self._attr_unique_id = f"{entry.entry_id}_pause"
        self._attr_name = "KKT Cooktop Pause"
        self._attr_icon = "mdi:pause"

    @property
    def is_on(self) -> bool:
        """Return if pause is active."""
        return self._device._status.get("102", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Activate pause."""
        self._device._device.set_value(102, True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Deactivate pause."""
        self._device._device.set_value(102, False)
        self.async_write_ha_state()

class CooktopSeniorMode(SwitchEntity):
    """Senior/Old people mode for cooktop."""

    def __init__(self, entry: ConfigEntry, device):
        """Initialize the switch."""
        self._entry = entry
        self._device = device
        self._attr_unique_id = f"{entry.entry_id}_senior_mode"
        self._attr_name = "KKT Cooktop Senior Mode"
        self._attr_icon = "mdi:account"

    @property
    def is_on(self) -> bool:
        """Return if senior mode is active."""
        return self._device._status.get("145", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Activate senior mode."""
        self._device._device.set_value(145, True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Deactivate senior mode."""
        self._device._device.set_value(145, False)
        self.async_write_ha_state()

class CooktopZoneBoost(SwitchEntity):
    """Boost mode for specific zone."""

    def __init__(self, entry: ConfigEntry, device, zone: int):
        """Initialize the switch."""
        self._entry = entry
        self._device = device
        self._zone = zone
        self._attr_unique_id = f"{entry.entry_id}_zone{zone}_boost"
        self._attr_name = f"KKT Zone {zone} Boost"
        self._attr_icon = "mdi:flash"

    @property
    def is_on(self) -> bool:
        """Return if boost is active for this zone."""
        raw_data = self._device._status.get("163", b"")
        if raw_data:
            flags = decode_zone_flags(raw_data)
            return flags.get(self._zone, False)
        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Activate boost for this zone."""
        raw_data = self._device._status.get("163", b"")
        flags = decode_zone_flags(raw_data) if raw_data else {i: False for i in range(1, 6)}
        flags[self._zone] = True
        encoded = encode_zone_flags(flags)
        self._device._device.set_value(163, encoded)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Deactivate boost for this zone."""
        raw_data = self._device._status.get("163", b"")
        flags = decode_zone_flags(raw_data) if raw_data else {i: False for i in range(1, 6)}
        flags[self._zone] = False
        encoded = encode_zone_flags(flags)
        self._device._device.set_value(163, encoded)
        self.async_write_ha_state()

class CooktopZoneWarm(SwitchEntity):
    """Keep warm mode for specific zone."""

    def __init__(self, entry: ConfigEntry, device, zone: int):
        """Initialize the switch."""
        self._entry = entry
        self._device = device
        self._zone = zone
        self._attr_unique_id = f"{entry.entry_id}_zone{zone}_warm"
        self._attr_name = f"KKT Zone {zone} Keep Warm"
        self._attr_icon = "mdi:radiator"

    @property
    def is_on(self) -> bool:
        """Return if keep warm is active for this zone."""
        raw_data = self._device._status.get("164", b"")
        if raw_data:
            flags = decode_zone_flags(raw_data)
            return flags.get(self._zone, False)
        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Activate keep warm for this zone."""
        raw_data = self._device._status.get("164", b"")
        flags = decode_zone_flags(raw_data) if raw_data else {i: False for i in range(1, 6)}
        flags[self._zone] = True
        encoded = encode_zone_flags(flags)
        self._device._device.set_value(164, encoded)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Deactivate keep warm for this zone."""
        raw_data = self._device._status.get("164", b"")
        flags = decode_zone_flags(raw_data) if raw_data else {i: False for i in range(1, 6)}
        flags[self._zone] = False
        encoded = encode_zone_flags(flags)
        self._device._device.set_value(164, encoded)
        self.async_write_ha_state()

class CooktopZoneQuickLevel(SelectEntity):
    """Quick level preset for specific zone."""

    def __init__(self, entry: ConfigEntry, device, zone: int):
        """Initialize the selector."""
        self._entry = entry
        self._device = device
        self._zone = zone
        self._attr_unique_id = f"{entry.entry_id}_zone{zone}_quick"
        self._attr_name = f"KKT Zone {zone} Quick Level"
        self._attr_icon = "mdi:speedometer"
        self._attr_options = ["Level 1", "Level 2", "Level 3", "Level 4", "Level 5"]

    @property
    def current_option(self) -> str:
        """Return the current quick level."""
        dp_index = 147 + self._zone  # DPs 148-152
        value = self._device._status.get(str(dp_index), "")
        if value in QUICK_LEVELS:
            return f"Level {QUICK_LEVELS.index(value) + 1}"
        return "Level 1"

    async def async_select_option(self, option: str) -> None:
        """Set the quick level."""
        level_num = int(option.split()[-1]) - 1
        if 0 <= level_num < len(QUICK_LEVELS):
            dp_index = 147 + self._zone
            self._device._device.set_value(dp_index, QUICK_LEVELS[level_num])
            self.async_write_ha_state()

class CooktopGeneralTimer(NumberEntity):
    """General countdown timer for cooktop."""

    def __init__(self, entry: ConfigEntry, device):
        """Initialize the timer."""
        self._entry = entry
        self._device = device
        self._attr_unique_id = f"{entry.entry_id}_general_timer"
        self._attr_name = "KKT Cooktop General Timer"
        self._attr_icon = "mdi:timer-outline"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 99
        self._attr_native_step = 1
        self._attr_native_unit_of_measurement = "min"

    @property
    def native_value(self) -> float:
        """Return the current timer value."""
        return float(self._device._status.get("134", 0))

    async def async_set_native_value(self, value: float) -> None:
        """Set the timer."""
        self._device._device.set_value(134, int(value))
        self.async_write_ha_state()
