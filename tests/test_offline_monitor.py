"""Test the long-offline repair issue."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from custom_components.kkt_kolbe.const import DOMAIN
from custom_components.kkt_kolbe.offline_monitor import OfflineMonitor
from custom_components.kkt_kolbe.offline_monitor import async_remove_issue
from custom_components.kkt_kolbe.offline_monitor import issue_id


@pytest.mark.asyncio
async def test_issue_after_24h_and_cleared_on_recovery(
    hass: HomeAssistant, mock_config_entry, freezer: FrozenDateTimeFactory
) -> None:
    """Only a long outage raises the issue; recovery clears it."""
    mock_config_entry.add_to_hass(hass)
    coordinator = MagicMock()
    listeners: list = []
    coordinator.async_add_listener = lambda cb: listeners.append(cb) or (lambda: None)
    monitor = OfflineMonitor(hass, mock_config_entry, coordinator)
    monitor.async_start()
    registry = ir.async_get(hass)

    coordinator.last_update_success = False
    listeners[0]()
    freezer.tick(timedelta(hours=23))
    monitor._async_check()
    assert registry.async_get_issue(DOMAIN, issue_id(mock_config_entry)) is None

    freezer.tick(timedelta(hours=2))
    monitor._async_check()
    issue = registry.async_get_issue(DOMAIN, issue_id(mock_config_entry))
    assert issue is not None
    assert issue.translation_key == "device_offline"

    coordinator.last_update_success = True
    listeners[0]()
    assert registry.async_get_issue(DOMAIN, issue_id(mock_config_entry)) is None
    assert monitor.offline_since is None

    await mock_config_entry._async_process_on_unload(hass)


@pytest.mark.asyncio
async def test_issue_removed_with_entry(hass: HomeAssistant, mock_config_entry) -> None:
    """Removing the entry drops its issue."""
    mock_config_entry.add_to_hass(hass)
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id(mock_config_entry),
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="device_offline",
    )
    async_remove_issue(hass, mock_config_entry)
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id(mock_config_entry)) is None
