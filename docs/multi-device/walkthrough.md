# Walkthrough: Multi-Device Renogy BLE Integration

We have successfully redesigned and re-implemented the Renogy BLE Home Assistant integration. The integration now supports multiple Renogy devices (charge controllers, batteries, and inverters) communicating dynamically over a single shared Bluetooth BLE connection, using the optimized logic from `Anto79-ops/renogy-ble`.

## Changes Made

### 1. Bluetooth & Modbus Core
- **`utils.py`**: Created helper utilities for Modbus RTU frame creation and CRC validation, ASCII conversions, signed/unsigned int conversions, and MAC address formatting. Implemented type overloads to ensure robust type checking.
- **`parsers.py`**: Integrated parser logic for charge controllers, batteries, and inverters from the `Anto79-ops/renogy-ble` library, parsing Modbus register responses dynamically.
- **`ble.py`**: Re-implemented the Bluetooth update coordinator using `ActiveBluetoothDataUpdateCoordinator`. It manages a persistent BLE connection with the Bluetooth device, and polls all configured device IDs in sequence. Implemented `async_probe_device_types` to query connected devices during integration setup.

### 2. Home Assistant Integration Structure
- **`const.py`**: Updated constants, including adding `CONF_DEVICE_IDS` and removing deprecated config parameters.
- **`config_flow.py`**: Rebuilt the flow to support comma-separated device IDs inputs from the user during integration configuration, as well as optional manual connection details.
- **`__init__.py`**: Configures the coordinator with the selected device IDs list and forwards setups to platforms. Supports clean shutdown and stopping of connections.
- **`sensor.py`**: Dynamically creates sensor entities based on the probed device types and configured device IDs.
- **`switch.py`**: Exposes load switch entities for controllers, sending the corresponding Modbus writes to toggle load status.
- **`manifest.json`**: Upgraded requirements to use bleak-retry-connector.

### 3. Cleanup
- Removed unused and obsolete platforms: `number.py` and `select.py`.

## Verification & Testing

All verification steps described in the project guidelines have been run and passed successfully.

### 1. Formatting and Quality Checks
- Formatted the codebase: `uv run ruff format .`
- Lint checked the codebase: `uv run ruff check custom_components`
- Type checked the codebase: `uv run ty check custom_components`

### 2. Unit Tests
All unit tests have been written/updated to match the new architecture, covering utilities, parsing logic, config flow user inputs, platform setup, and entity state updates.
- Test runner output:
```bash
$ uv run pytest tests
======================== 25 passed in 1.12s =========================
```
