"""Repair flow for KKT Kolbe integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import data_entry_flow
from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import CONF_API_ENDPOINT
from .const import DOMAIN

# Home Assistant doesn't have CONF_LOCAL_KEY in const, so we define it here
CONF_LOCAL_KEY = "local_key"

_LOGGER = logging.getLogger(__name__)


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, Any] | None,
) -> RepairsFlow:
    """Create a fix flow for repair issues."""
    if issue_id.startswith("tuya_api_auth_failed_"):
        return TuyaAPIAuthRepairFlow(hass, issue_id, data)
    elif issue_id.startswith("tuya_api_wrong_region_"):
        return TuyaAPIRegionRepairFlow(hass, issue_id, data)
    elif issue_id.startswith("local_key_expired_"):
        return LocalKeyExpiredRepairFlow(hass, issue_id, data)
    elif issue_id.startswith("device_id_changed_"):
        return DeviceIdChangedRepairFlow(hass, issue_id, data)

    raise ValueError(f"Unknown repair issue: {issue_id}")


class TuyaAPIAuthRepairFlow(RepairsFlow):
    """Handler for Tuya API authentication repair flow."""

    def __init__(
        self,
        hass: HomeAssistant,
        issue_id: str,
        data: dict[str, Any] | None,
    ) -> None:
        """Initialize repair flow."""
        super().__init__()
        self.hass = hass
        self.issue_id = issue_id
        self.data = data or {}
        self.entry_id = self.data.get("entry_id")

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the first step of the repair flow."""
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Confirm the user wants to fix this issue."""
        if user_input is not None:
            # Trigger reauth flow for the config entry
            if self.entry_id:
                entry = self.hass.config_entries.async_get_entry(self.entry_id)
                if entry:
                    _LOGGER.info(f"Triggering reauth flow for entry {self.entry_id}")
                    self.hass.async_create_task(
                        self.hass.config_entries.flow.async_init(
                            DOMAIN,
                            context={
                                "source": "reauth",
                                "entry_id": self.entry_id,
                            },
                            data=entry.data,
                        )
                    )

            # Mark issue as resolved
            await self.async_mark_resolved()
            return self.async_create_entry(data={})

        return self.async_show_form(
            step_id="confirm",
            description_placeholders={
                "entry_title": self.data.get("entry_title", "Unknown"),
            },
        )

    async def async_mark_resolved(self) -> None:
        """Mark the issue as resolved."""
        ir.async_delete_issue(self.hass, DOMAIN, self.issue_id)


class TuyaAPIRegionRepairFlow(RepairsFlow):
    """Handler for Tuya API wrong region repair flow."""

    ENDPOINTS = {
        "Central Europe": "https://openapi.tuyaeu.com",
        "Western Europe": "https://openapi.tuyaeu.com",
        "Eastern US": "https://openapi.tuyaus.com",
        "Western US": "https://openapi-ueaz.tuyaus.com",
        "China": "https://openapi.tuyacn.com",
        "India": "https://openapi.tuyain.com",
    }

    def __init__(
        self,
        hass: HomeAssistant,
        issue_id: str,
        data: dict[str, Any] | None,
    ) -> None:
        """Initialize repair flow."""
        super().__init__()
        self.hass = hass
        self.issue_id = issue_id
        self.data = data or {}
        self.entry_id = self.data.get("entry_id")

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the first step of the repair flow."""
        return await self.async_step_confirm_region()

    async def async_step_confirm_region(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Ask user to select correct region."""
        errors = {}

        if user_input is not None:
            region = str(user_input.get("region", ""))
            new_endpoint = self.ENDPOINTS.get(region)

            if new_endpoint and self.entry_id:
                entry = self.hass.config_entries.async_get_entry(self.entry_id)
                if entry:
                    # Update config entry with new endpoint
                    new_data = dict(entry.data)
                    new_data[CONF_API_ENDPOINT] = new_endpoint

                    self.hass.config_entries.async_update_entry(
                        entry, data=new_data
                    )

                    # Reload the integration
                    await self.hass.config_entries.async_reload(self.entry_id)

                    _LOGGER.info(
                        f"Updated Tuya API endpoint to {region}: {new_endpoint}"
                    )

                    # Mark issue as resolved
                    await self.async_mark_resolved()
                    return self.async_create_entry(data={})
            else:
                errors["base"] = "invalid_region"

        return self.async_show_form(
            step_id="confirm_region",
            data_schema=vol.Schema(
                {
                    vol.Required("region", default="Central Europe"): vol.In(
                        list(self.ENDPOINTS.keys())
                    ),
                }
            ),
            errors=errors,
            description_placeholders={
                "entry_title": self.data.get("entry_title", "Unknown"),
                "current_endpoint": self.data.get("current_endpoint", "Unknown"),
            },
        )

    async def async_mark_resolved(self) -> None:
        """Mark the issue as resolved."""
        ir.async_delete_issue(self.hass, DOMAIN, self.issue_id)


class LocalKeyExpiredRepairFlow(RepairsFlow):
    """Handler for expired local key repair flow."""

    def __init__(
        self,
        hass: HomeAssistant,
        issue_id: str,
        data: dict[str, Any] | None,
    ) -> None:
        """Initialize repair flow."""
        super().__init__()
        self.hass = hass
        self.issue_id = issue_id
        self.data = data or {}
        self.entry_id = self.data.get("entry_id")

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the first step of the repair flow."""
        return await self.async_step_update_local_key()

    async def async_step_update_local_key(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Ask user to enter new local key."""
        errors = {}

        if user_input is not None:
            new_local_key = user_input.get(CONF_LOCAL_KEY, "").strip()

            if len(new_local_key) != 16:
                errors[CONF_LOCAL_KEY] = "invalid_local_key"
            else:
                if self.entry_id:
                    entry = self.hass.config_entries.async_get_entry(self.entry_id)
                    if entry:
                        # Update config entry with new local key
                        new_data = dict(entry.data)
                        new_data[CONF_LOCAL_KEY] = new_local_key

                        self.hass.config_entries.async_update_entry(
                            entry, data=new_data
                        )

                        # Reload the integration
                        await self.hass.config_entries.async_reload(self.entry_id)

                        _LOGGER.info(
                            f"Updated local key for entry {self.entry_id}"
                        )

                        # Mark issue as resolved
                        await self.async_mark_resolved()
                        return self.async_create_entry(data={})

        return self.async_show_form(
            step_id="update_local_key",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LOCAL_KEY): str,
                }
            ),
            errors=errors,
            description_placeholders={
                "entry_title": self.data.get("entry_title", "Unknown"),
                "device_id": self.data.get("device_id", "Unknown"),
            },
        )

    async def async_mark_resolved(self) -> None:
        """Mark the issue as resolved."""
        ir.async_delete_issue(self.hass, DOMAIN, self.issue_id)


class DeviceIdChangedRepairFlow(RepairsFlow):
    """Handler for device ID changed repair flow.

    This handles the case when a device is re-added to Tuya/SmartLife
    and gets a new device_id. The local_key also changes in this case.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        issue_id: str,
        data: dict[str, Any] | None,
    ) -> None:
        """Initialize repair flow."""
        super().__init__()
        self.hass = hass
        self.issue_id = issue_id
        self.data = data or {}
        self.entry_id = self.data.get("entry_id")
        self.new_device_id = self.data.get("new_device_id")
        self.new_ip = self.data.get("new_ip")

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the first step of the repair flow."""
        return await self.async_step_update_device()

    async def async_step_update_device(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Ask user to confirm device ID and IP update, enter new local key."""
        errors = {}

        if user_input is not None:
            new_device_id = user_input.get("device_id", "").strip()
            new_ip = user_input.get("ip_address", "").strip()
            new_local_key = user_input.get(CONF_LOCAL_KEY, "").strip()
            fetch_from_cloud = user_input.get("fetch_from_cloud", False)

            # Validate inputs
            if not new_device_id:
                errors["device_id"] = "required"
            elif len(new_device_id) < 20:
                errors["device_id"] = "invalid_device_id"

            if not new_ip:
                errors["ip_address"] = "required"

            if not fetch_from_cloud and not new_local_key:
                errors[CONF_LOCAL_KEY] = "required"
            elif not fetch_from_cloud and len(new_local_key) != 16:
                errors[CONF_LOCAL_KEY] = "invalid_local_key"

            if not errors:
                if self.entry_id:
                    entry = self.hass.config_entries.async_get_entry(self.entry_id)
                    if entry:
                        # Try to fetch local_key from SmartLife if requested
                        if fetch_from_cloud:
                            new_local_key = await self._fetch_local_key_from_cloud(
                                new_device_id
                            )
                            if not new_local_key:
                                errors["base"] = "cloud_fetch_failed"

                        if not errors:
                            # Get old device_id for device registry cleanup
                            old_device_id = entry.data.get("device_id")

                            # Update config entry
                            new_data = dict(entry.data)
                            new_data["device_id"] = new_device_id
                            new_data["ip_address"] = new_ip
                            new_data[CONF_LOCAL_KEY] = new_local_key

                            self.hass.config_entries.async_update_entry(
                                entry, data=new_data
                            )

                            # Remove old device from device registry before reload
                            # This prevents duplicate devices
                            if old_device_id and old_device_id != new_device_id:
                                from homeassistant.helpers import device_registry as dr
                                dev_reg = dr.async_get(self.hass)
                                old_device = dev_reg.async_get_device(
                                    identifiers={(DOMAIN, old_device_id)}
                                )
                                if old_device:
                                    _LOGGER.info(
                                        f"Removing old device registry entry for {old_device_id}"
                                    )
                                    dev_reg.async_remove_device(old_device.id)

                            # Reload the integration
                            await self.hass.config_entries.async_reload(self.entry_id)

                            _LOGGER.info(
                                f"Updated device_id to {new_device_id}, "
                                f"IP to {new_ip} for entry {self.entry_id}"
                            )

                            # Mark issue as resolved
                            await self.async_mark_resolved()
                            return self.async_create_entry(data={})

        # Pre-fill with detected values if available
        suggested_device_id = self.new_device_id or self.data.get("old_device_id", "")
        suggested_ip = self.new_ip or self.data.get("old_ip", "")

        return self.async_show_form(
            step_id="update_device",
            data_schema=vol.Schema(
                {
                    vol.Required("device_id", default=suggested_device_id): str,
                    vol.Required("ip_address", default=suggested_ip): str,
                    vol.Optional("fetch_from_cloud", default=True): bool,
                    vol.Optional(CONF_LOCAL_KEY, default=""): str,
                }
            ),
            errors=errors,
            description_placeholders={
                "entry_title": self.data.get("entry_title", "Unknown"),
                "old_device_id": self.data.get("old_device_id", "Unknown"),
                "new_device_id": self.new_device_id or "Not detected",
                "old_ip": self.data.get("old_ip", "Unknown"),
                "new_ip": self.new_ip or "Not detected",
            },
        )

    async def _fetch_local_key_from_cloud(self, device_id: str) -> str | None:
        """Try to fetch local_key from SmartLife cloud."""
        try:
            # Find parent account entry
            if not self.entry_id:
                _LOGGER.warning("No entry_id available for cloud fetch")
                return None

            entry = self.hass.config_entries.async_get_entry(self.entry_id)
            if not entry:
                _LOGGER.warning(f"Config entry {self.entry_id} not found")
                return None

            parent_entry_id = entry.data.get("parent_entry_id")
            if not parent_entry_id:
                _LOGGER.warning(f"No parent_entry_id in config entry {self.entry_id}")
                return None

            parent_entry = self.hass.config_entries.async_get_entry(parent_entry_id)
            if not parent_entry:
                _LOGGER.warning(f"Parent config entry {parent_entry_id} not found")
                return None

            # Get SmartLife client from coordinator
            from .clients.tuya_sharing_client import TuyaSharingClient

            token_info = parent_entry.data.get("smartlife_token_info", {})
            if not token_info:
                _LOGGER.warning("No smartlife_token_info in parent entry")
                return None

            _LOGGER.info(f"Creating TuyaSharingClient to fetch local_key for {device_id}")

            # Add user_code to token_info if missing (needed for restoration)
            full_token_info = dict(token_info)
            if "user_code" not in full_token_info:
                user_code = parent_entry.data.get("smartlife_user_code")
                if user_code:
                    full_token_info["user_code"] = user_code
                else:
                    _LOGGER.warning("No user_code available for SmartLife client")
                    return None

            client = await TuyaSharingClient.async_from_stored_tokens(self.hass, full_token_info)

            # Get device info including local_key
            devices = await client.async_get_devices()

            # Log all available devices for debugging (TuyaSharingDevice objects)
            device_ids = [d.device_id for d in devices]
            _LOGGER.info(f"SmartLife returned {len(devices)} devices: {device_ids}")

            for device in devices:
                if device.device_id == device_id:
                    if device.local_key:
                        _LOGGER.info(f"Fetched local_key from cloud for {device_id}")
                        return device.local_key
                    else:
                        _LOGGER.warning(f"Device {device_id} found but has no local_key")
                        return None

            _LOGGER.warning(f"Device {device_id} not found in SmartLife. Available: {device_ids}")
            return None

        except Exception as e:
            _LOGGER.error(f"Failed to fetch local_key from cloud: {e}", exc_info=True)
            return None

    async def async_mark_resolved(self) -> None:
        """Mark the issue as resolved."""
        ir.async_delete_issue(self.hass, DOMAIN, self.issue_id)
