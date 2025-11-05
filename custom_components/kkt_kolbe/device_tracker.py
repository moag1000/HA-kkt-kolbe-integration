"""Device tracker for monitoring stale devices - Gold Tier requirement."""
import logging
from datetime import datetime, timedelta
from typing import Set

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Consider device stale if not seen for 30 days
STALE_DEVICE_THRESHOLD = timedelta(days=30)

# Check for stale devices every 24 hours
CLEANUP_INTERVAL = timedelta(hours=24)


class StaleDeviceTracker:
    """Track and clean up stale devices."""

    def __init__(self, hass: HomeAssistant):
        """Initialize the device tracker."""
        self.hass = hass
        self._cleanup_task = None
        self._tracked_devices: Set[str] = set()

    async def async_start(self) -> None:
        """Start the stale device tracker."""
        # Schedule periodic cleanup
        self._cleanup_task = async_track_time_interval(
            self.hass,
            self._async_cleanup_stale_devices,
            CLEANUP_INTERVAL
        )
        _LOGGER.info("Stale device tracker started")

        # Run initial cleanup after 1 hour
        self.hass.loop.call_later(3600, self._schedule_initial_cleanup)

    def _schedule_initial_cleanup(self):
        """Schedule the initial cleanup."""
        self.hass.async_create_task(self._async_cleanup_stale_devices(None))

    async def async_stop(self) -> None:
        """Stop the stale device tracker."""
        if self._cleanup_task:
            self._cleanup_task()
            self._cleanup_task = None
        _LOGGER.info("Stale device tracker stopped")

    @callback
    def track_device(self, device_id: str) -> None:
        """Mark a device as active/seen."""
        self._tracked_devices.add(device_id)

    async def _async_cleanup_stale_devices(self, now) -> None:
        """Clean up stale devices."""
        try:
            device_reg = dr.async_get(self.hass)
            entity_reg = er.async_get(self.hass)

            # Get all KKT Kolbe config entries
            config_entries = self.hass.config_entries.async_entries(DOMAIN)

            removed_count = 0
            # Check devices for each config entry
            for entry in config_entries:
                devices = dr.async_entries_for_config_entry(device_reg, entry.entry_id)

                for device in devices:
                    # Check if device is stale
                    if await self._is_device_stale(device, entity_reg):
                        _LOGGER.info(
                            f"Removing stale device: {device.name} "
                            f"(ID: {device.id}, not seen for {STALE_DEVICE_THRESHOLD.days} days)"
                        )

                        # Remove the device (this also removes its entities)
                        device_reg.async_remove_device(device.id)
                        removed_count += 1

            if removed_count > 0:
                _LOGGER.info(f"Removed {removed_count} stale device(s)")
            else:
                _LOGGER.debug("No stale devices found during cleanup")

        except Exception as e:
            _LOGGER.error(f"Error during stale device cleanup: {e}", exc_info=True)

    async def _is_device_stale(
        self, device: dr.DeviceEntry, entity_reg: er.EntityRegistry
    ) -> bool:
        """Check if a device is stale (not seen recently)."""
        try:
            # Get all entities for this device
            entities = er.async_entries_for_device(entity_reg, device.id)

            if not entities:
                # No entities = device not properly initialized, could be stale
                # But be conservative - only remove if old
                if device.created_at:
                    age = datetime.now() - device.created_at
                    return age > STALE_DEVICE_THRESHOLD
                return False

            # Check if any entity has been updated recently
            now = datetime.now()
            for entity in entities:
                # If entity is available, device is not stale
                state = self.hass.states.get(entity.entity_id)
                if state and state.state != "unavailable":
                    return False

                # Check when entity was last updated
                if state and state.last_updated:
                    time_since_update = now - state.last_updated
                    if time_since_update < STALE_DEVICE_THRESHOLD:
                        return False

            # Check if device has active config entry
            if device.config_entries:
                for config_entry_id in device.config_entries:
                    entry = self.hass.config_entries.async_get_entry(config_entry_id)
                    if entry and not entry.disabled_by:
                        # Config entry is active, check coordinator
                        if DOMAIN in self.hass.data and config_entry_id in self.hass.data[DOMAIN]:
                            coordinator = self.hass.data[DOMAIN][config_entry_id].get("coordinator")
                            if coordinator and coordinator.last_update_success:
                                # Coordinator is working, device is not stale
                                return False

            # All checks failed - device appears stale
            _LOGGER.debug(
                f"Device {device.name} appears stale: "
                f"All entities unavailable for >{STALE_DEVICE_THRESHOLD.days} days"
            )
            return True

        except Exception as e:
            _LOGGER.error(f"Error checking if device {device.id} is stale: {e}")
            return False  # Conservative: don't remove if check fails


# Global tracker instance
_tracker_instance = None


async def async_start_tracker(hass: HomeAssistant) -> None:
    """Start the stale device tracker."""
    global _tracker_instance

    if _tracker_instance is None:
        _tracker_instance = StaleDeviceTracker(hass)
        await _tracker_instance.async_start()


async def async_stop_tracker() -> None:
    """Stop the stale device tracker."""
    global _tracker_instance

    if _tracker_instance:
        await _tracker_instance.async_stop()
        _tracker_instance = None


def track_device_activity(device_id: str) -> None:
    """Mark a device as active."""
    global _tracker_instance

    if _tracker_instance:
        _tracker_instance.track_device(device_id)
