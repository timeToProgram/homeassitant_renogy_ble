# Implementation Plan - Multi-Device Renogy BLE Home Assistant Integration

This plan updates the Renogy BLE integration to support multiple devices sharing a single Bluetooth connection (e.g. via a Communication Hub) and replaces the old parser/client code with the improved implementation from `Anto79-ops/renogy-ble`. All MQTT-related code is omitted.

## User Review Required

> [!IMPORTANT]
> The integration configuration (Config Flow) will now include a new field for **Device IDs** (comma-separated list of Modbus slave IDs, e.g. `255` for a single direct connection, or `48,32` for a battery and inverter on a communication hub).
> 
> The integration will auto-detect the type of each device ID (`controller`, `battery`, `inverter`) during setup/polling by reading device registers.

## Proposed Changes

### Configuration & Config Flow

Modify the config flow and constants to accept a comma-separated list of device IDs instead of a single device type.

#### [MODIFY] [const.py](file:///home/karan/Documents/github/homeassitant_renogy_ble/custom_components/renogy/const.py)
* Add `CONF_DEVICE_IDS` constant.
* Keep definitions for `DeviceType` (`controller`, `battery`, `inverter`).
* Remove options for connection modes (`sustained`/`intermittent`) that are not applicable to the persistent connection manager of `renogy-ble`.

#### [MODIFY] [config_flow.py](file:///home/karan/Documents/github/homeassitant_renogy_ble/custom_components/renogy/config_flow.py)
* Update schemas to include `CONF_DEVICE_IDS` (defaulting to `"255"`).
* Remove the standalone device type picker since it is now auto-detected per device ID.

### Core BLE Communication & Parsing

Integrate `parsers.py`, `utils.py`, and `ble_client.py` from `renogy-ble` directly inside the custom component.

#### [NEW] [utils.py](file:///home/karan/Documents/github/homeassitant_renogy_ble/custom_components/renogy/utils.py)
* Modbus CRC16 calculations.
* Modbus request frame builders.
* Safe byte-to-integer, byte-to-ascii, and sign-handling temperature parsers.
* Modbus response validation.

#### [NEW] [parsers.py](file:///home/karan/Documents/github/homeassitant_renogy_ble/custom_components/renogy/parsers.py)
* Register definition maps for `controller`, `battery`, and `inverter`.
* Parsing functions for controller (charging info, device info, battery type, faults, historical).
* Parsing functions for battery (cell info, temperature info, battery main info, alarm info, device info).
* Parsing functions for inverter (main status, device info, PV info, settings status, settings, statistics).

#### [MODIFY] [ble.py](file:///home/karan/Documents/github/homeassitant_renogy_ble/custom_components/renogy/ble.py)
* Re-implement the persistent active coordinator using `BleakClient` and the persistent connection manager class from `renogy-ble`.
* Integrate automatic device type detection: for each configured device ID, probe registers to identify whether it is a controller, battery, or inverter.
* Periodically poll all configured device IDs on the single BLE connection.
* Store data in a dictionary keyed by device ID.

### Home Assistant Platforms & Entities

Map all the parsed attributes from the new parsers to Home Assistant sensor, binary sensor, switch, or button entities, separated by device.

#### [MODIFY] [__init__.py](file:///home/karan/Documents/github/homeassitant_renogy_ble/custom_components/renogy/__init__.py)
* Set up the coordinator with the list of configured device IDs.
* Initialize and register multiple devices (one for each configured device ID) in the Home Assistant Device Registry.

#### [MODIFY] [sensor.py](file:///home/karan/Documents/github/homeassitant_renogy_ble/custom_components/renogy/sensor.py)
* Read the comprehensive metrics returned by the new parsers.
* Generate sensor entities dynamically for each active device ID and its detected type.
* Update sensor value mappings to use the new parsed dict structure.

## Verification Plan

### Automated Tests
* We will verify the syntax and execution of the python files using local tests.
* Ensure all code compiles cleanly and matches Home Assistant integration standards.

### Manual Verification
* The user will install the integration in Home Assistant and configure it via the config flow, specifying multiple device IDs (e.g. `48,32`).
* Verify that multiple devices are successfully created in the Home Assistant Device Registry, each with their own set of sensors.
