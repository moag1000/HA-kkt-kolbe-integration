"""Services for KKT Kolbe integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.core import ServiceCall
from homeassistant.core import callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from .exceptions import KKTServiceError

_LOGGER = logging.getLogger(__name__)

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


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for KKT Kolbe integration."""

    async def handle_reconnect_device(service: ServiceCall) -> None:
        """Handle reconnect device service."""
        device_id = service.data.get("device_id")
        entry_id = service.data.get("entry_id")

        # Find the coordinator(s) to reconnect
        coordinators = _get_coordinators(hass, device_id, entry_id)

        if not coordinators:
            raise ServiceValidationError("No matching devices found")

        results = {}
        for coord_entry_id, coordinator in coordinators:
            try:
                # Use ReconnectCoordinator if available
                if hasattr(coordinator, 'async_request_reconnect'):
                    success = await coordinator.async_request_reconnect()
                    results[coord_entry_id] = {
                        "success": success,
                        "state": coordinator.device_state.value if hasattr(coordinator, 'device_state') else "unknown"
                    }
                else:
                    # Fallback for standard coordinator
                    if coordinator.device is None:
                        results[coord_entry_id] = {
                            "success": False,
                            "error": "No local device available (API-only mode)",
                            "state": "api_only"
                        }
                        continue

                    await coordinator.device.async_disconnect()
                    await coordinator.device.async_connect()
                    await coordinator.async_request_refresh()
                    results[coord_entry_id] = {
                        "success": coordinator.device.is_connected,
                        "state": "online" if coordinator.device.is_connected else "offline"
                    }

                device_id_str = coordinator.device.device_id[:8] if coordinator.device else coord_entry_id[:8]
                _LOGGER.info(f"Reconnected device {device_id_str}: {results[coord_entry_id]}")

            except Exception as err:
                _LOGGER.error(f"Failed to reconnect device: {err}")
                results[coord_entry_id] = {"error": str(err)}

        # Fire event with results
        hass.bus.async_fire(
            f"{DOMAIN}_reconnect_complete",
            {"results": results}
        )

    async def handle_update_local_key(service: ServiceCall) -> None:
        """Handle update local key service with enhanced reconnection."""
        local_key = service.data["local_key"]
        device_id = service.data.get("device_id")
        entry_id = service.data.get("entry_id")
        force_reconnect = service.data.get("force_reconnect", True)

        # Find the coordinator(s) to update
        coordinators = _get_coordinators(hass, device_id, entry_id)

        if not coordinators:
            raise ServiceValidationError("No matching devices found")

        results = {}
        for coord_entry_id, coordinator in coordinators:
            try:
                entry = hass.config_entries.async_get_entry(coord_entry_id)
                if not entry:
                    raise ServiceValidationError(f"Config entry {coord_entry_id} not found")

                device_id = entry.data.get("device_id")
                ip_address = entry.data.get("ip_address")

                # Check if coordinator has a local device
                if coordinator.device is None:
                    results[coord_entry_id] = {
                        "success": False,
                        "device_id": device_id,
                        "error": "No local device available (API-only mode). Cannot update local key."
                    }
                    continue

                # Log current connection state
                _LOGGER.info(
                    f"Updating local key for device {device_id[:8]} "
                    f"(currently {'connected' if coordinator.device.is_connected else 'disconnected'})"
                )

                # First, disconnect the current device if connected
                if coordinator.device.is_connected:
                    _LOGGER.debug("Disconnecting current device connection")
                    await coordinator.device.async_disconnect()
                    await asyncio.sleep(1)  # Give it time to fully disconnect

                # Test new local key with fresh device instance
                from .tuya_device import KKTKolbeTuyaDevice
                test_device = KKTKolbeTuyaDevice(device_id, ip_address, local_key, hass=hass)

                _LOGGER.debug(f"Testing new local key for device {device_id[:8]}")
                connection_test = await test_device.async_test_connection()

                if connection_test:
                    _LOGGER.info(f"New local key validated for device {device_id[:8]}")

                    # Update config entry with new local key
                    hass.config_entries.async_update_entry(
                        entry,
                        data={**entry.data, "local_key": local_key}
                    )

                    # Update the coordinator's device with new key
                    coordinator.device.local_key = local_key

                    if force_reconnect:
                        # Force immediate reconnection with new key
                        _LOGGER.info(f"Forcing reconnection for device {device_id[:8]}")

                        # If coordinator has reconnect capability, use it
                        if hasattr(coordinator, 'async_request_reconnect'):
                            await coordinator.async_request_reconnect()
                        else:
                            # Manual reconnection
                            try:
                                await coordinator.device.async_connect()
                                await coordinator.async_request_refresh()
                            except Exception as reconnect_err:
                                _LOGGER.warning(f"Reconnection attempt failed: {reconnect_err}")

                    # Optionally reload the entire integration for clean state
                    if service.data.get("reload_integration", False):
                        _LOGGER.info(f"Reloading integration for device {device_id[:8]}")
                        await hass.config_entries.async_reload(coord_entry_id)

                    results[coord_entry_id] = {
                        "success": True,
                        "device_id": device_id,
                        "message": "Local key updated and device reconnected successfully",
                        "reconnected": coordinator.device.is_connected
                    }

                    _LOGGER.info(
                        f"Successfully updated local key for device {device_id[:8]}. "
                        f"Connection status: {coordinator.device.is_connected}"
                    )
                else:
                    _LOGGER.error(f"Failed to validate new local key for device {device_id[:8]}")

                    # Try to reconnect with old key if available
                    old_key = entry.data.get("local_key")
                    if old_key and old_key != local_key:
                        _LOGGER.info("Attempting to restore connection with old key")
                        coordinator.device.local_key = old_key
                        try:
                            await coordinator.device.async_connect()
                        except Exception:
                            pass

                    results[coord_entry_id] = {
                        "success": False,
                        "device_id": device_id,
                        "error": "Invalid local key - connection test failed. Device may need to be reset in Tuya app."
                    }

            except Exception as err:
                _LOGGER.error(f"Failed to update local key: {err}")
                results[coord_entry_id] = {
                    "success": False,
                    "error": str(err)
                }

        # Fire event with results
        hass.bus.async_fire(
            f"{DOMAIN}_local_key_updated",
            {"results": results}
        )

    async def handle_get_connection_status(service: ServiceCall) -> None:
        """Handle get connection status service."""
        device_id = service.data.get("device_id")
        entry_id = service.data.get("entry_id")

        # Get all coordinators if no filter specified
        coordinators = _get_coordinators(hass, device_id, entry_id)

        statuses = {}
        for coord_entry_id, coordinator in coordinators:
            try:
                # Get connection info based on coordinator type
                if hasattr(coordinator, 'connection_info'):
                    # ReconnectCoordinator
                    statuses[coord_entry_id] = coordinator.connection_info
                else:
                    # Standard coordinator
                    if coordinator.device is None:
                        statuses[coord_entry_id] = {
                            "state": "api_only",
                            "last_update": coordinator.last_update_success_time if hasattr(coordinator, 'last_update_success_time') else None,
                            "is_connected": False,
                            "device_id": "api_mode",
                            "ip_address": None,
                            "mode": "api_only",
                        }
                    else:
                        statuses[coord_entry_id] = {
                            "state": "online" if coordinator.device.is_connected else "offline",
                            "last_update": coordinator.last_update_success_time if hasattr(coordinator, 'last_update_success_time') else None,
                            "is_connected": coordinator.device.is_connected,
                            "device_id": coordinator.device.device_id,
                            "ip_address": coordinator.device.ip_address,
                        }

            except Exception as err:
                _LOGGER.error(f"Failed to get status: {err}")
                statuses[coord_entry_id] = {"error": str(err)}

        # Fire event with statuses
        hass.bus.async_fire(
            f"{DOMAIN}_connection_status",
            {"statuses": statuses}
        )

        return statuses

    def _get_coordinators(
        hass: HomeAssistant,
        device_id: str | None = None,
        entry_id: str | None = None,
    ) -> list[tuple[str, Any]]:
        """Get coordinators matching the criteria."""
        coordinators: list[tuple[str, Any]] = []

        for coord_entry_id, entry_data in hass.data.get(DOMAIN, {}).items():
            if "coordinator" not in entry_data:
                continue

            # Filter by entry_id if specified
            if entry_id and coord_entry_id != entry_id:
                continue

            coordinator = entry_data["coordinator"]

            # Filter by device_id if specified
            if device_id:
                # Handle case where coordinator.device may be None (API-only mode)
                coord_device_id = None
                if hasattr(coordinator, 'device_id'):
                    # HybridCoordinator has device_id attribute directly
                    coord_device_id = coordinator.device_id
                elif coordinator.device is not None:
                    coord_device_id = coordinator.device.device_id

                if coord_device_id != device_id:
                    continue

            coordinators.append((coord_entry_id, coordinator))

        return coordinators

    @callback
    def validate_entity_id(entity_id: str, required_domain: str | None = None) -> None:
        """Validate entity ID and check if it belongs to KKT Kolbe integration."""
        entity_registry = er.async_get(hass)
        entity_entry = entity_registry.async_get(entity_id)

        if not entity_entry:
            raise ServiceValidationError(f"Entity {entity_id} not found")

        if entity_entry.platform != DOMAIN:
            raise ServiceValidationError(f"Entity {entity_id} is not a KKT Kolbe entity")

        if required_domain and not entity_id.startswith(f"{required_domain}."):
            raise ServiceValidationError(
                f"Entity {entity_id} must be in {required_domain} domain"
            )

        # Check if entity is available
        state = hass.states.get(entity_id)
        if not state or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            raise ServiceValidationError(f"Entity {entity_id} is not available")

    async def async_set_cooking_timer(call: ServiceCall) -> None:
        """Set cooking timer for a specific zone."""
        entity_id = call.data[ATTR_ENTITY_ID]
        timer_minutes = call.data["timer_minutes"]

        try:
            validate_entity_id(entity_id, "number")

            # Set the timer value
            await hass.services.async_call(
                "number",
                "set_value",
                {ATTR_ENTITY_ID: entity_id, "value": timer_minutes},
                blocking=True,
            )

            _LOGGER.info(
                "Set cooking timer for %s to %d minutes",
                entity_id,
                timer_minutes
            )

        except Exception as exc:
            _LOGGER.error("Failed to set cooking timer: %s", exc)
            raise KKTServiceError(
                service_name=SERVICE_SET_COOKING_TIMER,
                reason=str(exc)
            ) from exc

    async def async_set_zone_power(call: ServiceCall) -> None:
        """Set power level for a specific zone."""
        entity_id = call.data[ATTR_ENTITY_ID]
        power_level = call.data["power_level"]

        try:
            validate_entity_id(entity_id, "number")

            # Set the power level
            await hass.services.async_call(
                "number",
                "set_value",
                {ATTR_ENTITY_ID: entity_id, "value": power_level},
                blocking=True,
            )

            _LOGGER.info(
                "Set zone power for %s to level %d",
                entity_id,
                power_level
            )

        except Exception as exc:
            _LOGGER.error("Failed to set zone power: %s", exc)
            raise KKTServiceError(
                service_name=SERVICE_SET_ZONE_POWER,
                reason=str(exc)
            ) from exc

    async def async_bulk_power_off(call: ServiceCall) -> None:
        """Turn off all or specific types of KKT Kolbe devices."""
        device_types = call.data.get("device_types", ["all"])
        confirm = call.data.get("confirm", False)

        if not confirm:
            raise ServiceValidationError("Must confirm bulk power off operation")

        try:
            affected_entities = []
            entity_registry = er.async_get(hass)

            # Find all KKT Kolbe power entities
            for entity_entry in entity_registry.entities.values():
                if entity_entry.platform != DOMAIN:
                    continue

                # Check device type filter
                if "all" not in device_types:
                    # Get device info to determine type
                    device_registry_instance = dr.async_get(hass)
                    device_entry = device_registry_instance.async_get(entity_entry.device_id)

                    if not device_entry:
                        continue

                    device_model = (device_entry.model or "").lower()

                    should_include = (
                        ("cooktop" in device_types and "ind" in device_model) or
                        ("hood" in device_types and ("hermes" in device_model or "style" in device_model))
                    )

                    if not should_include:
                        continue

                # Check if this is a power-related entity
                entity_id = entity_entry.entity_id
                if (entity_id.startswith("switch.") and "power" in entity_id.lower()) or \
                   (entity_id.startswith("number.") and any(term in entity_id.lower() for term in ["zone", "power"])):

                    state = hass.states.get(entity_id)
                    if state and state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                        affected_entities.append(entity_id)

            # Turn off entities
            tasks = []
            for entity_id in affected_entities:
                if entity_id.startswith("switch."):
                    tasks.append(
                        hass.services.async_call(
                            "switch", "turn_off", {ATTR_ENTITY_ID: entity_id}
                        )
                    )
                elif entity_id.startswith("number."):
                    tasks.append(
                        hass.services.async_call(
                            "number", "set_value", {ATTR_ENTITY_ID: entity_id, "value": 0}
                        )
                    )

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                _LOGGER.info(
                    "Bulk power off completed for %d entities with filter %s",
                    len(affected_entities),
                    device_types
                )
            else:
                _LOGGER.warning("No entities found for bulk power off with filter %s", device_types)

        except Exception as exc:
            _LOGGER.error("Failed to execute bulk power off: %s", exc)
            raise KKTServiceError(
                service_name=SERVICE_BULK_POWER_OFF,
                reason=str(exc)
            ) from exc

    async def async_sync_all_devices(call: ServiceCall) -> None:
        """Force refresh data for all KKT Kolbe devices."""
        device_filter = call.data.get("device_filter", "all")

        try:
            coordinators_refreshed = 0

            for entry_id, entry_data in hass.data.get(DOMAIN, {}).items():
                if "coordinator" not in entry_data:
                    continue

                coordinator = entry_data["coordinator"]

                # Apply device filter
                if device_filter == "online_only" and not coordinator.last_update_success:
                    continue
                elif device_filter == "offline_only" and coordinator.last_update_success:
                    continue

                try:
                    await coordinator.async_request_refresh()
                    coordinators_refreshed += 1
                except Exception as exc:
                    _LOGGER.warning(
                        "Failed to refresh coordinator for entry %s: %s",
                        entry_id,
                        exc
                    )

            _LOGGER.info(
                "Synchronized %d KKT Kolbe devices with filter '%s'",
                coordinators_refreshed,
                device_filter
            )

        except Exception as exc:
            _LOGGER.error("Failed to sync devices: %s", exc)
            raise KKTServiceError(
                service_name=SERVICE_SYNC_ALL_DEVICES,
                reason=str(exc)
            ) from exc

    async def async_set_hood_fan_speed(call: ServiceCall) -> None:
        """Set fan speed for range hood."""
        entity_id = call.data[ATTR_ENTITY_ID]
        fan_speed = call.data["fan_speed"]

        try:
            validate_entity_id(entity_id, "number")

            await hass.services.async_call(
                "number",
                "set_value",
                {ATTR_ENTITY_ID: entity_id, "value": fan_speed},
                blocking=True,
            )

            _LOGGER.info(
                "Set hood fan speed for %s to level %d",
                entity_id,
                fan_speed
            )

        except Exception as exc:
            _LOGGER.error("Failed to set hood fan speed: %s", exc)
            raise KKTServiceError(
                service_name=SERVICE_SET_HOOD_FAN_SPEED,
                reason=str(exc)
            ) from exc

    async def async_set_hood_lighting(call: ServiceCall) -> None:
        """Control range hood lighting."""
        entity_id = call.data[ATTR_ENTITY_ID]
        brightness = call.data.get("brightness")

        try:
            validate_entity_id(entity_id, "switch")

            if brightness is not None:
                # If brightness is specified, turn on and set brightness
                await hass.services.async_call(
                    "switch", "turn_on", {ATTR_ENTITY_ID: entity_id}, blocking=True
                )
                # Note: Brightness control would need to be implemented in the switch entity
                _LOGGER.info(
                    "Set hood lighting for %s to brightness %d",
                    entity_id,
                    brightness
                )
            else:
                # Toggle the lighting
                await hass.services.async_call(
                    "switch", "toggle", {ATTR_ENTITY_ID: entity_id}, blocking=True
                )
                _LOGGER.info("Toggled hood lighting for %s", entity_id)

        except Exception as exc:
            _LOGGER.error("Failed to set hood lighting: %s", exc)
            raise KKTServiceError(
                service_name=SERVICE_SET_HOOD_LIGHTING,
                reason=str(exc)
            ) from exc

    async def async_emergency_stop(call: ServiceCall) -> None:
        """Emergency stop all cooking operations."""
        confirm = call.data.get("confirm", False)
        send_notification = call.data.get("notification", True)

        if not confirm:
            raise ServiceValidationError("Must confirm emergency stop operation")

        try:
            entity_registry = er.async_get(hass)
            stopped_entities = []

            # Find all cooking-related entities and turn them off
            for entity_entry in entity_registry.entities.values():
                if entity_entry.platform != DOMAIN:
                    continue

                entity_id = entity_entry.entity_id

                # Emergency stop targets: power switches, zone powers, timers
                if (entity_id.startswith("switch.") and "power" in entity_id.lower()) or \
                   (entity_id.startswith("number.") and any(term in entity_id.lower() for term in ["zone", "power", "timer"])):

                    state = hass.states.get(entity_id)
                    if state and state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                        if entity_id.startswith("switch."):
                            await hass.services.async_call(
                                "switch", "turn_off", {ATTR_ENTITY_ID: entity_id}
                            )
                        elif entity_id.startswith("number."):
                            await hass.services.async_call(
                                "number", "set_value", {ATTR_ENTITY_ID: entity_id, "value": 0}
                            )
                        stopped_entities.append(entity_id)

            _LOGGER.warning(
                "EMERGENCY STOP executed - stopped %d cooking operations",
                len(stopped_entities)
            )

            if send_notification:
                await hass.services.async_call(
                    "persistent_notification",
                    "create",
                    {
                        "title": "KKT Kolbe Emergency Stop",
                        "message": f"Emergency stop executed - {len(stopped_entities)} cooking operations stopped",
                        "notification_id": "kkt_kolbe_emergency_stop",
                    }
                )

        except Exception as exc:
            _LOGGER.error("Failed to execute emergency stop: %s", exc)
            raise KKTServiceError(
                service_name=SERVICE_EMERGENCY_STOP,
                reason=str(exc)
            ) from exc

    async def async_reset_filter_timer(call: ServiceCall) -> None:
        """Reset filter timer for range hood."""
        entity_id = call.data[ATTR_ENTITY_ID]
        confirm = call.data.get("confirm", False)

        if not confirm:
            raise ServiceValidationError("Must confirm filter timer reset")

        try:
            validate_entity_id(entity_id)

            # Get the coordinator for this entity
            entity_registry = er.async_get(hass)
            entity_entry = entity_registry.async_get(entity_id)

            if not entity_entry:
                raise ServiceValidationError(f"Entity {entity_id} not found")

            # Find the coordinator for this entity's config entry
            config_entry_id = entity_entry.config_entry_id
            if config_entry_id in hass.data.get(DOMAIN, {}):
                coordinator = hass.data[DOMAIN][config_entry_id]["coordinator"]

                # Reset filter using DP 15 (filter_reset switch)
                await coordinator.async_set_data_point(15, True)

                _LOGGER.info("Filter timer reset completed for %s", entity_id)
            else:
                raise ServiceValidationError(f"Coordinator not found for entity {entity_id}")

        except Exception as exc:
            _LOGGER.error("Failed to reset filter timer: %s", exc)
            raise KKTServiceError(
                service_name=SERVICE_RESET_FILTER_TIMER,
                reason=str(exc)
            ) from exc

    # Register all services
    hass.services.async_register(
        DOMAIN, SERVICE_SET_COOKING_TIMER, async_set_cooking_timer
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SET_ZONE_POWER, async_set_zone_power
    )
    hass.services.async_register(
        DOMAIN, SERVICE_BULK_POWER_OFF, async_bulk_power_off
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SYNC_ALL_DEVICES, async_sync_all_devices
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SET_HOOD_FAN_SPEED, async_set_hood_fan_speed
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SET_HOOD_LIGHTING, async_set_hood_lighting
    )
    hass.services.async_register(
        DOMAIN, SERVICE_EMERGENCY_STOP, async_emergency_stop
    )
    hass.services.async_register(
        DOMAIN, SERVICE_RESET_FILTER_TIMER, async_reset_filter_timer
    )
    hass.services.async_register(
        DOMAIN, SERVICE_RECONNECT_DEVICE, handle_reconnect_device
    )
    hass.services.async_register(
        DOMAIN, SERVICE_UPDATE_LOCAL_KEY, handle_update_local_key
    )
    hass.services.async_register(
        DOMAIN, SERVICE_GET_CONNECTION_STATUS, handle_get_connection_status
    )

    async def handle_rescan_devices(service: ServiceCall) -> None:
        """Handle rescan devices service - triggers dynamic device discovery."""
        timeout = service.data.get("timeout", 6)

        try:
            from .discovery import get_discovered_devices
            from .discovery import simple_tuya_discover

            _LOGGER.info(f"Starting device rescan with timeout {timeout}s...")

            # Run UDP discovery
            await simple_tuya_discover(timeout=timeout)

            # Get all discovered devices (including mDNS)
            all_devices = get_discovered_devices()

            # Fire event with results
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
                }
            )

            _LOGGER.info(f"Device rescan complete - found {len(all_devices)} device(s)")

        except Exception as err:
            _LOGGER.error(f"Device rescan failed: {err}")
            hass.bus.async_fire(
                f"{DOMAIN}_devices_discovered",
                {"error": str(err), "count": 0, "devices": []}
            )

    hass.services.async_register(
        DOMAIN, SERVICE_RESCAN_DEVICES, handle_rescan_devices
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
    ]

    for service in services_to_remove:
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)

    _LOGGER.info("KKT Kolbe services unloaded successfully")