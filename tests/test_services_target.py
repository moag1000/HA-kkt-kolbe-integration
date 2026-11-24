"""End-to-end tests of the KKT Kolbe actions through hass.services.async_call.

Every action is called the way the UI, scripts and Assist call it: with a
``target`` and through the real registration and schema, on entities that
were created by really setting up the config entry. Nothing on the service
path is patched; only the Tuya device (the network) is faked.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock
from unittest.mock import patch

import probatio as vol
import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kkt_kolbe.bitfield_utils import extract_zone_value_from_bitfield
from custom_components.kkt_kolbe.const import DOMAIN

HOOD_ID = "bf735dfe2ad64fba7cpyhn"
SOLO_ID = "bf735dfe2ad64fba7csolo"
COOKTOP_ID = "bf5592b47738c5b46evzff"


class FakeTuyaDevice:
    """A Tuya device that answers locally and records every write."""

    def __init__(self, device_id: str, ip_address: str, local_key: str, *args: Any, **kwargs: Any) -> None:
        self.device_id = device_id
        self.ip_address = ip_address
        self.local_key = local_key
        self.version = "3.3"
        self.is_connected = True
        self.status: dict[str, Any] = dict(INITIAL_STATUS.get(device_id, {}))
        self.writes: list[tuple[int, Any]] = []
        self.async_connect = AsyncMock()
        self.async_disconnect = AsyncMock()
        self.async_test_connection = AsyncMock(return_value=True)
        DEVICES[device_id] = self

    def add_status_listener(self, listener: Any) -> Any:
        return lambda: None

    async def async_get_status(self) -> dict[str, Any]:
        return dict(self.status)

    async def async_set_dp(self, dp: int, value: Any) -> bool:
        self.writes.append((dp, value))
        return True


INITIAL_STATUS: dict[str, dict[str, Any]] = {}
# DP 162: power level of the five cooktop zones, one byte each (Base64 RAW)
ZONES_OFF = "AAAAAAA="
DEVICES: dict[str, FakeTuyaDevice] = {}


def _entry(device_id: str, device_type: str, title: str) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title=title,
        data={
            "device_id": device_id,
            "ip_address": "192.168.1.100",
            "local_key": "1234567890abcdef",
            "integration_mode": "manual",
            "product_name": device_type,
            "device_type": device_type,
        },
        unique_id=device_id,
        version=1,
    )


@pytest.fixture
async def devices(hass: HomeAssistant) -> AsyncGenerator[dict[str, MockConfigEntry]]:
    """Set up a hood and a cooktop entry with all their platforms."""
    INITIAL_STATUS.clear()
    DEVICES.clear()
    INITIAL_STATUS[HOOD_ID] = {"1": False, "4": False, "5": 0, "10": "off", "13": 0, "15": False}
    INITIAL_STATUS[COOKTOP_ID] = {"101": True, "162": ZONES_OFF}
    hood = _entry(HOOD_ID, "hermes_style_hood", "Hood")
    cooktop = _entry(COOKTOP_ID, "ind7705hc_cooktop", "Cooktop")
    with (
        patch("custom_components.kkt_kolbe.tuya_device.KKTKolbeTuyaDevice", FakeTuyaDevice),
        patch("custom_components.kkt_kolbe.coordinator.CLOUD_PROPAGATION_DELAY_SECONDS", 3600),
    ):
        for entry in (hood, cooktop):
            entry.add_to_hass(hass)
            assert await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()
            assert entry.state is ConfigEntryState.LOADED
        yield {"hood": hood, "cooktop": cooktop}


async def _call(hass: HomeAssistant, service: str, data: dict[str, Any] | None = None, **kwargs: Any) -> Any:
    return await hass.services.async_call(DOMAIN, service, data or {}, blocking=True, **kwargs)


def _entity_id(hass: HomeAssistant, entry: MockConfigEntry, platform: str, unique_suffix: str) -> str:
    registry = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        if entity.domain == platform and entity.unique_id.endswith(unique_suffix):
            return entity.entity_id
    raise AssertionError(f"no {platform} entity ending in {unique_suffix}")


def _device_id(hass: HomeAssistant, tuya_id: str) -> str:
    device = next(iter(dr.async_get(hass).async_get_devices(identifiers={(DOMAIN, tuya_id)})), None)
    assert device is not None
    return device.id


def _zone_levels(raw: str) -> list[int]:
    return [extract_zone_value_from_bitfield(raw, zone) for zone in range(1, 6)]


# --- Entity actions (target = entity) --------------------------------------


async def test_set_cooking_timer_with_target(hass: HomeAssistant, devices) -> None:
    """set_cooking_timer writes the timer DP of the targeted Timer entity."""
    timer = _entity_id(hass, devices["hood"], "number", "_number_dp13_timer")

    await _call(hass, "set_cooking_timer", {"timer_minutes": 15}, target={"entity_id": timer})

    assert DEVICES[HOOD_ID].writes == [(13, 15)]
    assert hass.states.get(timer).state == "15.0"


async def test_set_cooking_timer_rejects_wrong_kind(hass: HomeAssistant, devices) -> None:
    """A number action on another kind of number entity is refused, nothing is written."""
    zone_power = _entity_id(hass, devices["cooktop"], "number", "_zone1_zone_1:_power_level")

    with pytest.raises(ServiceValidationError) as err:
        await _call(hass, "set_cooking_timer", {"timer_minutes": 5}, target={"entity_id": zone_power})

    assert err.value.translation_key == "entity_wrong_kind"
    assert DEVICES[COOKTOP_ID].writes == []


async def test_set_zone_power_with_target_keeps_other_pending_zone(hass: HomeAssistant, devices) -> None:
    """Two zones set back to back: the second write keeps the first zone's new level.

    DP 162 holds all five zones. Building the second write from the last
    *reported* value (instead of the pending one) used to reset zone 1.
    """
    zone1 = _entity_id(hass, devices["cooktop"], "number", "_zone1_zone_1:_power_level")
    zone2 = _entity_id(hass, devices["cooktop"], "number", "_zone2_zone_2:_power_level")

    await _call(hass, "set_zone_power", {"power_level": 7}, target={"entity_id": zone1})
    await _call(hass, "set_zone_power", {"power_level": 4}, target={"entity_id": zone2})

    writes = DEVICES[COOKTOP_ID].writes
    assert [dp for dp, _ in writes] == [162, 162]
    assert _zone_levels(writes[0][1]) == [7, 0, 0, 0, 0]
    assert _zone_levels(writes[1][1]) == [7, 4, 0, 0, 0]
    # Both zone entities show their new value before the device confirms
    assert hass.states.get(zone1).state == "7.0"
    assert hass.states.get(zone2).state == "4.0"


async def test_set_zone_power_refuses_unknown_zone_state(hass: HomeAssistant, devices) -> None:
    """Without a reported DP 162 the other zones are unknown: refuse instead of zeroing them."""
    coordinator = devices["cooktop"].runtime_data.coordinator
    coordinator.async_set_updated_data({"101": True})
    zone1 = _entity_id(hass, devices["cooktop"], "number", "_zone1_zone_1:_power_level")

    with pytest.raises(HomeAssistantError) as err:
        await _call(hass, "set_zone_power", {"power_level": 3}, target={"entity_id": zone1})

    assert err.value.translation_key == "zone_state_unknown"
    assert DEVICES[COOKTOP_ID].writes == []


async def test_set_zone_power_out_of_entity_range(hass: HomeAssistant, devices) -> None:
    """The schema allows 0-25, the zone entity decides its own range."""
    zone1 = _entity_id(hass, devices["cooktop"], "number", "_zone1_zone_1:_power_level")
    with pytest.raises(vol.Invalid):
        await _call(hass, "set_zone_power", {"power_level": 26}, target={"entity_id": zone1})
    assert DEVICES[COOKTOP_ID].writes == []


async def test_set_hood_fan_speed_with_device_target(hass: HomeAssistant) -> None:
    """set_hood_fan_speed accepts the full 0-9 range of numeric hoods, via a device target."""
    INITIAL_STATUS.clear()
    DEVICES.clear()
    INITIAL_STATUS[SOLO_ID] = {"1": True, "102": 0}
    entry = _entry(SOLO_ID, "solo_hcm_hood", "Solo")
    entry.add_to_hass(hass)
    with (
        patch("custom_components.kkt_kolbe.tuya_device.KKTKolbeTuyaDevice", FakeTuyaDevice),
        patch("custom_components.kkt_kolbe.coordinator.CLOUD_PROPAGATION_DELAY_SECONDS", 3600),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        # The Fan Speed number is an advanced entity: enable it like a user would
        fan_speed = _entity_id(hass, entry, "number", "_number_dp102_fan_speed")
        er.async_get(hass).async_update_entity(fan_speed, disabled_by=None)
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()

        await _call(hass, "set_hood_fan_speed", {"fan_speed": 8}, target={"entity_id": fan_speed})

    assert DEVICES[SOLO_ID].writes == [(102, 8)]


async def test_set_hood_fan_speed_rejects_timer_entity(hass: HomeAssistant, devices) -> None:
    """The Timer number of the hood is not a fan speed entity."""
    timer = _entity_id(hass, devices["hood"], "number", "_number_dp13_timer")
    with pytest.raises(ServiceValidationError):
        await _call(hass, "set_hood_fan_speed", {"fan_speed": 2}, target={"entity_id": timer})
    assert DEVICES[HOOD_ID].writes == []


async def test_set_hood_lighting_with_target_sets_brightness(hass: HomeAssistant, devices) -> None:
    """Brightness level 3 of 5 turns the light on and sets the brightness DP."""
    light = _entity_id(hass, devices["hood"], "light", "_light_dp4_light")

    await _call(hass, "set_hood_lighting", {"brightness": 3}, target={"entity_id": light})

    writes = DEVICES[HOOD_ID].writes
    assert (4, True) in writes
    assert (5, 153) in writes  # round(3 * 255 / 5)
    assert hass.states.get(light).state == "on"


async def test_set_hood_lighting_without_brightness_toggles(hass: HomeAssistant, devices) -> None:
    """Without brightness the light toggles (off -> on)."""
    light = _entity_id(hass, devices["hood"], "light", "_light_dp4_light")
    await _call(hass, "set_hood_lighting", target={"entity_id": light})
    assert (4, True) in DEVICES[HOOD_ID].writes


@pytest.mark.parametrize("target_kind", ["device", "power_switch"])
async def test_set_hood_lighting_other_targets_use_main_light(hass: HomeAssistant, devices, target_kind) -> None:
    """The device or another hood entity (older automations named the switch) selects the main light.

    Regression: with the action bound to light entities, such targets were
    silently skipped and the call did nothing.
    """
    if target_kind == "device":
        target = {"device_id": _device_id(hass, HOOD_ID)}
    else:
        target = {"entity_id": _entity_id(hass, devices["hood"], "switch", "_switch_dp1_power")}

    await _call(hass, "set_hood_lighting", {"brightness": 3}, target=target)

    assert (4, True) in DEVICES[HOOD_ID].writes
    assert (5, 153) in DEVICES[HOOD_ID].writes


async def test_set_hood_lighting_without_hood_is_refused(hass: HomeAssistant, devices) -> None:
    """A target without any hood light raises instead of doing nothing."""
    with pytest.raises(ServiceValidationError) as err:
        await _call(hass, "set_hood_lighting", {"brightness": 2}, target={"device_id": _device_id(hass, COOKTOP_ID)})
    assert err.value.translation_key == "no_matching_devices"
    with pytest.raises(vol.Invalid):
        await _call(hass, "set_hood_lighting", {"brightness": 2})


async def test_entity_action_accepts_legacy_entity_id_in_data(hass: HomeAssistant, devices) -> None:
    """Older scripts pass entity_id in the data instead of a target."""
    timer = _entity_id(hass, devices["hood"], "number", "_number_dp13_timer")
    await _call(hass, "set_cooking_timer", {"entity_id": timer, "timer_minutes": 9})
    assert DEVICES[HOOD_ID].writes == [(13, 9)]


# --- Device actions (target = device) --------------------------------------


async def test_reset_filter_timer_with_device_target(hass: HomeAssistant, devices) -> None:
    """The Filter Reset DP of the hood profile (DP 15) is written."""
    await _call(hass, "reset_filter_timer", {"confirm": True}, target={"device_id": _device_id(hass, HOOD_ID)})
    assert DEVICES[HOOD_ID].writes == [(15, True)]


async def test_reset_filter_timer_with_entity_target(hass: HomeAssistant, devices) -> None:
    """Any entity of the hood selects the hood (the old entity_id field)."""
    light = _entity_id(hass, devices["hood"], "light", "_light_dp4_light")
    await _call(hass, "reset_filter_timer", {"entity_id": light, "confirm": True})
    assert DEVICES[HOOD_ID].writes == [(15, True)]


async def test_reset_filter_timer_refuses_device_without_filter_reset(hass: HomeAssistant, devices) -> None:
    """A cooktop has no filter reset: nothing is written (DP 15 used to be written blindly)."""
    with pytest.raises(ServiceValidationError) as err:
        await _call(hass, "reset_filter_timer", {"confirm": True}, target={"device_id": _device_id(hass, COOKTOP_ID)})
    assert err.value.translation_key == "filter_reset_not_supported"
    assert DEVICES[COOKTOP_ID].writes == []


async def test_reset_filter_timer_requires_target_and_confirm(hass: HomeAssistant, devices) -> None:
    """The schema needs a target; confirm false is refused."""
    with pytest.raises(vol.Invalid):
        await _call(hass, "reset_filter_timer", {"confirm": True})
    with pytest.raises(ServiceValidationError):
        await _call(hass, "reset_filter_timer", {"confirm": False}, target={"device_id": _device_id(hass, HOOD_ID)})
    assert DEVICES[HOOD_ID].writes == []


async def test_reconnect_device_with_device_target(hass: HomeAssistant, devices) -> None:
    """Only the targeted device reconnects."""
    for device in DEVICES.values():
        device.async_connect.reset_mock()

    await _call(hass, "reconnect_device", target={"device_id": _device_id(hass, HOOD_ID)})

    DEVICES[HOOD_ID].async_connect.assert_awaited()
    DEVICES[COOKTOP_ID].async_connect.assert_not_awaited()


async def test_reconnect_device_accepts_tuya_device_id(hass: HomeAssistant, devices) -> None:
    """Older automations pass the Tuya device id as device_id."""
    for device in DEVICES.values():
        device.async_connect.reset_mock()
    await _call(hass, "reconnect_device", {"device_id": COOKTOP_ID})
    DEVICES[COOKTOP_ID].async_connect.assert_awaited()
    DEVICES[HOOD_ID].async_connect.assert_not_awaited()


async def test_get_connection_status_with_device_target(hass: HomeAssistant, devices) -> None:
    """The response holds only the targeted device."""
    response = await _call(
        hass,
        "get_connection_status",
        target={"device_id": _device_id(hass, COOKTOP_ID)},
        return_response=True,
    )
    assert list(response["statuses"]) == [devices["cooktop"].entry_id]

    everything = await _call(hass, "get_connection_status", return_response=True)
    assert set(everything["statuses"]) == {entry.entry_id for entry in devices.values()}


async def test_get_firmware_info_with_device_target(hass: HomeAssistant, devices) -> None:
    """Firmware info is queried for the targeted device only."""
    response = await _call(
        hass, "get_firmware_info", target={"device_id": _device_id(hass, HOOD_ID)}, return_response=True
    )
    assert [device["entry_id"] for device in response["devices"]] == [devices["hood"].entry_id]


async def test_update_local_key_with_device_target(hass: HomeAssistant, devices) -> None:
    """The key is tested, stored in both entry fields and the entry reloads with it."""
    hood = devices["hood"]
    new_key = "fedcba0987654321"
    with (
        patch("custom_components.kkt_kolbe.tuya_device.KKTKolbeTuyaDevice", FakeTuyaDevice),
        patch("custom_components.kkt_kolbe.coordinator.CLOUD_PROPAGATION_DELAY_SECONDS", 3600),
    ):
        await _call(hass, "update_local_key", {"local_key": new_key}, target={"device_id": _device_id(hass, HOOD_ID)})
        await hass.async_block_till_done()

    assert hood.data["local_key"] == new_key
    assert hood.data[CONF_ACCESS_TOKEN] == new_key
    assert hood.state is ConfigEntryState.LOADED
    # The reloaded entry connects with the new key
    assert hood.runtime_data.device.local_key == new_key
    assert devices["cooktop"].data["local_key"] == "1234567890abcdef"


async def test_update_local_key_requires_a_device(hass: HomeAssistant, devices) -> None:
    """One key never goes to all devices: a target (or entry_id) is required."""
    with pytest.raises(ServiceValidationError) as err:
        await _call(hass, "update_local_key", {"local_key": "fedcba0987654321"})
    assert err.value.translation_key == "target_required"
    with pytest.raises(vol.Invalid):
        await _call(hass, "update_local_key", {"local_key": "short"}, target={"device_id": _device_id(hass, HOOD_ID)})


# --- Integration-wide actions (no target) ----------------------------------


async def test_bulk_power_off_hoods_only(hass: HomeAssistant, devices) -> None:
    """The hood's power switch is turned off through switch.turn_off; the cooktop stays on."""
    await _call(hass, "bulk_power_off", {"device_types": ["hood"], "confirm": True})

    assert DEVICES[HOOD_ID].writes == [(1, False)]
    assert DEVICES[COOKTOP_ID].writes == []


async def test_emergency_stop_turns_off_all_devices(hass: HomeAssistant, devices) -> None:
    """Every device is powered off via its profile power switch (DP 1 hood, DP 101 cooktop)."""
    await _call(hass, "emergency_stop", {"confirm": True, "notification": False})

    assert DEVICES[HOOD_ID].writes == [(1, False)]
    assert DEVICES[COOKTOP_ID].writes == [(101, False)]
    cooktop_power = _entity_id(hass, devices["cooktop"], "switch", "_switch_dp101_power")
    assert hass.states.get(cooktop_power).state == "off"


async def test_emergency_stop_with_disabled_power_switch(hass: HomeAssistant, devices) -> None:
    """A disabled power switch does not exempt the device from an emergency stop.

    Regression: switch.turn_off skips disabled entities without an error.
    """
    registry = er.async_get(hass)
    cooktop_power = _entity_id(hass, devices["cooktop"], "switch", "_switch_dp101_power")
    registry.async_update_entity(cooktop_power, disabled_by=er.RegistryEntryDisabler.USER)
    await hass.async_block_till_done()

    await _call(hass, "emergency_stop", {"confirm": True, "notification": False})

    assert DEVICES[COOKTOP_ID].writes == [(101, False)]
    assert DEVICES[HOOD_ID].writes == [(1, False)]


async def test_emergency_stop_reports_failures(hass: HomeAssistant, devices) -> None:
    """A failed write is raised, not swallowed."""
    DEVICES[COOKTOP_ID].async_set_dp = AsyncMock(side_effect=OSError("socket closed"))
    with pytest.raises(HomeAssistantError):
        await _call(hass, "emergency_stop", {"confirm": True, "notification": False})


async def test_sync_all_devices(hass: HomeAssistant, devices) -> None:
    """All coordinators refresh; an unknown filter is refused by the schema."""
    await _call(hass, "sync_all_devices", {"device_filter": "all"})
    with pytest.raises(vol.Invalid):
        await _call(hass, "sync_all_devices", {"device_filter": "sometimes"})


async def test_integration_wide_actions_reject_a_target(hass: HomeAssistant, devices) -> None:
    """Actions without a target in services.yaml do not silently ignore one."""
    with pytest.raises(vol.Invalid):
        await _call(hass, "sync_all_devices", target={"device_id": _device_id(hass, HOOD_ID)})
    with pytest.raises(vol.Invalid):
        await _call(hass, "download_device_icons", {"entity_id": "light.x"})


async def test_rescan_devices(hass: HomeAssistant, devices) -> None:
    """The timeout is validated and passed on."""
    with patch("custom_components.kkt_kolbe.discovery.simple_tuya_discover", new_callable=AsyncMock) as discover:
        await _call(hass, "rescan_devices", {"timeout": 4})
    discover.assert_awaited_once_with(timeout=4)
    with pytest.raises(vol.Invalid):
        await _call(hass, "rescan_devices", {"timeout": 300})


async def test_refresh_smartlife_cache_and_download_icons(hass: HomeAssistant, devices) -> None:
    """Both run through their schemas (local-only devices: nothing to do)."""
    await _call(hass, "refresh_smartlife_cache")
    await _call(hass, "download_device_icons", {"force": True})


# --- Shared state of one device (pending writes) ----------------------------


async def test_fan_turn_on_shows_hood_power_at_once(hass: HomeAssistant, devices) -> None:
    """fan.turn_on on a hood that is off: power switch and fan both show on at once.

    The fan's auto power-on writes DP 1. With the optimistic state kept per
    entity, the fan (which derives is_on from DP 1) and the power switch kept
    showing "off" until the device confirmed.
    """
    fan = _entity_id(hass, devices["hood"], "fan", "_fan_dp10_fan")
    power = _entity_id(hass, devices["hood"], "switch", "_switch_dp1_power")

    with patch("custom_components.kkt_kolbe.fan.POWER_ON_DELAY", 0):
        await hass.services.async_call("fan", "turn_on", {"entity_id": fan, "percentage": 50}, blocking=True)

    assert DEVICES[HOOD_ID].writes[0] == (1, True)
    assert hass.states.get(power).state == "on"
    assert hass.states.get(fan).state == "on"


async def test_pending_write_released_by_device_report(hass: HomeAssistant, devices) -> None:
    """Once the device reports, its value counts again (also a later physical change)."""
    power = _entity_id(hass, devices["hood"], "switch", "_switch_dp1_power")
    coordinator = devices["hood"].runtime_data.coordinator

    with patch("custom_components.kkt_kolbe.switch.POWER_ON_DELAY", 0):
        await hass.services.async_call("switch", "turn_on", {"entity_id": power}, blocking=True)
    coordinator.async_set_updated_data({**INITIAL_STATUS[HOOD_ID], "1": False})  # stale poll
    assert hass.states.get(power).state == "on"

    coordinator.async_set_updated_data({**INITIAL_STATUS[HOOD_ID], "1": True})  # confirmed
    coordinator.async_set_updated_data({**INITIAL_STATUS[HOOD_ID], "1": False})  # button on the hood
    assert hass.states.get(power).state == "off"


async def test_pending_write_released_by_other_representation(hass: HomeAssistant, devices) -> None:
    """A device that reports True as "true" (or 3 as "3") confirms the write too."""
    power = _entity_id(hass, devices["hood"], "switch", "_switch_dp1_power")
    coordinator = devices["hood"].runtime_data.coordinator

    with patch("custom_components.kkt_kolbe.switch.POWER_ON_DELAY", 0):
        await hass.services.async_call("switch", "turn_on", {"entity_id": power}, blocking=True)
    coordinator.async_set_updated_data({**INITIAL_STATUS[HOOD_ID], "1": "true"})  # confirmed, as text
    coordinator.async_set_updated_data({**INITIAL_STATUS[HOOD_ID], "1": False})  # button on the hood
    assert hass.states.get(power).state == "off"


# --- Lifecycle ---------------------------------------------------------------


async def test_reload_keeps_discovery_running_until_ha_stops(hass: HomeAssistant, devices) -> None:
    """Unloading the last device entry no longer stops discovery for good."""
    with patch("custom_components.kkt_kolbe.discovery.async_stop_discovery", new_callable=AsyncMock) as stop:
        for entry in devices.values():
            assert await hass.config_entries.async_unload(entry.entry_id)
        stop.assert_not_awaited()

        hass.bus.async_fire(EVENT_HOMEASSISTANT_STOP)
        await hass.async_block_till_done()
        stop.assert_awaited_once()


async def test_removing_last_device_frees_discovery_ports(hass: HomeAssistant, devices) -> None:
    """Deleting (not reloading) the last device entry stops discovery."""
    with patch("custom_components.kkt_kolbe.discovery.async_stop_discovery", new_callable=AsyncMock) as stop:
        await hass.config_entries.async_remove(devices["hood"].entry_id)
        stop.assert_not_awaited()
        await hass.config_entries.async_remove(devices["cooktop"].entry_id)
        stop.assert_awaited_once()
