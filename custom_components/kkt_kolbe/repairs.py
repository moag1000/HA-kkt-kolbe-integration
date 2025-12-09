"""Repair flow for KKT Kolbe integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import data_entry_flow
from homeassistant.components.repairs import RepairsFlow
from homeassistant.const import CONF_DEVICE_ID, CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import (
    CONF_API_CLIENT_ID,
    CONF_API_CLIENT_SECRET,
    CONF_API_ENDPOINT,
    DOMAIN,
)

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
            region = user_input.get("region")
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
