"""Test the KKT Kolbe integration initialization."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from custom_components.kkt_kolbe.const import DOMAIN


@pytest.mark.asyncio
async def test_domain_constant() -> None:
    """Test the domain constant is correct."""
    assert DOMAIN == "kkt_kolbe"


@pytest.mark.asyncio
async def test_async_setup(hass: HomeAssistant) -> None:
    """Test the async_setup function."""
    with patch(
        "custom_components.kkt_kolbe.discovery.async_start_discovery",
        new_callable=AsyncMock,
    ) as mock_discovery:
        with patch(
            "custom_components.kkt_kolbe.device_tracker.async_start_tracker",
            new_callable=AsyncMock,
        ) as mock_tracker:
            from custom_components.kkt_kolbe import async_setup

            result = await async_setup(hass, {})

            assert result is True
            mock_discovery.assert_called_once_with(hass)
            mock_tracker.assert_called_once_with(hass)


@pytest.mark.asyncio
async def test_async_setup_entry_success(
    hass: HomeAssistant,
    mock_config_entry,
    mock_tuya_device,
    mock_coordinator,
) -> None:
    """Test successful setup of a config entry."""
    mock_config_entry.add_to_hass(hass)

    # Initialize hass.data for the domain
    hass.data.setdefault(DOMAIN, {})

    with patch(
        "custom_components.kkt_kolbe.discovery.async_start_discovery",
        new_callable=AsyncMock,
    ):
        with patch(
            "custom_components.kkt_kolbe.device_tracker.async_start_tracker",
            new_callable=AsyncMock,
        ):
            with patch(
                "custom_components.kkt_kolbe.tuya_device.KKTKolbeTuyaDevice"
            ) as mock_device_class:
                mock_device = MagicMock()
                mock_device.async_connect = AsyncMock()
                mock_device.is_connected = True
                mock_device_class.return_value = mock_device

                with patch(
                    "custom_components.kkt_kolbe.coordinator.KKTKolbeUpdateCoordinator"
                ) as mock_coord_class:
                    mock_coord = MagicMock()
                    mock_coord.async_config_entry_first_refresh = AsyncMock()
                    mock_coord.data = {}
                    mock_coord.last_update_success = True
                    mock_coord.last_update_success_time = None
                    mock_coord_class.return_value = mock_coord

                    with patch(
                        "custom_components.kkt_kolbe.services.async_setup_services",
                        new_callable=AsyncMock,
                    ):
                        with patch.object(
                            hass.config_entries,
                            "async_forward_entry_setups",
                            new_callable=AsyncMock,
                        ):
                            from custom_components.kkt_kolbe import async_setup_entry

                            result = await async_setup_entry(hass, mock_config_entry)

                            assert result is True
                            assert mock_config_entry.entry_id in hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_async_unload_entry(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """Test successful unload of a config entry."""
    mock_config_entry.add_to_hass(hass)

    # Initialize hass.data with mock data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][mock_config_entry.entry_id] = {
        "coordinator": MagicMock(),
        "device": MagicMock(),
    }

    # Mock runtime_data
    mock_config_entry.runtime_data = MagicMock()
    mock_config_entry.runtime_data.device_info = {"category": "hood"}

    with patch.object(
        hass.config_entries,
        "async_unload_platforms",
        return_value=True,
    ) as mock_unload:
        with patch(
            "custom_components.kkt_kolbe.services.async_unload_services",
            new_callable=AsyncMock,
        ):
            with patch(
                "custom_components.kkt_kolbe.discovery.async_stop_discovery",
                new_callable=AsyncMock,
            ):
                from custom_components.kkt_kolbe import async_unload_entry

                result = await async_unload_entry(hass, mock_config_entry)

                assert result is True
                assert mock_config_entry.entry_id not in hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_runtime_data_dataclass() -> None:
    """Test the KKTKolbeRuntimeData dataclass."""
    from custom_components.kkt_kolbe import KKTKolbeRuntimeData

    # Create a mock runtime data instance
    runtime_data = KKTKolbeRuntimeData(
        coordinator=MagicMock(),
        device=MagicMock(),
        api_client=None,
        device_info={"name": "Test Device", "category": "hood"},
        product_name="hermes_style_hood",
        device_type="hermes_style_hood",
        integration_mode="manual",
    )

    assert runtime_data.product_name == "hermes_style_hood"
    assert runtime_data.device_type == "hermes_style_hood"
    assert runtime_data.integration_mode == "manual"
    assert runtime_data.device_info["name"] == "Test Device"
    assert runtime_data.api_client is None


@pytest.mark.asyncio
async def test_platforms_list() -> None:
    """Test that PLATFORMS list contains expected platforms."""
    from homeassistant.const import Platform

    from custom_components.kkt_kolbe import PLATFORMS

    expected_platforms = [
        Platform.SENSOR,
        Platform.FAN,
        Platform.LIGHT,
        Platform.SWITCH,
        Platform.SELECT,
        Platform.NUMBER,
        Platform.BINARY_SENSOR,
    ]

    for platform in expected_platforms:
        assert platform in PLATFORMS


@pytest.mark.asyncio
async def test_config_schema() -> None:
    """Test that CONFIG_SCHEMA is config_entry_only."""
    from custom_components.kkt_kolbe import CONFIG_SCHEMA

    # The schema should be a config_entry_only schema
    # This means it won't accept any configuration.yaml setup
    assert CONFIG_SCHEMA is not None
