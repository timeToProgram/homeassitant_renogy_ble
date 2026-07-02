"""Tests for the Renogy BLE config flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
)
from homeassistant.const import CONF_ADDRESS

from custom_components.renogy_ble.config_flow import RenogyConfigFlow
from custom_components.renogy_ble.const import (
    CONF_DEVICE_IDS,
    CONF_SCAN_INTERVAL,
)


@pytest.mark.asyncio
async def test_flow_manual_setup_success() -> None:
    """Test manual setup flow with valid inputs."""
    flow = RenogyConfigFlow()
    flow.hass = MagicMock()
    flow.hass.config_entries.async_entry_for_domain_unique_id = MagicMock(
        return_value=None
    )
    flow.context = {}

    # Submit manual step
    mock_coordinator = MagicMock()
    mock_coordinator.async_probe_device_types = AsyncMock(
        return_value={1: "controller"}
    )
    mock_coordinator.async_shutdown = AsyncMock()

    with patch(
        "custom_components.renogy_ble.ble.RenogyActiveBluetoothCoordinator",
        return_value=mock_coordinator,
    ):
        result = await flow.async_step_manual_device(
            user_input={
                CONF_ADDRESS: "AA:BB:CC:DD:EE:FF",
                CONF_DEVICE_IDS: "1,2",
                CONF_SCAN_INTERVAL: 30,
            }
        )

    assert result["type"] == "create_entry"
    assert result["title"] == "Renogy BLE (AA:BB:CC:DD:EE:FF)"
    assert result["data"] == {
        CONF_ADDRESS: "AA:BB:CC:DD:EE:FF",
        CONF_DEVICE_IDS: [1, 2],
        CONF_SCAN_INTERVAL: 30,
    }


@pytest.mark.asyncio
async def test_flow_manual_setup_connection_failure() -> None:
    """Test manual setup flow when coordinator connection fails."""
    flow = RenogyConfigFlow()
    flow.hass = MagicMock()
    flow.hass.config_entries.async_entry_for_domain_unique_id = MagicMock(
        return_value=None
    )
    flow.context = {}

    # Mock coordinator throwing exception
    mock_coordinator = MagicMock()
    mock_coordinator.async_probe_device_types = AsyncMock(
        side_effect=Exception("Connection failed")
    )
    mock_coordinator.async_shutdown = AsyncMock()

    with patch(
        "custom_components.renogy_ble.ble.RenogyActiveBluetoothCoordinator",
        return_value=mock_coordinator,
    ):
        result = await flow.async_step_manual_device(
            user_input={
                CONF_ADDRESS: "AA:BB:CC:DD:EE:FF",
                CONF_DEVICE_IDS: "1",
                CONF_SCAN_INTERVAL: 30,
            }
        )

    assert result["type"] == "form"
    assert result["step_id"] == "manual_device"
    assert result["errors"] == {"base": "cannot_connect"}


@pytest.mark.asyncio
async def test_flow_manual_setup_no_devices() -> None:
    """Test manual setup flow when no devices are found during probe."""
    flow = RenogyConfigFlow()
    flow.hass = MagicMock()
    flow.hass.config_entries.async_entry_for_domain_unique_id = MagicMock(
        return_value=None
    )
    flow.context = {}

    # Mock coordinator returning empty device types
    mock_coordinator = MagicMock()
    mock_coordinator.async_probe_device_types = AsyncMock(return_value={})
    mock_coordinator.async_shutdown = AsyncMock()

    with patch(
        "custom_components.renogy_ble.ble.RenogyActiveBluetoothCoordinator",
        return_value=mock_coordinator,
    ):
        result = await flow.async_step_manual_device(
            user_input={
                CONF_ADDRESS: "AA:BB:CC:DD:EE:FF",
                CONF_DEVICE_IDS: "1",
                CONF_SCAN_INTERVAL: 30,
            }
        )

    assert result["type"] == "form"
    assert result["step_id"] == "manual_device"
    assert result["errors"] == {"base": "no_devices_found"}


@pytest.mark.asyncio
async def test_flow_user_discovery_presentation() -> None:
    """Test user step presentation with a discovered device."""
    flow = RenogyConfigFlow()
    flow.hass = MagicMock()
    flow.hass.config_entries.async_entry_for_domain_unique_id = MagicMock(
        return_value=None
    )
    flow.context = {}

    # Mock discovered device (looks like a Rover controller by name)
    discovery_info = MagicMock(spec=BluetoothServiceInfoBleak)
    discovery_info.name = "BT-TH-Rover40"
    discovery_info.address = "AA:BB:CC:DD:EE:FF"
    discovery_info.advertisement = MagicMock()
    discovery_info.advertisement.manufacturer_data = {}

    flow._discovered_device = discovery_info

    result = await flow.async_step_user()
    assert result["type"] == "form"
    assert result["step_id"] == "user"

    # Check the schema defaults
    schema = result["data_schema"]
    assert schema is not None
    keys_by_name = {
        key.schema if hasattr(key, "schema") else key: key for key in schema.schema
    }

    # Handle potentially callable default_factory
    controller_default = keys_by_name["controller"].default
    if callable(controller_default):
        controller_default = controller_default()
    battery_default = keys_by_name["battery"].default
    if callable(battery_default):
        battery_default = battery_default()
    controller_ids_default = keys_by_name["controller_ids"].default
    if callable(controller_ids_default):
        controller_ids_default = controller_ids_default()

    assert controller_default is True
    assert battery_default is False
    assert controller_ids_default == "255"


@pytest.mark.asyncio
async def test_flow_user_success() -> None:
    """Test user step success with multiple devices selected."""
    flow = RenogyConfigFlow()
    flow.hass = MagicMock()
    flow.hass.config_entries.async_entry_for_domain_unique_id = MagicMock(
        return_value=None
    )
    flow.context = {}

    discovery_info = MagicMock(spec=BluetoothServiceInfoBleak)
    discovery_info.name = "BT-TH-Rover40"
    discovery_info.address = "AA:BB:CC:DD:EE:FF"
    discovery_info.advertisement = MagicMock()
    discovery_info.advertisement.manufacturer_data = {}

    flow._discovered_device = discovery_info

    result = await flow.async_step_user(
        user_input={
            "controller": True,
            "controller_ids": "255",
            "battery": True,
            "battery_ids": "1, 2",
            "inverter": False,
            "inverter_ids": "255",
            "dcc": False,
            "dcc_ids": "255",
            "shunt300": False,
            "shunt300_ids": "255",
            CONF_SCAN_INTERVAL: 30,
        }
    )

    assert result["type"] == "create_entry"
    assert result["title"] == "BT-TH-Rover40"
    assert result["data"] == {
        CONF_ADDRESS: "AA:BB:CC:DD:EE:FF",
        CONF_DEVICE_IDS: [255, 1, 2],
        CONF_SCAN_INTERVAL: 30,
    }


@pytest.mark.asyncio
async def test_flow_user_no_device_selected() -> None:
    """Test user step validation failure when no device is checked."""
    flow = RenogyConfigFlow()
    flow.hass = MagicMock()
    flow.hass.config_entries.async_entry_for_domain_unique_id = MagicMock(
        return_value=None
    )
    flow.context = {}

    discovery_info = MagicMock(spec=BluetoothServiceInfoBleak)
    discovery_info.name = "BT-TH-Rover40"
    discovery_info.address = "AA:BB:CC:DD:EE:FF"
    discovery_info.advertisement = MagicMock()
    discovery_info.advertisement.manufacturer_data = {}

    flow._discovered_device = discovery_info

    result = await flow.async_step_user(
        user_input={
            "controller": False,
            "battery": False,
            CONF_SCAN_INTERVAL: 30,
        }
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "no_device_selected"}


@pytest.mark.asyncio
async def test_flow_user_manual_scan_success() -> None:
    """Test manual scan flow in user step."""
    flow = RenogyConfigFlow()
    flow.hass = MagicMock()
    flow.hass.config_entries.async_entry_for_domain_unique_id = MagicMock(
        return_value=None
    )
    flow.context = {}

    discovery_info = MagicMock(spec=BluetoothServiceInfoBleak)
    discovery_info.name = "BT-TH-Rover40"
    discovery_info.address = "AA:BB:CC:DD:EE:FF"
    discovery_info.advertisement = MagicMock()
    discovery_info.advertisement.manufacturer_data = {}

    # Mock discover devices returning our device
    with patch.object(flow, "_async_discover_devices") as mock_discover:

        async def mock_discover_impl():
            flow._discovered_devices = {"AA:BB:CC:DD:EE:FF": discovery_info}

        mock_discover.side_effect = mock_discover_impl

        result = await flow.async_step_user()
        assert result["type"] == "form"
        assert result["step_id"] == "user"

        # Submit form selecting the device and configuring it
        result = await flow.async_step_user(
            user_input={
                CONF_ADDRESS: "AA:BB:CC:DD:EE:FF",
                "controller": True,
                "controller_ids": "255",
                "battery": False,
                CONF_SCAN_INTERVAL: 30,
            }
        )

    assert result["type"] == "create_entry"
    assert result["title"] == "BT-TH-Rover40"
    assert result["data"] == {
        CONF_ADDRESS: "AA:BB:CC:DD:EE:FF",
        CONF_DEVICE_IDS: [255],
        CONF_SCAN_INTERVAL: 30,
    }
