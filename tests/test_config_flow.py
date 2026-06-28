"""Tests for the Renogy BLE config flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import CONF_ADDRESS

from custom_components.renogy.config_flow import RenogyConfigFlow
from custom_components.renogy.const import (
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
        "custom_components.renogy.ble.RenogyActiveBluetoothCoordinator",
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
        "custom_components.renogy.ble.RenogyActiveBluetoothCoordinator",
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
        "custom_components.renogy.ble.RenogyActiveBluetoothCoordinator",
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
