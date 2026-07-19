"""Test the KKT Kolbe number platform."""
from __future__ import annotations

from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant

from custom_components.kkt_kolbe import KKTKolbeRuntimeData
from custom_components.kkt_kolbe.const import DOMAIN


@pytest.fixture
def mock_runtime_data():
    """Create mock runtime data."""
    coordinator = MagicMock()
    coordinator.data = {
        13: 30,    # Timer at 30 minutes
        "13": 30,  # Also string key version
        101: 5,    # RGB mode
        "101": 5,  # Also string key version
        5: 200,    # Light brightness
        "5": 200,  # Also string key version
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
async def test_number_setup_entry(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test number platform setup."""
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

    from custom_components.kkt_kolbe.number import async_setup_entry

    await async_setup_entry(hass, mock_config_entry, mock_add_entities)

    # Should have number entities


@pytest.mark.asyncio
async def test_number_native_value(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test number native_value property."""
    from custom_components.kkt_kolbe.number import KKTKolbeNumber

    config = {
        "dp": 13,
        "name": "Timer",
        "min": 0,
        "max": 60,
    }

    number = KKTKolbeNumber(
        mock_runtime_data.coordinator,
        mock_config_entry,
        config,
    )

    # DP 13 is 30 in mock_runtime_data
    assert number.native_value == 30.0


@pytest.mark.asyncio
async def test_number_set_value(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test setting number value."""
    from custom_components.kkt_kolbe.number import KKTKolbeNumber

    config = {
        "dp": 13,
        "name": "Timer",
        "min": 0,
        "max": 60,
    }

    number = KKTKolbeNumber(
        mock_runtime_data.coordinator,
        mock_config_entry,
        config,
    )

    await number.async_set_native_value(45.0)

    mock_runtime_data.coordinator.async_set_data_point.assert_called_once_with(13, 45)


@pytest.mark.asyncio
async def test_number_min_max_values(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test number min/max values."""
    from custom_components.kkt_kolbe.number import KKTKolbeNumber

    config = {
        "dp": 13,
        "name": "Timer",
        "min": 0,
        "max": 60,
        "step": 5,
    }

    number = KKTKolbeNumber(
        mock_runtime_data.coordinator,
        mock_config_entry,
        config,
    )

    assert number.native_min_value == 0
    assert number.native_max_value == 60
    assert number.native_step == 5


@pytest.mark.asyncio
async def test_number_display_precision(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test number display precision for timer."""
    from custom_components.kkt_kolbe.number import KKTKolbeNumber

    config = {
        "dp": 13,
        "name": "Timer",
        "min": 0,
        "max": 60,
    }

    number = KKTKolbeNumber(
        mock_runtime_data.coordinator,
        mock_config_entry,
        config,
    )

    # Timer should have no decimals (access internal attribute for unit tests)
    assert number._attr_suggested_display_precision == 0


@pytest.mark.asyncio
async def test_number_icon(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test number icon based on name."""
    from custom_components.kkt_kolbe.number import KKTKolbeNumber

    # Timer should get timer icon
    config_timer = {
        "dp": 13,
        "name": "Timer",
        "min": 0,
        "max": 60,
    }

    number_timer = KKTKolbeNumber(
        mock_runtime_data.coordinator,
        mock_config_entry,
        config_timer,
    )

    assert "timer" in number_timer.icon.lower()


@pytest.mark.asyncio
async def test_number_unique_id(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test number unique_id generation."""
    from custom_components.kkt_kolbe.number import KKTKolbeNumber

    config = {
        "dp": 13,
        "name": "Timer",
        "min": 0,
        "max": 60,
    }

    number = KKTKolbeNumber(
        mock_runtime_data.coordinator,
        mock_config_entry,
        config,
    )

    assert number.unique_id is not None
    assert mock_config_entry.entry_id in number.unique_id
    assert "number" in number.unique_id


@pytest.mark.asyncio
async def test_number_optimistic_survives_stale_coordinator_update(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """Number must keep set value when coordinator returns stale value (Issue #6)."""
    from custom_components.kkt_kolbe.number import KKTKolbeNumber

    coordinator = MagicMock()
    coordinator.data = {103: 30, "103": 30}  # Currently 30 min
    coordinator.last_update_success = True
    coordinator.async_set_data_point = AsyncMock()

    mock_config_entry.add_to_hass(hass)

    config = {
        "dp": 103,
        "name": "Timer",
        "min": 0,
        "max": 360,
        "unit": "min",
        "device_class": "duration",
    }

    number = KKTKolbeNumber(coordinator, mock_config_entry, config)
    number.hass = hass
    number.entity_id = "number.test_timer"
    number.async_write_ha_state = MagicMock()

    assert number.native_value == 30.0

    # User sets timer to 60
    await number.async_set_native_value(60)
    assert number.native_value == 60.0

    # Coordinator polls — Tuya cloud still reports old value
    number._handle_coordinator_update()
    assert number.native_value == 60.0, "Number snapped back to stale value"

    # Cloud propagates
    coordinator.data = {103: 60, "103": 60}
    number._handle_coordinator_update()
    assert number.native_value == 60.0


@pytest.mark.asyncio
async def test_number_optimistic_released_when_write_fails(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """Failed device write must release optimistic lock."""
    from custom_components.kkt_kolbe.number import KKTKolbeNumber

    coordinator = MagicMock()
    coordinator.data = {103: 30, "103": 30}
    coordinator.last_update_success = True
    coordinator.async_set_data_point = AsyncMock(side_effect=RuntimeError("device offline"))

    mock_config_entry.add_to_hass(hass)

    config = {
        "dp": 103,
        "name": "Timer",
        "min": 0,
        "max": 360,
        "unit": "min",
        "device_class": "duration",
    }

    number = KKTKolbeNumber(coordinator, mock_config_entry, config)
    number.hass = hass
    number.entity_id = "number.test_timer_fail"
    number.async_write_ha_state = MagicMock()

    with pytest.raises(RuntimeError):
        await number.async_set_native_value(60)

    assert number._is_optimistic_active() is False
    number._handle_coordinator_update()
    assert number.native_value == 30.0


# =============== ZONE NUMBER OPTIMISTIC WRITE TESTS ===============


@pytest.mark.asyncio
async def test_zone_number_set_native_value_optimistic_immediate(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """KKTKolbeZoneNumber must paint native_value to the target immediately
    (non-bitfield path), before any coordinator poll confirms the write.

    DP 200 is deliberately NOT in bitfield_utils.BITFIELD_CONFIG so
    async_set_native_value takes the legacy/simple-value fallback path
    (number.py ~line 231-263), not the Base64 bitfield path.
    """
    from custom_components.kkt_kolbe.number import KKTKolbeZoneNumber

    coordinator = MagicMock()
    coordinator.data = {200: 1, "200": 1}
    coordinator.last_update_success = True
    coordinator.async_set_data_point = AsyncMock()

    mock_config_entry.add_to_hass(hass)

    config = {
        "dp": 200,
        "name": "Zone Power Level",
        "zone": 1,
        "min_value": 0,
        "max_value": 9,
    }

    number = KKTKolbeZoneNumber(coordinator, mock_config_entry, config)
    number.hass = hass
    number.entity_id = "number.test_zone_optimistic"
    number.async_write_ha_state = MagicMock()

    await number.async_set_native_value(7)

    assert number.native_value == 7.0, (
        "KKTKolbeZoneNumber.async_set_native_value must paint native_value to "
        "the target immediately, without waiting for a coordinator poll."
    )
    coordinator.async_set_data_point.assert_called_once_with(200, 7)


@pytest.mark.asyncio
async def test_zone_number_set_native_value_rolls_back_on_write_failure(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """A failed device write must roll the zone number back to its prior value."""
    from custom_components.kkt_kolbe.number import KKTKolbeZoneNumber

    coordinator = MagicMock()
    coordinator.data = {200: 1, "200": 1}
    coordinator.last_update_success = True
    coordinator.async_set_data_point = AsyncMock(side_effect=RuntimeError("device offline"))

    mock_config_entry.add_to_hass(hass)

    config = {
        "dp": 200,
        "name": "Zone Power Level",
        "zone": 1,
        "min_value": 0,
        "max_value": 9,
    }

    number = KKTKolbeZoneNumber(coordinator, mock_config_entry, config)
    number.hass = hass
    number.entity_id = "number.test_zone_rollback"
    number.async_write_ha_state = MagicMock()

    previous_value = number.native_value

    with pytest.raises(RuntimeError):
        await number.async_set_native_value(7)

    assert number.native_value == previous_value, (
        "After a failed write, KKTKolbeZoneNumber native_value must roll back to "
        "the prior value instead of sticking at the optimistic target."
    )
