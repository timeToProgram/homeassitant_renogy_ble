"""Tests for the Renogy BLE Home Assistant integration setup and entities."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import CONF_ADDRESS

from custom_components.renogy_ble.const import (
    CONF_DEVICE_IDS,
    CONF_SCAN_INTERVAL,
    DOMAIN,
)


@pytest.mark.asyncio
async def test_integration_setup_and_unload() -> None:
    """Test full integration setup and unload with mock coordinator."""
    hass = MagicMock()
    hass.data = {}
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.data = {
        CONF_ADDRESS: "AA:BB:CC:DD:EE:FF",
        CONF_DEVICE_IDS: [1],
        CONF_SCAN_INTERVAL: 30,
    }
    entry.options = {}

    # Mock Coordinator
    mock_coordinator = MagicMock()
    mock_coordinator.address = "AA:BB:CC:DD:EE:FF"
    mock_coordinator.data = {
        1: {
            "device_type": "controller",
            "model": "Rover-40A",
            "is_available": True,
            "battery_percentage": 90,
            "charging_status": "floating",
            "load_status": False,
        }
    }
    mock_coordinator.async_config_entry_first_refresh = AsyncMock()
    mock_coordinator.async_stop = MagicMock()
    mock_coordinator.async_shutdown = AsyncMock()

    with patch(
        "custom_components.renogy_ble.RenogyActiveBluetoothCoordinator",
        return_value=mock_coordinator,
    ):
        # Load integration
        from custom_components.renogy_ble import async_setup_entry, async_unload_entry

        assert await async_setup_entry(hass, entry) is True
        assert hass.config_entries.async_forward_entry_setups.called

        # Unload integration
        assert await async_unload_entry(hass, entry) is True
        assert mock_coordinator.async_stop.called


@pytest.mark.asyncio
async def test_sensor_setup() -> None:
    """Test sensor platform setup and state updates."""
    hass = MagicMock()
    hass.data = {}

    # Register entry
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.data = {
        CONF_ADDRESS: "AA:BB:CC:DD:EE:FF",
        CONF_DEVICE_IDS: [1],
        CONF_SCAN_INTERVAL: 30,
    }

    mock_coordinator = MagicMock()
    mock_coordinator.address = "AA:BB:CC:DD:EE:FF"
    mock_coordinator.data = {
        1: {
            "device_type": "controller",
            "model": "Rover-40A",
            "is_available": True,
            "battery_percentage": 90,
            "charging_status": "floating",
        }
    }
    mock_coordinator.last_update_success = True

    hass.data[DOMAIN] = {
        entry.entry_id: {
            "coordinator": mock_coordinator,
        }
    }

    # Setup sensor platform
    from custom_components.renogy_ble.sensor import (
        async_setup_entry as async_setup_sensors,
    )

    async_add_entities = MagicMock()
    await async_setup_sensors(hass, entry, async_add_entities)

    assert async_add_entities.called
    created_entities = async_add_entities.call_args[0][0]

    # Find the battery percentage sensor
    battery_sensor = next(
        entity
        for entity in created_entities
        if entity.entity_description.key == "battery_percentage"
    )

    assert battery_sensor.native_value == 90
    assert battery_sensor.available is True
    assert battery_sensor.unique_id == "AA:BB:CC:DD:EE:FF_1_battery_percentage"


@pytest.mark.asyncio
async def test_switch_setup_and_control() -> None:
    """Test switch platform setup, control, and state."""
    hass = MagicMock()
    hass.data = {}

    entry = MagicMock()
    entry.entry_id = "test_entry"

    mock_coordinator = MagicMock()
    mock_coordinator.address = "AA:BB:CC:DD:EE:FF"
    mock_coordinator.data = {
        1: {
            "device_type": "controller",
            "model": "Rover-40A",
            "is_available": True,
            "load_status": True,
        }
    }
    mock_coordinator.last_update_success = True
    mock_coordinator.async_write_register = AsyncMock()

    hass.data[DOMAIN] = {
        entry.entry_id: {
            "coordinator": mock_coordinator,
        }
    }

    # Setup switch platform
    from custom_components.renogy_ble.switch import (
        async_setup_entry as async_setup_switches,
    )

    async_add_entities = MagicMock()
    await async_setup_switches(hass, entry, async_add_entities)

    assert async_add_entities.called
    created_entities = async_add_entities.call_args[0][0]
    assert len(created_entities) == 1

    load_switch = created_entities[0]
    assert load_switch.is_on is True

    # Set hass and mock async_write_ha_state so state write works
    # without HA state machine
    load_switch.hass = hass
    load_switch.async_write_ha_state = MagicMock()

    # Turn off the switch
    await load_switch.async_turn_off()
    # Writes 0 to register 0x010A
    mock_coordinator.async_write_register.assert_called_with(1, 0x010A, 0)


@pytest.mark.asyncio
async def test_battery_aggregate_sensors() -> None:
    """Test setup and functionality of battery aggregate sensors."""
    hass = MagicMock()
    hass.data = {}

    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.data = {
        CONF_ADDRESS: "AA:BB:CC:DD:EE:FF",
        CONF_DEVICE_IDS: [1, 2],
        CONF_SCAN_INTERVAL: 30,
    }

    mock_coordinator = MagicMock()
    mock_coordinator.address = "AA:BB:CC:DD:EE:FF"
    mock_coordinator.data = {
        1: {
            "device_type": "battery",
            "model": "Smart Lithium 1",
            "is_available": True,
            "voltage": 13.2,
            "battery_temperature": 25.0,
            "total_capacity": 100.0,
            "remaining_capacity": 80.0,
            "current": 10.0,
            "power": 132.0,
            "cell_voltages": [3.28, 3.32, 3.30, 3.30],
            "temperatures": [24.8, 25.2],
        },
        2: {
            "device_type": "battery",
            "model": "Smart Lithium 2",
            "is_available": True,
            "voltage": 13.4,
            "battery_temperature": 27.0,
            "total_capacity": 100.0,
            "remaining_capacity": 90.0,
            "current": 15.0,
            "power": 201.0,
            "cell_voltages": [3.35, 3.35, 3.35, 3.35],
            "temperatures": [26.5, 27.5],
        },
    }
    mock_coordinator.last_update_success = True

    hass.data[DOMAIN] = {
        entry.entry_id: {
            "coordinator": mock_coordinator,
        }
    }

    from custom_components.renogy_ble.sensor import (
        async_setup_entry as async_setup_sensors,
    )

    async_add_entities = MagicMock()
    await async_setup_sensors(hass, entry, async_add_entities)

    assert async_add_entities.called
    created_entities = async_add_entities.call_args[0][0]

    # Verify battery aggregate entities
    aggregates = [
        entity for entity in created_entities if "battery_aggregate" in entity.unique_id
    ]
    assert len(aggregates) == 7

    voltage_agg = next(e for e in aggregates if e.entity_description.key == "voltage")
    assert voltage_agg.native_value == 13.3  # (13.2 + 13.4) / 2
    assert voltage_agg.name == "Renogy Battery Aggregate Voltage"

    temp_agg = next(
        e for e in aggregates if e.entity_description.key == "battery_temperature"
    )
    assert temp_agg.native_value == 26.0  # (25.0 + 27.0) / 2

    current_agg = next(e for e in aggregates if e.entity_description.key == "current")
    assert current_agg.native_value == 25.0  # 10.0 + 15.0

    power_agg = next(e for e in aggregates if e.entity_description.key == "power")
    assert power_agg.native_value == 333.0  # 132.0 + 201.0

    soc_agg = next(e for e in aggregates if e.entity_description.key == "soc")
    assert soc_agg.native_value == 85.0  # (80 + 90) / (100 + 100) * 100

    # Verify cell-specific entities are created and have correct values
    cell_voltages = [
        e
        for e in created_entities
        if hasattr(e, "device_id")
        and e.device_id == 1
        and e.entity_description.key.startswith("cell_voltage_")
        and e.entity_description.key.split("_")[-1].isdigit()
    ]
    # 4 cells in battery 1
    assert len(cell_voltages) == 4
    cell_voltage_0 = next(
        e for e in cell_voltages if e.entity_description.key == "cell_voltage_0"
    )
    assert cell_voltage_0.native_value == 3.28
    assert cell_voltage_0.suggested_display_precision == 1
    assert (
        next(
            e for e in cell_voltages if e.entity_description.key == "cell_voltage_1"
        ).native_value
        == 3.32
    )

    # Check average cell voltage of battery 1
    avg_cell_volt_1 = next(
        e
        for e in created_entities
        if hasattr(e, "device_id")
        and e.device_id == 1
        and e.entity_description.key == "average_cell_voltage"
    )
    assert avg_cell_volt_1.native_value == 3.30  # (3.28 + 3.32 + 3.30 + 3.30) / 4

    # Check cell temperatures of battery 1
    cell_temps = [
        e
        for e in created_entities
        if hasattr(e, "device_id")
        and e.device_id == 1
        and e.entity_description.key.startswith("cell_temp_")
        and e.entity_description.key.split("_")[-1].isdigit()
    ]
    # 2 temps in battery 1
    assert len(cell_temps) == 2
    assert (
        next(
            e for e in cell_temps if e.entity_description.key == "cell_temp_0"
        ).native_value
        == 24.8
    )

    # Check average cell temperature of battery 1
    avg_cell_temp_1 = next(
        e
        for e in created_entities
        if hasattr(e, "device_id")
        and e.device_id == 1
        and e.entity_description.key == "average_cell_temperature"
    )
    assert avg_cell_temp_1.native_value == 25.0  # (24.8 + 25.2) / 2


@pytest.mark.asyncio
async def test_bms_status_sensor() -> None:
    """Test battery BMS status sensor setup and attributes."""
    hass = MagicMock()
    hass.data = {}

    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.data = {
        CONF_ADDRESS: "AA:BB:CC:DD:EE:FF",
        CONF_DEVICE_IDS: [1],
        CONF_SCAN_INTERVAL: 30,
    }

    mock_coordinator = MagicMock()
    mock_coordinator.address = "AA:BB:CC:DD:EE:FF"
    mock_coordinator.data = {
        1: {
            "device_type": "battery",
            "model": "Smart Lithium 1",
            "is_available": True,
            "heater_on": True,
            "fully_charged": False,
            "alarms": ["short_circuit"],
            "warnings": [],
        }
    }
    mock_coordinator.last_update_success = True

    hass.data[DOMAIN] = {
        entry.entry_id: {
            "coordinator": mock_coordinator,
        }
    }

    from custom_components.renogy_ble.sensor import (
        async_setup_entry as async_setup_sensors,
    )

    async_add_entities = MagicMock()
    await async_setup_sensors(hass, entry, async_add_entities)

    assert async_add_entities.called
    created_entities = async_add_entities.call_args[0][0]

    # Verify the bms_status sensor
    bms_sensor = next(
        entity
        for entity in created_entities
        if entity.entity_description.key == "bms_status"
    )
    assert bms_sensor.native_value == "Alarm"
    assert bms_sensor.available is True

    # Verify separate status/diagnostics sensors are skipped under sensor platform
    assert not any(
        entity.entity_description.key == "heater_on" for entity in created_entities
    )
    assert not any(
        entity.entity_description.key == "fully_charged" for entity in created_entities
    )


@pytest.mark.asyncio
async def test_binary_sensor_setup() -> None:
    """Test binary sensor platform setup and state updates."""
    hass = MagicMock()
    hass.data = {}

    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.data = {
        CONF_ADDRESS: "AA:BB:CC:DD:EE:FF",
        CONF_DEVICE_IDS: [1],
        CONF_SCAN_INTERVAL: 30,
    }

    mock_coordinator = MagicMock()
    mock_coordinator.address = "AA:BB:CC:DD:EE:FF"
    mock_coordinator.data = {
        1: {
            "device_type": "battery",
            "model": "Smart Lithium 1",
            "is_available": True,
            "heater_on": True,
            "fully_charged": False,
            "alarms": ["short_circuit"],
            "warnings": [],
        }
    }
    mock_coordinator.last_update_success = True

    hass.data[DOMAIN] = {
        entry.entry_id: {
            "coordinator": mock_coordinator,
        }
    }

    from custom_components.renogy_ble.binary_sensor import (
        async_setup_entry as async_setup_binary_sensors,
    )

    async_add_entities = MagicMock()
    await async_setup_binary_sensors(hass, entry, async_add_entities)

    assert async_add_entities.called
    created_entities = async_add_entities.call_args[0][0]

    # Verify heater binary sensor
    heater_sensor = next(
        entity
        for entity in created_entities
        if entity.entity_description.key == "heater_on"
    )
    assert heater_sensor.is_on is True
    assert heater_sensor.available is True

    # Verify fully charged binary sensor
    charged_sensor = next(
        entity
        for entity in created_entities
        if entity.entity_description.key == "fully_charged"
    )
    assert charged_sensor.is_on is False

    # Verify alarms active binary sensor
    alarms_sensor = next(
        entity
        for entity in created_entities
        if entity.entity_description.key == "alarms_active"
    )
    assert alarms_sensor.is_on is True
