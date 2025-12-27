"""Fixtures for KKT Kolbe integration tests."""
from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kkt_kolbe.const import DOMAIN
# Import config_flow to ensure it's registered
import custom_components.kkt_kolbe.config_flow  # noqa: F401


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    yield


@pytest.fixture(autouse=True)
def mock_zeroconf_setup():
    """Mock zeroconf component setup to avoid socket issues in tests."""
    async def mock_async_setup(hass, config):
        """Mock zeroconf async_setup."""
        hass.data["zeroconf"] = MagicMock()
        return True

    with patch(
        "homeassistant.components.zeroconf.async_setup",
        side_effect=mock_async_setup,
    ):
        yield


@pytest.fixture(autouse=True)
def mock_device_tracker_and_discovery():
    """Mock device tracker and discovery to avoid timer and socket issues in tests."""
    # Reset the global tracker instance before each test
    import custom_components.kkt_kolbe.device_tracker as dt
    dt._tracker_instance = None

    # Mock the StaleDeviceTracker class itself to prevent timer creation
    mock_tracker = MagicMock()
    mock_tracker.async_start = AsyncMock()
    mock_tracker.async_stop = AsyncMock()

    with patch.object(dt, "StaleDeviceTracker", return_value=mock_tracker):
        with patch(
            "custom_components.kkt_kolbe.discovery.async_start_discovery",
            new_callable=AsyncMock,
        ):
            with patch(
                "custom_components.kkt_kolbe.discovery.async_stop_discovery",
                new_callable=AsyncMock,
            ):
                yield
                # Reset after test
                dt._tracker_instance = None


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create a mock config entry for testing."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Test KKT Hood",
        data={
            "device_id": "bf735dfe2ad64fba7cpyhn",
            "ip_address": "192.168.1.100",
            "local_key": "1234567890abcdef",
            "integration_mode": "manual",
            "product_name": "hermes_style_hood",
            "device_type": "hermes_style_hood",
        },
        unique_id="bf735dfe2ad64fba7cpyhn",
        version=1,
    )


@pytest.fixture
def mock_config_entry_with_api() -> MockConfigEntry:
    """Create a mock config entry with API credentials."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Test KKT Hood (Hybrid)",
        data={
            "device_id": "bf735dfe2ad64fba7cpyhn",
            "ip_address": "192.168.1.100",
            "local_key": "1234567890abcdef",
            "integration_mode": "hybrid",
            "product_name": "hermes_style_hood",
            "device_type": "hermes_style_hood",
            "api_enabled": True,
            "api_client_id": "test_client_id_123",
            "api_client_secret": "test_client_secret_456",
            "api_endpoint": "https://openapi.tuyaeu.com",
        },
        unique_id="bf735dfe2ad64fba7cpyhn",
        version=1,
    )


@pytest.fixture
def mock_cooktop_config_entry() -> MockConfigEntry:
    """Create a mock config entry for cooktop testing."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Test KKT Cooktop",
        data={
            "device_id": "bf5592b47738c5b46evzff",
            "ip_address": "192.168.1.101",
            "local_key": "abcdef1234567890",
            "integration_mode": "manual",
            "product_name": "ind7705hc_cooktop",
            "device_type": "ind7705hc_cooktop",
        },
        unique_id="bf5592b47738c5b46evzff",
        version=1,
    )


@pytest.fixture
def mock_tuya_device() -> Generator[MagicMock, None, None]:
    """Mock the KKTKolbeTuyaDevice class."""
    with patch(
        "custom_components.kkt_kolbe.tuya_device.KKTKolbeTuyaDevice",
        autospec=True,
    ) as mock_device_class:
        mock_device = MagicMock()
        mock_device.device_id = "bf735dfe2ad64fba7cpyhn"
        mock_device.ip_address = "192.168.1.100"
        mock_device.is_connected = True
        mock_device.version = "3.3"

        # Mock async methods
        mock_device.async_connect = AsyncMock(return_value=True)
        mock_device.async_get_status = AsyncMock(return_value={
            "1": True,   # Power
            "4": False,  # Light
            "10": "off", # Fan speed
        })
        mock_device.async_set_dp = AsyncMock(return_value=True)

        mock_device_class.return_value = mock_device
        yield mock_device


@pytest.fixture
def mock_coordinator() -> Generator[MagicMock, None, None]:
    """Mock the KKTKolbeUpdateCoordinator class."""
    with patch(
        "custom_components.kkt_kolbe.coordinator.KKTKolbeUpdateCoordinator",
        autospec=True,
    ) as mock_coordinator_class:
        mock_coordinator = MagicMock()
        mock_coordinator.data = {
            "1": True,   # Power
            "4": False,  # Light
            "10": "off", # Fan speed
        }
        mock_coordinator.last_update_success = True
        mock_coordinator.last_update_success_time = None

        # Mock async methods
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator.async_refresh = AsyncMock()

        mock_coordinator_class.return_value = mock_coordinator
        yield mock_coordinator


@pytest.fixture
def mock_api_client() -> Generator[MagicMock, None, None]:
    """Mock the TuyaCloudClient class."""
    with patch(
        "custom_components.kkt_kolbe.api.TuyaCloudClient",
        autospec=True,
    ) as mock_client_class:
        mock_client = MagicMock()
        mock_client.is_authenticated = True
        mock_client._access_token = "mock_token"

        # Mock async methods
        mock_client.test_connection = AsyncMock(return_value=True)
        mock_client.get_device_status = AsyncMock(return_value={
            "1": True,
            "4": False,
            "10": "off",
        })
        mock_client.get_device_local_key = AsyncMock(return_value="1234567890abcdef")

        mock_client_class.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_discovery() -> Generator[MagicMock, None, None]:
    """Mock the discovery module."""
    with patch(
        "custom_components.kkt_kolbe.discovery.async_start_discovery",
        new_callable=AsyncMock,
    ) as mock_start:
        with patch(
            "custom_components.kkt_kolbe.discovery.async_stop_discovery",
            new_callable=AsyncMock,
        ) as mock_stop:
            yield {"start": mock_start, "stop": mock_stop}


@pytest.fixture
def mock_device_tracker() -> Generator[AsyncMock, None, None]:
    """Mock the device tracker module."""
    with patch(
        "custom_components.kkt_kolbe.device_tracker.async_start_tracker",
        new_callable=AsyncMock,
    ) as mock_tracker:
        yield mock_tracker


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock, None, None]:
    """Mock successful setup of the config entry."""
    with patch(
        "custom_components.kkt_kolbe.async_setup_entry",
        return_value=True,
    ) as mock_setup:
        yield mock_setup
