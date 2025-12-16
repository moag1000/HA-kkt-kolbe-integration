"""Fixtures for KKT Kolbe integration tests."""
import pytest
from unittest.mock import MagicMock, AsyncMock

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kkt_kolbe.const import DOMAIN


@pytest.fixture
def mock_config_entry():
    """Mock ConfigEntry for testing."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Test KKT Device",
        data={
            "device_id": "test_device_id_12345",
            "ip_address": "192.168.1.100",
            "local_key": "test_local_key_1",
            "integration_mode": "manual",
            "product_name": "KKT DH9509NP",
        },
        unique_id="test_device_id_12345",
    )
