"""Entity factory helpers for KKT Kolbe integration.

This module provides utilities to reduce code duplication in entity platform setup.
Each platform (switch, sensor, number, etc.) uses similar patterns that can be
centralized here.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable, TypeVar

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from ..device_types import get_device_entities, get_device_entity_config

if TYPE_CHECKING:
    from .. import KKTKolbeConfigEntry

_LOGGER = logging.getLogger(__name__)

# Generic type for entity classes
EntityT = TypeVar("EntityT", bound=Entity)


def get_entity_lookup_key(entry: KKTKolbeConfigEntry) -> str:
    """Get the lookup key for device_types based on config entry.

    Priority: device_type (KNOWN_DEVICES key) > product_name (Tuya product ID)

    Args:
        entry: The config entry with runtime_data

    Returns:
        The lookup key to use with device_types functions
    """
    runtime_data = entry.runtime_data
    device_type = runtime_data.device_type
    product_name = runtime_data.product_name

    if device_type not in ("auto", None, ""):
        return device_type
    return product_name


def is_advanced_entities_enabled(entry: KKTKolbeConfigEntry) -> bool:
    """Check if advanced entities are enabled in options.

    Args:
        entry: The config entry

    Returns:
        True if advanced entities should be created
    """
    return entry.options.get("enable_advanced_entities", True)


def create_entities_from_config(
    entry: KKTKolbeConfigEntry,
    platform: str,
    entity_class: type[EntityT],
    zone_entity_class: type[EntityT] | None = None,
) -> list[EntityT]:
    """Create entities from device_types configuration.

    This is the main factory function that reads entity configurations from
    device_types.py and creates the appropriate entity instances.

    Args:
        entry: The config entry with runtime_data
        platform: Platform name (e.g., "switch", "sensor", "number")
        entity_class: The main entity class to instantiate
        zone_entity_class: Optional zone-specific entity class

    Returns:
        List of entity instances
    """
    runtime_data = entry.runtime_data
    coordinator = runtime_data.coordinator
    lookup_key = get_entity_lookup_key(entry)
    enable_advanced = is_advanced_entities_enabled(entry)

    entities: list[EntityT] = []
    entity_configs = get_device_entities(lookup_key, platform)

    for config in entity_configs:
        # Skip advanced entities if not enabled
        if config.get("advanced", False) and not enable_advanced:
            continue

        # Determine which class to use
        if zone_entity_class and "zone" in config:
            entity = zone_entity_class(coordinator, entry, config)
        else:
            entity = entity_class(coordinator, entry, config)

        entities.append(entity)

    return entities


def create_single_entity_from_config(
    entry: KKTKolbeConfigEntry,
    platform: str,
    entity_class: type[EntityT],
) -> EntityT | None:
    """Create a single entity from device_types configuration.

    Use this for platforms that only have one entity (like fan, light main).

    Args:
        entry: The config entry with runtime_data
        platform: Platform name
        entity_class: The entity class to instantiate

    Returns:
        Single entity instance or None if not configured
    """
    runtime_data = entry.runtime_data
    coordinator = runtime_data.coordinator
    lookup_key = get_entity_lookup_key(entry)

    entity_config = get_device_entity_config(lookup_key, platform)

    if entity_config:
        return entity_class(coordinator, entry, entity_config)

    return None


async def async_setup_platform_entities(
    hass: HomeAssistant,
    entry: KKTKolbeConfigEntry,
    async_add_entities: AddEntitiesCallback,
    platform: str,
    entity_class: type[EntityT],
    zone_entity_class: type[EntityT] | None = None,
    extra_entities: list[EntityT] | None = None,
) -> None:
    """Generic platform setup for entity creation.

    This function handles the common setup pattern used across all platforms:
    1. Get runtime_data and lookup key
    2. Create entities from config
    3. Optionally add extra entities (like connection sensors)
    4. Add all entities to Home Assistant

    Args:
        hass: Home Assistant instance
        entry: Config entry with runtime_data
        async_add_entities: Callback to add entities
        platform: Platform name for logging
        entity_class: Main entity class
        zone_entity_class: Optional zone-specific class
        extra_entities: Additional entities to add (like status sensors)
    """
    runtime_data = entry.runtime_data
    lookup_key = get_entity_lookup_key(entry)

    entities: list[EntityT] = []

    # Add extra entities first (like connection status sensors)
    if extra_entities:
        entities.extend(extra_entities)

    # Create entities from device_types config
    config_entities = create_entities_from_config(
        entry=entry,
        platform=platform,
        entity_class=entity_class,
        zone_entity_class=zone_entity_class,
    )
    entities.extend(config_entities)

    if entities:
        _LOGGER.info(
            "Setting up %d %s entities for %s",
            len(entities),
            platform,
            lookup_key,
        )
        async_add_entities(entities)
    else:
        _LOGGER.debug("No %s configuration found for %s", platform, lookup_key)


def get_coordinator_from_entry(
    entry: KKTKolbeConfigEntry,
) -> DataUpdateCoordinator[dict[str, Any]]:
    """Get the coordinator from a config entry.

    Args:
        entry: Config entry with runtime_data

    Returns:
        The data update coordinator
    """
    return entry.runtime_data.coordinator


def get_device_info_from_entry(entry: KKTKolbeConfigEntry) -> dict[str, Any]:
    """Get device info from a config entry.

    Args:
        entry: Config entry with runtime_data

    Returns:
        Device info dictionary
    """
    return entry.runtime_data.device_info
