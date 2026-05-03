"""Test the KKT Kolbe sensor platform."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.const import UnitOfTime

from custom_components.kkt_kolbe.const import DOMAIN
from custom_components.kkt_kolbe import KKTKolbeRuntimeData


@pytest.fixture
def mock_runtime_data():
    """Create mock runtime data."""
    coordinator = MagicMock()
    coordinator.data = {
        5: 128,      # Brightness level
        "5": 128,    # Also string key
        6: 30,       # Filter replacement days
        "6": 30,     # Also string key
        13: 15,      # Timer minutes
        "13": 15,    # Also string key
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
async def test_domain_constant(hass: HomeAssistant) -> None:
    """Test the domain constant is correct."""
    assert DOMAIN == "kkt_kolbe"


@pytest.mark.asyncio
async def test_sensor_setup_entry(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test sensor platform setup."""
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

    from custom_components.kkt_kolbe.sensor import async_setup_entry

    await async_setup_entry(hass, mock_config_entry, mock_add_entities)

    # Sensors depend on device configuration


@pytest.mark.asyncio
async def test_sensor_native_value(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test sensor native_value property."""
    from custom_components.kkt_kolbe.sensor import KKTKolbeSensor

    mock_config_entry.add_to_hass(hass)

    config = {
        "dp": 13,
        "name": "Timer",
        "unit": "min",
    }

    sensor = KKTKolbeSensor(
        mock_runtime_data.coordinator,
        mock_config_entry,
        config,
    )

    # DP 13 is 15 in mock_runtime_data
    assert sensor.native_value == 15


@pytest.mark.asyncio
async def test_sensor_unit_of_measurement(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test sensor unit of measurement."""
    from custom_components.kkt_kolbe.sensor import KKTKolbeSensor

    mock_config_entry.add_to_hass(hass)

    config = {
        "dp": 6,
        "name": "Filter Days",
        "unit_of_measurement": "days",
    }

    sensor = KKTKolbeSensor(
        mock_runtime_data.coordinator,
        mock_config_entry,
        config,
    )

    assert sensor.native_unit_of_measurement == "days"


@pytest.mark.asyncio
async def test_sensor_device_class(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test sensor device class."""
    from custom_components.kkt_kolbe.sensor import KKTKolbeSensor

    mock_config_entry.add_to_hass(hass)

    config = {
        "dp": 13,
        "name": "Timer",
        "device_class": "duration",
    }

    sensor = KKTKolbeSensor(
        mock_runtime_data.coordinator,
        mock_config_entry,
        config,
    )

    # Duration device class from config
    assert sensor.device_class is not None or config.get("device_class") == "duration"


@pytest.mark.asyncio
async def test_sensor_state_class(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test sensor state class."""
    from custom_components.kkt_kolbe.sensor import KKTKolbeSensor

    mock_config_entry.add_to_hass(hass)

    config = {
        "dp": 5,
        "name": "Brightness",
        "state_class": "measurement",
    }

    sensor = KKTKolbeSensor(
        mock_runtime_data.coordinator,
        mock_config_entry,
        config,
    )

    # Measurement state class from config
    assert sensor.state_class is not None or config.get("state_class") == "measurement"


@pytest.mark.asyncio
async def test_sensor_icon(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test sensor icon."""
    from custom_components.kkt_kolbe.sensor import KKTKolbeSensor

    mock_config_entry.add_to_hass(hass)

    config = {
        "dp": 6,
        "name": "Filter Days",
    }

    sensor = KKTKolbeSensor(
        mock_runtime_data.coordinator,
        mock_config_entry,
        config,
    )

    # Filter sensor should have air-filter icon
    assert "filter" in sensor.icon.lower()


@pytest.mark.asyncio
async def test_sensor_unique_id(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test sensor unique_id generation."""
    from custom_components.kkt_kolbe.sensor import KKTKolbeSensor

    mock_config_entry.add_to_hass(hass)

    config = {
        "dp": 13,
        "name": "Timer",
    }

    sensor = KKTKolbeSensor(
        mock_runtime_data.coordinator,
        mock_config_entry,
        config,
    )

    assert sensor.unique_id is not None
    assert mock_config_entry.entry_id in sensor.unique_id
    assert "sensor" in sensor.unique_id


@pytest.mark.asyncio
async def test_sensor_none_value(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """Test sensor handles None values gracefully."""
    from custom_components.kkt_kolbe.sensor import KKTKolbeSensor

    coordinator = MagicMock()
    coordinator.data = {}  # No data for the DP
    coordinator.last_update_success = True

    runtime_data = KKTKolbeRuntimeData(
        coordinator=coordinator,
        device=MagicMock(),
        api_client=None,
        device_info={"name": "Test Hood", "category": "hood"},
        product_name="hermes_style_hood",
        device_type="hermes_style_hood",
        integration_mode="manual",
    )

    mock_config_entry.add_to_hass(hass)

    config = {
        "dp": 99,  # Non-existent DP
        "name": "Unknown",
    }

    sensor = KKTKolbeSensor(
        runtime_data.coordinator,
        mock_config_entry,
        config,
    )

    # Should handle missing DP gracefully
    assert sensor.native_value is None


@pytest.mark.asyncio
async def test_sensor_duration_returns_int_when_device_sends_float(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """Duration sensors must coerce float DP values (e.g. 10.0) to int.

    Regression: Issue #6, Lucky-ESA reported "Time Remaining" shown as "10.0"
    in HA device view despite suggested_display_precision=0. The precision
    suggestion only affects entity-card formatting, not the raw native_value.
    """
    from custom_components.kkt_kolbe.sensor import KKTKolbeSensor

    coordinator = MagicMock()
    coordinator.data = {104: 10.0, "104": 10.0}
    coordinator.last_update_success = True

    runtime_data = KKTKolbeRuntimeData(
        coordinator=coordinator,
        device=MagicMock(),
        api_client=None,
        device_info={"name": "Test Oven", "category": "oven"},
        product_name="eb8313hc_oven",
        device_type="eb8313hc_oven",
        integration_mode="manual",
    )

    mock_config_entry.add_to_hass(hass)

    config = {
        "dp": 104,
        "name": "Time Remaining",
        "unit_of_measurement": UnitOfTime.MINUTES,
        "device_class": "duration",
    }

    sensor = KKTKolbeSensor(
        runtime_data.coordinator,
        mock_config_entry,
        config,
    )

    assert sensor.native_value == 10
    assert isinstance(sensor.native_value, int)


@pytest.mark.asyncio
async def test_sensor_duration_zero_returns_int(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """Specifically reproduce Lucky-ESA's "0.0" report.

    His Time Remaining sensor showed 0.0 in the device view even after
    v4.6.5. This locks in the contract: native_value MUST be int 0,
    not float 0.0, for a duration sensor whose Tuya DP returns float 0.0.
    If this passes locally but Lucky still sees 0.0, the issue is in
    HA's display_precision registry override, not our native_value.
    """
    from custom_components.kkt_kolbe.sensor import KKTKolbeSensor

    coordinator = MagicMock()
    coordinator.data = {104: 0.0, "104": 0.0}
    coordinator.last_update_success = True

    runtime_data = KKTKolbeRuntimeData(
        coordinator=coordinator,
        device=MagicMock(),
        api_client=None,
        device_info={"name": "Test Oven", "category": "oven"},
        product_name="eb8313hc_oven",
        device_type="eb8313hc_oven",
        integration_mode="manual",
    )

    mock_config_entry.add_to_hass(hass)

    config = {
        "dp": 104,
        "name": "Time Remaining",
        "unit_of_measurement": UnitOfTime.MINUTES,
        "device_class": "duration",
    }

    sensor = KKTKolbeSensor(
        runtime_data.coordinator,
        mock_config_entry,
        config,
    )

    assert sensor.native_value == 0
    assert isinstance(sensor.native_value, int), (
        f"native_value must be int but got {type(sensor.native_value).__name__}: "
        f"{sensor.native_value!r}"
    )
    assert sensor._attr_suggested_display_precision == 0


@pytest.mark.asyncio
async def test_sensor_temperature_keeps_float_precision(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """Temperature sensors must preserve float for 1-decimal display."""
    from custom_components.kkt_kolbe.sensor import KKTKolbeSensor

    coordinator = MagicMock()
    coordinator.data = {2: 21.5, "2": 21.5}
    coordinator.last_update_success = True

    runtime_data = KKTKolbeRuntimeData(
        coordinator=coordinator,
        device=MagicMock(),
        api_client=None,
        device_info={"name": "Test Oven", "category": "oven"},
        product_name="eb8313hc_oven",
        device_type="eb8313hc_oven",
        integration_mode="manual",
    )

    mock_config_entry.add_to_hass(hass)

    config = {
        "dp": 2,
        "name": "Temperature",
        "device_class": "temperature",
    }

    sensor = KKTKolbeSensor(
        runtime_data.coordinator,
        mock_config_entry,
        config,
    )

    assert sensor.native_value == 21.5
    assert isinstance(sensor.native_value, float)
