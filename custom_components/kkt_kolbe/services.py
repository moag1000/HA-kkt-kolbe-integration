"""Services for KKT Kolbe integration."""
import asyncio
import logging
from typing import Any, Dict, List

from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er, device_registry as dr
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.const import (
    ATTR_ENTITY_ID,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)

from .const import DOMAIN
from .exceptions import (
    KKTServiceError,
    KKTDeviceError,
    KKTTimeoutError,
    KKTConnectionError,
)

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


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for KKT Kolbe integration."""

    @callback
    def validate_entity_id(entity_id: str, required_domain: str = None) -> None:
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
    ]

    for service in services_to_remove:
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)

    _LOGGER.info("KKT Kolbe services unloaded successfully")