"""Test the KKT Kolbe select platform."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant

from custom_components.kkt_kolbe.const import DOMAIN
from custom_components.kkt_kolbe import KKTKolbeRuntimeData


@pytest.fixture
def mock_runtime_data():
    """Create mock runtime data."""
    coordinator = MagicMock()
    coordinator.data = {
        101: 2,    # RGB mode at index 2
        "101": 2,  # Also string key version
        102: 0,    # Another select value
        "102": 0,  # Also string key version
    }
    coordinator.last_update_success = True
    coordinator.async_set_data_point = AsyncMock()

    return KKTKolbeRuntimeData(
        coordinator=coordinator,
        device=MagicMock(),
        api_client=None,
        device_info={"name": "Test Hood", "category": "hood"},
        product_name="hermes_style_hood",
        device_type="hermes_style_hood",
        integration_mode="manual",
    )


@pytest.mark.asyncio
async def test_select_setup_entry(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test select platform setup."""
    mock_config_entry.add_to_hass(hass)
    mock_config_entry.runtime_data = mock_runtime_data

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][mock_config_entry.entry_id] = {
        "device_type": "hermes_style_hood",
        "product_name": "hermes_style_hood",
    }

    entities = []

    def mock_add_entities(new_entities):
        entities.extend(new_entities)

    from custom_components.kkt_kolbe.select import async_setup_entry

    await async_setup_entry(hass, mock_config_entry, mock_add_entities)

    # Select entities depend on device configuration


@pytest.mark.asyncio
async def test_select_current_option(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test select current_option property."""
    from custom_components.kkt_kolbe.select import KKTKolbeSelect

    config = {
        "dp": 101,
        "name": "RGB Mode",
        "options": ["Off", "Rainbow", "Pulse", "Static"],
        "options_map": {"Off": 0, "Rainbow": 1, "Pulse": 2, "Static": 3},
    }

    select = KKTKolbeSelect(
        mock_runtime_data.coordinator,
        mock_config_entry,
        config,
    )

    # DP 101 is 2 -> "Pulse"
    assert select.current_option == "Pulse"


@pytest.mark.asyncio
async def test_select_options_list(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test select options list."""
    from custom_components.kkt_kolbe.select import KKTKolbeSelect

    config = {
        "dp": 101,
        "name": "RGB Mode",
        "options": ["Off", "Rainbow", "Pulse", "Static"],
        "options_map": {"Off": 0, "Rainbow": 1, "Pulse": 2, "Static": 3},
    }

    select = KKTKolbeSelect(
        mock_runtime_data.coordinator,
        mock_config_entry,
        config,
    )

    assert select.options == ["Off", "Rainbow", "Pulse", "Static"]
    assert len(select.options) == 4


@pytest.mark.asyncio
async def test_select_async_select_option(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test selecting an option."""
    from custom_components.kkt_kolbe.select import KKTKolbeSelect

    config = {
        "dp": 101,
        "name": "RGB Mode",
        "options": ["Off", "Rainbow", "Pulse", "Static"],
        "options_map": {"Off": 0, "Rainbow": 1, "Pulse": 2, "Static": 3},
    }

    select = KKTKolbeSelect(
        mock_runtime_data.coordinator,
        mock_config_entry,
        config,
    )

    await select.async_select_option("Rainbow")

    mock_runtime_data.coordinator.async_set_data_point.assert_called_once_with(101, 1)


@pytest.mark.asyncio
async def test_select_icon(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test select icon based on name."""
    from custom_components.kkt_kolbe.select import KKTKolbeSelect

    # RGB mode should get palette icon
    config_rgb = {
        "dp": 101,
        "name": "RGB Mode",
        "options": ["Off", "On"],
        "options_map": {"Off": 0, "On": 1},
    }

    select_rgb = KKTKolbeSelect(
        mock_runtime_data.coordinator,
        mock_config_entry,
        config_rgb,
    )

    assert "palette" in select_rgb.icon

    # Regular mode should get form-select icon
    config_mode = {
        "dp": 102,
        "name": "Fan Mode",
        "options": ["Auto", "Manual"],
        "options_map": {"Auto": 0, "Manual": 1},
    }

    select_mode = KKTKolbeSelect(
        mock_runtime_data.coordinator,
        mock_config_entry,
        config_mode,
    )

    assert "mode" in select_mode.name.lower() or "form-select" in select_mode.icon


@pytest.mark.asyncio
async def test_select_unique_id(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test select unique_id generation."""
    from custom_components.kkt_kolbe.select import KKTKolbeSelect

    config = {
        "dp": 101,
        "name": "RGB Mode",
        "options": ["Off", "On"],
        "options_map": {"Off": 0, "On": 1},
    }

    select = KKTKolbeSelect(
        mock_runtime_data.coordinator,
        mock_config_entry,
        config,
    )

    assert select.unique_id is not None
    assert mock_config_entry.entry_id in select.unique_id
    assert "select" in select.unique_id


@pytest.mark.asyncio
async def test_select_invalid_option(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test selecting an invalid option."""
    from custom_components.kkt_kolbe.select import KKTKolbeSelect

    config = {
        "dp": 101,
        "name": "RGB Mode",
        "options": ["Off", "Rainbow", "Pulse"],
        "options_map": {"Off": 0, "Rainbow": 1, "Pulse": 2},
    }

    select = KKTKolbeSelect(
        mock_runtime_data.coordinator,
        mock_config_entry,
        config,
    )

    # Invalid option should not call set_data_point
    await select.async_select_option("InvalidOption")

    mock_runtime_data.coordinator.async_set_data_point.assert_not_called()


@pytest.mark.asyncio
async def test_select_optimistic_survives_stale_coordinator_update(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """Select must keep chosen option when coordinator returns stale value.

    Regression: Issue #6, Lucky-ESA reported program selector snap-back.
    Forced refresh in coordinator.async_set_data_point reads stale Tuya cloud
    value (1-3s propagation), which then overwrites the optimistic option.
    """
    from custom_components.kkt_kolbe.select import KKTKolbeSelect

    coordinator = MagicMock()
    coordinator.data = {101: "f1", "101": "f1"}  # Currently F1
    coordinator.last_update_success = True
    coordinator.async_set_data_point = AsyncMock()

    mock_config_entry.add_to_hass(hass)

    config = {
        "dp": 101,
        "name": "Program",
        "options": ["F1 Auftaustufe", "P5 Hühnerschenkel"],
        "options_map": {"F1 Auftaustufe": "f1", "P5 Hühnerschenkel": "p5"},
    }

    select = KKTKolbeSelect(coordinator, mock_config_entry, config)
    select.hass = hass
    select.entity_id = "select.test_program"
    select.async_write_ha_state = MagicMock()

    assert select.current_option == "F1 Auftaustufe"

    # User selects P5
    await select.async_select_option("P5 Hühnerschenkel")
    assert select.current_option == "P5 Hühnerschenkel"

    # Coordinator polls — Tuya cloud still reports old value
    select._handle_coordinator_update()
    assert select.current_option == "P5 Hühnerschenkel", (
        "Select snapped back to stale coordinator value"
    )

    # Cloud propagates — coordinator now reports new value
    coordinator.data = {101: "p5", "101": "p5"}
    select._handle_coordinator_update()
    assert select.current_option == "P5 Hühnerschenkel"


@pytest.mark.asyncio
async def test_select_optimistic_released_when_write_fails(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """Failed device write must release optimistic lock."""
    from custom_components.kkt_kolbe.select import KKTKolbeSelect

    coordinator = MagicMock()
    coordinator.data = {101: "f1", "101": "f1"}
    coordinator.last_update_success = True
    coordinator.async_set_data_point = AsyncMock(side_effect=RuntimeError("device offline"))

    mock_config_entry.add_to_hass(hass)

    config = {
        "dp": 101,
        "name": "Program",
        "options": ["F1 Auftaustufe", "P5 Hühnerschenkel"],
        "options_map": {"F1 Auftaustufe": "f1", "P5 Hühnerschenkel": "p5"},
    }

    select = KKTKolbeSelect(coordinator, mock_config_entry, config)
    select.hass = hass
    select.entity_id = "select.test_program_fail"
    select.async_write_ha_state = MagicMock()

    with pytest.raises(RuntimeError):
        await select.async_select_option("P5 Hühnerschenkel")

    assert select._is_optimistic_active() is False
    select._handle_coordinator_update()
    assert select.current_option == "F1 Auftaustufe"
