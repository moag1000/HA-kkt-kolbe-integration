"""Services for KKT Kolbe integration."""

from __future__ import annotations

import contextlib
import logging
from functools import partial
from typing import Any

import probatio as vol
from homeassistant.components.light import ATTR_BRIGHTNESS
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.number import DOMAIN as NUMBER_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_AREA_ID
from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.const import ATTR_FLOOR_ID
from homeassistant.const import ATTR_LABEL_ID
from homeassistant.const import ENTITY_MATCH_NONE
from homeassistant.const import SERVICE_TURN_OFF
from homeassistant.core import HomeAssistant
from homeassistant.core import ServiceCall
from homeassistant.core import ServiceResponse
from homeassistant.core import SupportsResponse
from homeassistant.core import callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import service as service_helper
from homeassistant.helpers.json import json_dumps
from homeassistant.util.json import json_loads

from .base_entity import entity_unique_id
from .const import CATEGORY_COOKTOP
from .const import CATEGORY_HOOD
from .const import DOMAIN
from .device_types import get_device_entities
from .exceptions import KKTServiceError
from .helpers.local_key import entry_data_with_local_key

_LOGGER = logging.getLogger(__name__)


def _validation_error(key: str, **placeholders: str) -> ServiceValidationError:
    """Build a translated ServiceValidationError (quality scale: exception-translations)."""
    return ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key=key,
        translation_placeholders=placeholders,
    )


def _loaded_device_entries(hass: HomeAssistant) -> list[ConfigEntry]:
    """Return loaded KKT Kolbe device entries (account entries excluded).

    Replaces the former ``hass.data[DOMAIN]`` registry: everything a service
    needs lives on ``entry.runtime_data`` (KKTKolbeRuntimeData).
    """
    return [
        entry
        for entry in hass.config_entries.async_loaded_entries(DOMAIN)
        if getattr(getattr(entry, "runtime_data", None), "coordinator", None) is not None
    ]


# Service names
SERVICE_SET_COOKING_TIMER = "set_cooking_timer"
SERVICE_SET_ZONE_POWER = "set_zone_power"
SERVICE_BULK_POWER_OFF = "bulk_power_off"
SERVICE_SYNC_ALL_DEVICES = "sync_all_devices"
SERVICE_SET_HOOD_FAN_SPEED = "set_hood_fan_speed"
SERVICE_SET_HOOD_LIGHTING = "set_hood_lighting"
SERVICE_EMERGENCY_STOP = "emergency_stop"
SERVICE_RESET_FILTER_TIMER = "reset_filter_timer"
SERVICE_RECONNECT_DEVICE = "reconnect_device"
SERVICE_UPDATE_LOCAL_KEY = "update_local_key"
SERVICE_GET_CONNECTION_STATUS = "get_connection_status"
SERVICE_RESCAN_DEVICES = "rescan_devices"
SERVICE_DOWNLOAD_DEVICE_ICONS = "download_device_icons"
SERVICE_REFRESH_SMARTLIFE_CACHE = "refresh_smartlife_cache"
SERVICE_GET_FIRMWARE_INFO = "get_firmware_info"

# set_hood_lighting brightness levels (1-5), mapped onto HA's 0-255 scale
HOOD_LIGHT_LEVELS = 5


# Fields shared by the actions that act on selected devices. The target
# (device, entity, area, ...) is resolved to config entries by Home Assistant;
# ``entry_id`` stays as an alternative for older scripts.
_TARGET_FIELDS: dict[Any, Any] = {
    **cv.ENTITY_SERVICE_FIELDS,
    vol.Optional("entry_id"): cv.string,
}

_TARGET_KEYS = (ATTR_ENTITY_ID, ATTR_DEVICE_ID, ATTR_AREA_ID, ATTR_FLOOR_ID, ATTR_LABEL_ID)

RECONNECT_DEVICE_SCHEMA = vol.Schema(_TARGET_FIELDS)
GET_CONNECTION_STATUS_SCHEMA = vol.Schema(_TARGET_FIELDS)
GET_FIRMWARE_INFO_SCHEMA = vol.Schema(_TARGET_FIELDS)
UPDATE_LOCAL_KEY_SCHEMA = vol.Schema(
    {
        **_TARGET_FIELDS,
        vol.Required("local_key"): vol.All(cv.string, vol.Length(min=16, max=16)),
        vol.Optional("force_reconnect", default=True): cv.boolean,
        vol.Optional("reload_integration", default=False): cv.boolean,
    }
)
RESET_FILTER_TIMER_SCHEMA = cv.make_entity_service_schema({vol.Required("confirm"): cv.boolean})
BULK_POWER_OFF_SCHEMA = vol.Schema(
    {
        vol.Optional("device_types", default=["all"]): vol.All(cv.ensure_list, [vol.In(["all", "cooktop", "hood"])]),
        vol.Required("confirm"): cv.boolean,
    }
)
EMERGENCY_STOP_SCHEMA = vol.Schema(
    {
        vol.Required("confirm"): cv.boolean,
        vol.Optional("notification", default=True): cv.boolean,
    }
)
SYNC_ALL_DEVICES_SCHEMA = vol.Schema(
    {vol.Optional("device_filter", default="all"): vol.In(["all", "online_only", "offline_only"])}
)
RESCAN_DEVICES_SCHEMA = vol.Schema(
    {vol.Optional("timeout", default=6): vol.All(vol.Coerce(int), vol.Range(min=3, max=30))}
)
DOWNLOAD_DEVICE_ICONS_SCHEMA = vol.Schema({vol.Optional("force", default=False): cv.boolean})
REFRESH_SMARTLIFE_CACHE_SCHEMA = vol.Schema({})

DEVICE_TYPE_CATEGORIES = {"cooktop": CATEGORY_COOKTOP, "hood": CATEGORY_HOOD}

# Number entity actions: which profile entities they may target. The profile
# name (``config["name"]``) is the stable English name the unique_id is built
# from, unlike entity_ids and display names, which users rename and which
# follow the UI language.
_NUMBER_ACTION_KINDS: dict[str, str] = {
    SERVICE_SET_COOKING_TIMER: "timer",
    SERVICE_SET_ZONE_POWER: "power level",
    SERVICE_SET_HOOD_FAN_SPEED: "fan speed",
}


def _check_number_target(entity: Any, service_name: str, value: float) -> None:
    """Reject a number action on the wrong kind of entity or out of its range."""
    kind = _NUMBER_ACTION_KINDS[service_name]
    profile_name = str(getattr(entity, "_name", "")).lower()
    wrong_kind = kind not in profile_name or (
        service_name == SERVICE_SET_ZONE_POWER and getattr(entity, "_zone", None) is None
    )
    if wrong_kind:
        raise _validation_error("entity_wrong_kind", entity_id=entity.entity_id, kind=kind)
    if not entity.min_value <= value <= entity.max_value:
        raise _validation_error(
            "value_out_of_range",
            entity_id=entity.entity_id,
            value=f"{value:g}",
            min=f"{entity.min_value:g}",
            max=f"{entity.max_value:g}",
        )


async def _async_set_number(entity: Any, call: ServiceCall, field: str) -> None:
    """Set a KKT Kolbe number entity (zone timer, zone power, fan level)."""
    value = float(call.data[field])
    _check_number_target(entity, call.service, value)
    await entity.async_set_native_value(value)


async def _async_set_hood_lighting(entity: Any, call: ServiceCall) -> None:
    """Turn the hood light on at a brightness level (1-5), or toggle it."""
    level = call.data.get("brightness")
    if level is None:
        await entity.async_toggle()
        return
    await entity.async_turn_on(**{ATTR_BRIGHTNESS: round(level * 255 / HOOD_LIGHT_LEVELS)})


@callback
def _register_entity_actions(hass: HomeAssistant) -> None:
    """Register the platform entity actions of this integration.

    Home Assistant wraps the field dicts in ``cv.make_entity_service_schema``,
    so ``target`` (entity, device, area, ...) and ``entity_id`` in the data
    both work.
    """
    number_actions = {
        SERVICE_SET_COOKING_TIMER: ("timer_minutes", vol.All(vol.Coerce(int), vol.Range(min=1, max=255))),
        SERVICE_SET_ZONE_POWER: ("power_level", vol.All(vol.Coerce(int), vol.Range(min=0, max=25))),
        SERVICE_SET_HOOD_FAN_SPEED: ("fan_speed", vol.All(vol.Coerce(int), vol.Range(min=0, max=9))),
    }
    for service_name, (field, validator) in number_actions.items():
        service_helper.async_register_platform_entity_service(
            hass,
            DOMAIN,
            service_name,
            entity_domain=NUMBER_DOMAIN,
            schema={vol.Required(field): validator},
            func=partial(_async_set_number, field=field),
        )

    service_helper.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_SET_HOOD_LIGHTING,
        entity_domain=LIGHT_DOMAIN,
        schema={vol.Optional("brightness"): vol.All(vol.Coerce(int), vol.Range(min=1, max=HOOD_LIGHT_LEVELS))},
        func=_async_set_hood_lighting,
    )


def _has_target(call: ServiceCall) -> bool:
    """Return True if the call names a target (entity, device, area, ...)."""
    return any(call.data.get(key) not in (None, [], ENTITY_MATCH_NONE) for key in _TARGET_KEYS)


async def _async_target_entries(hass: HomeAssistant, call: ServiceCall) -> list[ConfigEntry]:
    """Return the loaded device entries an action call selects.

    No target and no ``entry_id`` selects all devices. ``device_id`` also
    accepts the Tuya device id, which older automations pass.
    """
    entries = _loaded_device_entries(hass)
    entry_id = call.data.get("entry_id")
    if not _has_target(call) and not entry_id:
        return entries

    selected: set[str] = {entry_id} if entry_id else set()
    if _has_target(call):
        selected |= await service_helper.async_extract_config_entry_ids(call)
        device_registry = dr.async_get(hass)
        tuya_ids = {
            device_id
            for device_id in call.data.get(ATTR_DEVICE_ID) or []
            if device_id != ENTITY_MATCH_NONE and device_registry.async_get(device_id) is None
        }
        selected |= {entry.entry_id for entry in entries if entry.data.get("device_id") in tuya_ids}
    return [entry for entry in entries if entry.entry_id in selected]


def _profile_switch_dp(entry: ConfigEntry, name: str) -> int | None:
    """Return the DP of the device profile's switch with this profile name."""
    runtime_data = entry.runtime_data
    lookup_key = runtime_data.device_type
    if lookup_key in ("auto", None, ""):
        lookup_key = runtime_data.product_name
    for config in get_device_entities(lookup_key, "switch"):
        if config.get("name") == name and isinstance(config.get("dp"), int):
            dp: int = config["dp"]
            return dp
    return None


def _power_switch_entity_ids(hass: HomeAssistant, entries: list[ConfigEntry]) -> list[str]:
    """Return the power switch entities of the given device entries."""
    entity_registry = er.async_get(hass)
    entity_ids: list[str] = []
    for entry in entries:
        dp = _profile_switch_dp(entry, "Power")
        if dp is None:
            continue
        entity_id = entity_registry.async_get_entity_id(
            SWITCH_DOMAIN, DOMAIN, entity_unique_id(entry.entry_id, SWITCH_DOMAIN, dp, "Power")
        )
        if entity_id is None:
            _LOGGER.warning("No power switch entity for %s, skipped", entry.title)
            continue
        entity_ids.append(entity_id)
    return entity_ids


async def _async_power_off(hass: HomeAssistant, entries: list[ConfigEntry]) -> list[str]:
    """Turn off the given devices through their power switch entities.

    Goes through ``switch.turn_off`` so the switch shows the change at once
    and a failure is raised to the caller instead of being swallowed.
    """
    entity_ids = _power_switch_entity_ids(hass, entries)
    if entity_ids:
        await hass.services.async_call(SWITCH_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: entity_ids}, blocking=True)
    return entity_ids


def _entry_category(entry: ConfigEntry) -> str:
    """Return the device category (hood, cooktop, ...) of a device entry."""
    return str(entry.runtime_data.device_info.get("category", "unknown"))


async def async_reconnect_coordinator(coordinator: Any) -> dict[str, Any]:
    """Reconnect the local connection of one coordinator.

    Shared by the ``reconnect_device`` action and the reconnect button.
    """
    if hasattr(coordinator, "async_request_reconnect"):
        success = await coordinator.async_request_reconnect()
        return {
            "success": success,
            "state": coordinator.device_state.value if hasattr(coordinator, "device_state") else "unknown",
        }
    if coordinator.device is None:
        return {
            "success": False,
            "error": "No local device available (API-only mode)",
            "state": "api_only",
        }
    await coordinator.device.async_disconnect()
    await coordinator.device.async_connect()
    await coordinator.async_request_refresh()
    return {
        "success": coordinator.device.is_connected,
        "state": "online" if coordinator.device.is_connected else "offline",
    }


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for KKT Kolbe integration."""

    async def handle_reconnect_device(service: ServiceCall) -> None:
        """Reconnect the local connection of the selected (or all) devices."""
        entries = await _async_target_entries(hass, service)
        if not entries:
            raise _validation_error("no_matching_devices")

        results: dict[str, Any] = {}
        for entry in entries:
            coordinator = entry.runtime_data.coordinator
            try:
                results[entry.entry_id] = await async_reconnect_coordinator(coordinator)
            except Exception as err:
                _LOGGER.error("Failed to reconnect %s: %s", entry.title, err)
                results[entry.entry_id] = {"success": False, "error": str(err)}
            else:
                _LOGGER.info("Reconnected %s: %s", entry.title, results[entry.entry_id])

        hass.bus.async_fire(f"{DOMAIN}_reconnect_complete", {"results": results})
        failed = [entry.title for entry in entries if results[entry.entry_id].get("error")]
        if failed:
            raise KKTServiceError(service_name=SERVICE_RECONNECT_DEVICE, reason=", ".join(failed))

    async def handle_update_local_key(service: ServiceCall) -> None:
        """Validate a new local key, store it and reload the device entry.

        The reload ends the old connection (with the old key) completely
        before the entry connects again with the new one, instead of patching
        the running connection.
        """
        if not _has_target(service) and not service.data.get("entry_id"):
            # One key belongs to one device: never apply it to all of them
            raise _validation_error("target_required", action=SERVICE_UPDATE_LOCAL_KEY)
        entries = await _async_target_entries(hass, service)
        if not entries:
            raise _validation_error("no_matching_devices")

        local_key: str = service.data["local_key"]
        reload_entry = service.data["force_reconnect"] or service.data["reload_integration"]
        results: dict[str, Any] = {}
        for entry in entries:
            device = entry.runtime_data.device
            device_id = entry.data.get("device_id") or ""
            if device is None:
                results[entry.entry_id] = {
                    "success": False,
                    "device_id": device_id,
                    "error": "No local device available (API-only mode). Cannot update local key.",
                }
                continue

            # Tuya devices accept only few local sessions: free ours for the test
            if device.is_connected:
                await device.async_disconnect()

            from .tuya_device import KKTKolbeTuyaDevice

            test_device = KKTKolbeTuyaDevice(device_id, entry.data.get("ip_address") or "", local_key, hass=hass)
            if not await test_device.async_test_connection():
                with contextlib.suppress(Exception):
                    await device.async_connect()
                results[entry.entry_id] = {
                    "success": False,
                    "device_id": device_id,
                    "error": "Invalid local key - connection test failed. Device may need to be reset in Tuya app.",
                }
                continue

            hass.config_entries.async_update_entry(entry, data=entry_data_with_local_key(entry.data, local_key))
            if reload_entry:
                await hass.config_entries.async_reload(entry.entry_id)
            else:
                with contextlib.suppress(Exception):
                    await device.async_connect()
            results[entry.entry_id] = {"success": True, "device_id": device_id, "reloaded": reload_entry}
            _LOGGER.info("Local key updated for %s", entry.title)

        hass.bus.async_fire(f"{DOMAIN}_local_key_updated", {"results": results})
        failed = [entry.title for entry in entries if not results[entry.entry_id]["success"]]
        if failed:
            raise KKTServiceError(service_name=SERVICE_UPDATE_LOCAL_KEY, reason=", ".join(failed))

    async def handle_get_connection_status(service: ServiceCall) -> ServiceResponse:
        """Return the connection status of the selected (or all) devices."""
        statuses: dict[str, Any] = {}
        for entry in await _async_target_entries(hass, service):
            coordinator = entry.runtime_data.coordinator
            if hasattr(coordinator, "connection_info"):
                statuses[entry.entry_id] = coordinator.connection_info
            elif coordinator.device is None:
                statuses[entry.entry_id] = {
                    "state": "api_only",
                    "last_update": coordinator.last_update_success_time,
                    "is_connected": False,
                    "device_id": "api_mode",
                    "ip_address": None,
                    "mode": "api_only",
                }
            else:
                statuses[entry.entry_id] = {
                    "state": "online" if coordinator.device.is_connected else "offline",
                    "last_update": coordinator.last_update_success_time,
                    "is_connected": coordinator.device.is_connected,
                    "device_id": coordinator.device.device_id,
                    "ip_address": coordinator.device.ip_address,
                }

        hass.bus.async_fire(f"{DOMAIN}_connection_status", {"statuses": statuses})

        # Action response: usable via ``response_variable`` in scripts. Round-trip
        # through JSON so datetimes etc. become plain strings.
        return {"statuses": json_loads(json_dumps(statuses))}

    async def async_bulk_power_off(call: ServiceCall) -> None:
        """Turn off all KKT Kolbe devices, or all of the chosen types."""
        if not call.data["confirm"]:
            raise _validation_error("confirm_required", action=SERVICE_BULK_POWER_OFF)

        device_types: list[str] = call.data["device_types"]
        entries = _loaded_device_entries(hass)
        if "all" not in device_types:
            categories = {DEVICE_TYPE_CATEGORIES[device_type] for device_type in device_types}
            entries = [entry for entry in entries if _entry_category(entry) in categories]

        turned_off = await _async_power_off(hass, entries)
        _LOGGER.info("Bulk power off: %d device(s) with filter %s", len(turned_off), device_types)

    async def async_sync_all_devices(call: ServiceCall) -> None:
        """Force refresh data for all KKT Kolbe devices."""
        device_filter = call.data["device_filter"]
        refreshed = 0
        for config_entry in _loaded_device_entries(hass):
            coordinator = config_entry.runtime_data.coordinator
            if (device_filter == "online_only" and not coordinator.last_update_success) or (
                device_filter == "offline_only" and coordinator.last_update_success
            ):
                continue
            await coordinator.async_request_refresh()
            refreshed += 1
        _LOGGER.info("Synchronized %d KKT Kolbe devices with filter '%s'", refreshed, device_filter)

    async def async_emergency_stop(call: ServiceCall) -> None:
        """Turn off every KKT Kolbe device (cooktops stop all zones and timers)."""
        if not call.data["confirm"]:
            raise _validation_error("confirm_required", action=SERVICE_EMERGENCY_STOP)

        turned_off = await _async_power_off(hass, _loaded_device_entries(hass))
        _LOGGER.warning("EMERGENCY STOP executed - %d device(s) turned off", len(turned_off))

        if call.data["notification"]:
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "KKT Kolbe Emergency Stop",
                    "message": f"Emergency stop executed - {len(turned_off)} device(s) turned off",
                    "notification_id": "kkt_kolbe_emergency_stop",
                },
                blocking=True,
            )

    async def async_reset_filter_timer(call: ServiceCall) -> None:
        """Reset the filter timer of the targeted range hood(s)."""
        if not call.data["confirm"]:
            raise _validation_error("confirm_required", action=SERVICE_RESET_FILTER_TIMER)

        entries = await _async_target_entries(hass, call)
        if not entries:
            raise _validation_error("no_matching_devices")

        # Validate every target first, so nothing is reset if one is wrong
        writes: list[tuple[ConfigEntry, int]] = []
        for entry in entries:
            dp = _profile_switch_dp(entry, "Filter Reset")
            if dp is None:
                raise _validation_error("filter_reset_not_supported", device=entry.title)
            writes.append((entry, dp))

        for entry, dp in writes:
            await entry.runtime_data.coordinator.async_set_data_point(dp, True)
            _LOGGER.info("Filter timer reset for %s (DP %d)", entry.title, dp)

    # Entity actions (target = KKT Kolbe entities, validated by HA)
    _register_entity_actions(hass)

    hass.services.async_register(DOMAIN, SERVICE_BULK_POWER_OFF, async_bulk_power_off, BULK_POWER_OFF_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SYNC_ALL_DEVICES, async_sync_all_devices, SYNC_ALL_DEVICES_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_EMERGENCY_STOP, async_emergency_stop, EMERGENCY_STOP_SCHEMA)
    hass.services.async_register(
        DOMAIN, SERVICE_RESET_FILTER_TIMER, async_reset_filter_timer, RESET_FILTER_TIMER_SCHEMA
    )
    hass.services.async_register(DOMAIN, SERVICE_RECONNECT_DEVICE, handle_reconnect_device, RECONNECT_DEVICE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_UPDATE_LOCAL_KEY, handle_update_local_key, UPDATE_LOCAL_KEY_SCHEMA)
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_CONNECTION_STATUS,
        handle_get_connection_status,
        GET_CONNECTION_STATUS_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )

    async def handle_rescan_devices(service: ServiceCall) -> None:
        """Handle rescan devices service - triggers dynamic device discovery."""
        timeout = service.data["timeout"]

        from .discovery import get_discovered_devices
        from .discovery import simple_tuya_discover

        _LOGGER.info("Starting device rescan with timeout %ss", timeout)
        try:
            await simple_tuya_discover(timeout=timeout)
        except Exception as err:
            hass.bus.async_fire(f"{DOMAIN}_devices_discovered", {"error": str(err), "count": 0, "devices": []})
            raise KKTServiceError(service_name=SERVICE_RESCAN_DEVICES, reason=str(err)) from err

        all_devices = get_discovered_devices()
        hass.bus.async_fire(
            f"{DOMAIN}_devices_discovered",
            {
                "count": len(all_devices),
                "devices": [
                    {
                        "device_id": dev.get("device_id", ""),
                        "ip": dev.get("ip", ""),
                        "name": dev.get("name", ""),
                        "discovered_via": dev.get("discovered_via", ""),
                    }
                    for dev in all_devices.values()
                ],
            },
        )
        _LOGGER.info("Device rescan complete - found %d device(s)", len(all_devices))

    hass.services.async_register(DOMAIN, SERVICE_RESCAN_DEVICES, handle_rescan_devices, RESCAN_DEVICES_SCHEMA)

    async def handle_refresh_smartlife_cache(service: ServiceCall) -> None:
        """Manually refresh the SmartLife SDK device cache.

        Calls ``Manager.update_device_cache()`` which re-fetches all devices
        + their function/local_strategy from Tuya cloud. Use when commands
        fail with error 2008 ("command not supported") or after a firmware
        update. Fires ``kkt_kolbe_smartlife_cache_refreshed`` per entry.
        """
        failed: list[str] = []
        for config_entry in _loaded_device_entries(hass):
            entry_id = config_entry.entry_id
            client = getattr(config_entry.runtime_data.coordinator, "smartlife_client", None)
            if client is None:
                continue
            try:
                refreshed = await client.async_refresh_device_cache()
            except Exception as err:
                _LOGGER.error("Failed to refresh SmartLife cache for %s: %s", config_entry.title, err)
                hass.bus.async_fire(
                    f"{DOMAIN}_smartlife_cache_refreshed", {"entry_id": entry_id, "error": str(err), "success": False}
                )
                failed.append(config_entry.title)
                continue
            hass.bus.async_fire(f"{DOMAIN}_smartlife_cache_refreshed", {"entry_id": entry_id, "success": refreshed})
            _LOGGER.info("SmartLife cache refresh for %s: %s", entry_id[:8], refreshed)
        if failed:
            raise KKTServiceError(service_name=SERVICE_REFRESH_SMARTLIFE_CACHE, reason=", ".join(failed))

    hass.services.async_register(
        DOMAIN, SERVICE_REFRESH_SMARTLIFE_CACHE, handle_refresh_smartlife_cache, REFRESH_SMARTLIFE_CACHE_SCHEMA
    )

    async def handle_get_firmware_info(service: ServiceCall) -> ServiceResponse:
        """Query Tuya cloud for the firmware information of the selected devices.

        Fires ``kkt_kolbe_firmware_info`` per device. SmartLife tokens often
        lack the IoT-platform scope required for
        ``/v1.0/iot-03/devices/{id}/upgrade-infos``; then the payload carries
        ``"available": false`` and a hint to check the SmartLife app instead.
        """
        results: list[dict[str, Any]] = []

        def _publish(payload: dict[str, Any]) -> None:
            results.append(payload)
            hass.bus.async_fire(f"{DOMAIN}_firmware_info", payload)

        for config_entry in await _async_target_entries(hass, service):
            entry_id = config_entry.entry_id
            device_id = config_entry.data.get("device_id", "")
            client = getattr(config_entry.runtime_data.coordinator, "smartlife_client", None)
            if client is None:
                _publish(
                    {
                        "entry_id": entry_id,
                        "device_id": device_id,
                        "available": False,
                        "reason": "SmartLife client not configured for this entry",
                    },
                )
                continue

            info = await client.async_get_firmware_info(device_id)
            _publish(
                {
                    "entry_id": entry_id,
                    "device_id": device_id,
                    "available": info is not None,
                    "modules": info or [],
                    "reason": (
                        None
                        if info is not None
                        else "Tuya API rejected request — SmartLife token lacks IoT-platform "
                        "scope. Check firmware via Tuya/SmartLife app: device → ⋮ → Firmware Update"
                    ),
                },
            )
            _LOGGER.info("Firmware info for %s: %s modules", device_id[:8], len(info) if info else 0)

        # Same payloads as the events, returned as action response
        return {"devices": json_loads(json_dumps(results))}

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_FIRMWARE_INFO,
        handle_get_firmware_info,
        GET_FIRMWARE_INFO_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )

    async def handle_download_device_icons(service: ServiceCall) -> None:
        """Download device icons from Tuya Cloud for all configured devices.

        Icons are saved to /config/www/kkt_kolbe/icons/; users can then set
        device pictures in the HA UI using /local/kkt_kolbe/icons/{device_id}.png
        """
        force_redownload = service.data["force"]

        from .helpers.icon_downloader import download_icon
        from .helpers.icon_downloader import list_downloaded_icons

        downloaded = []
        skipped = []
        failed = []
        for config_entry in _loaded_device_entries(hass):
            device_id = config_entry.data.get("device_id")
            icon_url = config_entry.data.get("icon_url")
            if not device_id:
                continue
            if not icon_url:
                skipped.append(device_id)
                continue
            result = await download_icon(hass, device_id, icon_url, force=force_redownload)
            if result:
                downloaded.append(
                    {
                        "device_id": device_id,
                        "local_url": result,
                        "device_name": config_entry.data.get("device_name", device_id[:8]),
                    }
                )
            else:
                failed.append(device_id)

        hass.bus.async_fire(
            f"{DOMAIN}_icons_downloaded",
            {"downloaded": len(downloaded), "skipped": len(skipped), "failed": len(failed), "icons": downloaded},
        )
        _LOGGER.info(
            "Device icon download complete: %d downloaded, %d skipped (no URL), %d failed",
            len(downloaded),
            len(skipped),
            len(failed),
        )

        all_icons = await hass.async_add_executor_job(list_downloaded_icons, hass)
        if all_icons:
            _LOGGER.info(
                "Available device icons in /config/www/kkt_kolbe/icons/: %s",
                ", ".join(icon["device_id"][:8] for icon in all_icons),
            )
        if failed:
            raise KKTServiceError(
                service_name=SERVICE_DOWNLOAD_DEVICE_ICONS, reason=", ".join(device_id[:8] for device_id in failed)
            )

    hass.services.async_register(
        DOMAIN, SERVICE_DOWNLOAD_DEVICE_ICONS, handle_download_device_icons, DOWNLOAD_DEVICE_ICONS_SCHEMA
    )

    _LOGGER.info("KKT Kolbe services registered successfully")


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload KKT Kolbe services."""
    services_to_remove = [
        SERVICE_SET_COOKING_TIMER,
        SERVICE_SET_ZONE_POWER,
        SERVICE_BULK_POWER_OFF,
        SERVICE_SYNC_ALL_DEVICES,
        SERVICE_SET_HOOD_FAN_SPEED,
        SERVICE_SET_HOOD_LIGHTING,
        SERVICE_EMERGENCY_STOP,
        SERVICE_RESET_FILTER_TIMER,
        SERVICE_RECONNECT_DEVICE,
        SERVICE_UPDATE_LOCAL_KEY,
        SERVICE_GET_CONNECTION_STATUS,
        SERVICE_RESCAN_DEVICES,
        SERVICE_DOWNLOAD_DEVICE_ICONS,
        SERVICE_REFRESH_SMARTLIFE_CACHE,
        SERVICE_GET_FIRMWARE_INFO,
    ]

    for service in services_to_remove:
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)

    _LOGGER.info("KKT Kolbe services unloaded successfully")
