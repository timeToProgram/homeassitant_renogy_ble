"""Support for Renogy BLE sensors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from homeassistant.components.bluetooth.passive_update_coordinator import (
    PassiveBluetoothCoordinatorEntity,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .ble import RenogyActiveBluetoothCoordinator
from .const import ATTR_MANUFACTURER, DOMAIN, LOGGER


@dataclass(frozen=True)
class RenogyBLESensorDescription(SensorEntityDescription):
    """Describes a Renogy BLE sensor."""

    value_fn: Optional[Callable[[Dict[str, Any]], Any]] = None
    suggested_display_precision: int | None = 1
    is_binary: bool = False


SENSOR_DESCRIPTIONS: Dict[str, List[RenogyBLESensorDescription]] = {
    "controller": [
        RenogyBLESensorDescription(
            key="battery_percentage",
            name="Battery State of Charge",
            native_unit_of_measurement=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="battery_voltage",
            name="Battery Voltage",
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="battery_current",
            name="Battery Charging Current",
            native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="battery_temperature",
            name="Battery Temperature",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="controller_temperature",
            name="Controller Temperature",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="load_voltage",
            name="Load Voltage",
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="load_current",
            name="Load Current",
            native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="load_power",
            name="Load Power",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="pv_voltage",
            name="PV Voltage",
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="pv_current",
            name="PV Current",
            native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="pv_power",
            name="PV Power",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="max_charging_power_today",
            name="Max Charging Power Today",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="max_discharging_power_today",
            name="Max Discharging Power Today",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="charging_amp_hours_today",
            name="Charging Current Today",
            native_unit_of_measurement="Ah",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="discharging_amp_hours_today",
            name="Discharging Current Today",
            native_unit_of_measurement="Ah",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="power_generation_today",
            name="Power Generation Today",
            native_unit_of_measurement="Wh",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="power_consumption_today",
            name="Power Consumption Today",
            native_unit_of_measurement="Wh",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="power_generation_total",
            name="Power Generation Total",
            native_unit_of_measurement="Wh",
            state_class=SensorStateClass.TOTAL_INCREASING,
        ),
        RenogyBLESensorDescription(
            key="charging_status",
            name="Charging Status",
        ),
        RenogyBLESensorDescription(
            key="battery_type",
            name="Battery Type",
        ),
        RenogyBLESensorDescription(
            key="fault_count",
            name="Fault Count",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="warning_count",
            name="Warning Count",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="daily_power_generation_history",
            name="Power Generation History",
            value_fn=lambda data: (
                ", ".join(str(x) for x in data.get("daily_power_generation", []))
                if data.get("daily_power_generation")
                else "None"
            ),
        ),
        RenogyBLESensorDescription(
            key="daily_charge_ah_history",
            name="Charge Ah History",
            value_fn=lambda data: (
                ", ".join(str(x) for x in data.get("daily_charge_ah", []))
                if data.get("daily_charge_ah")
                else "None"
            ),
        ),
        RenogyBLESensorDescription(
            key="daily_max_power_history",
            name="Max Power History",
            value_fn=lambda data: (
                ", ".join(str(x) for x in data.get("daily_max_power", []))
                if data.get("daily_max_power")
                else "None"
            ),
        ),
        RenogyBLESensorDescription(
            key="status",
            name="Status",
            value_fn=lambda data: (
                "Fault"
                if len(data.get("faults", [])) > 0
                else ("Warning" if len(data.get("warnings", [])) > 0 else "Normal")
            ),
        ),
        RenogyBLESensorDescription(
            key="load_status",
            name="DC Load Status",
            value_fn=lambda data: (
                data.get("load_status") == "on" or data.get("load_status") is True
            ),
            is_binary=True,
        ),
        RenogyBLESensorDescription(
            key="faults_active",
            name="Faults Present",
            value_fn=lambda data: len(data.get("faults", [])) > 0,
            is_binary=True,
        ),
        RenogyBLESensorDescription(
            key="warnings_active",
            name="Warnings Present",
            value_fn=lambda data: len(data.get("warnings", [])) > 0,
            is_binary=True,
        ),
        RenogyBLESensorDescription(
            key="controller_faults",
            name="Controller Faults",
            value_fn=lambda data: (
                ", ".join(data.get("faults", [])) if data.get("faults") else "None"
            ),
        ),
        RenogyBLESensorDescription(
            key="controller_warnings",
            name="Controller Warnings",
            value_fn=lambda data: (
                ", ".join(data.get("warnings", [])) if data.get("warnings") else "None"
            ),
        ),
    ],
    "battery": [
        RenogyBLESensorDescription(
            key="cell_count",
            name="Cell Count",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="battery_temperature",
            name="Battery Temperature",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="current",
            name="Battery Current",
            native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="voltage",
            name="Battery Voltage",
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="remaining_capacity",
            name="Remaining Capacity",
            native_unit_of_measurement="Ah",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="total_capacity",
            name="Total Capacity",
            native_unit_of_measurement="Ah",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="soc",
            name="State of Charge",
            native_unit_of_measurement=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="power",
            name="Battery Power",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="alarm_count",
            name="Alarm Count",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="warning_count",
            name="Warning Count",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="discharge_mosfet",
            name="Discharge MOSFET Status",
        ),
        RenogyBLESensorDescription(
            key="charge_mosfet",
            name="Charge MOSFET Status",
        ),
        # Cell voltages (up to 16)
        *[
            RenogyBLESensorDescription(
                key=f"cell_voltage_{i}",
                name=f"Cell {i + 1} Voltage",
                native_unit_of_measurement=UnitOfElectricPotential.VOLT,
                device_class=SensorDeviceClass.VOLTAGE,
                state_class=SensorStateClass.MEASUREMENT,
                value_fn=lambda data, idx=i: (
                    data.get("cell_voltages", [])[idx]
                    if "cell_voltages" in data and idx < len(data["cell_voltages"])
                    else None
                ),
            )
            for i in range(16)
        ],
        # Average cell voltage
        RenogyBLESensorDescription(
            key="average_cell_voltage",
            name="Average Cell Voltage",
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda data: (
                sum(data["cell_voltages"]) / len(data["cell_voltages"])
                if "cell_voltages" in data and data["cell_voltages"]
                else None
            ),
        ),
        # Cell temperatures (up to 8)
        *[
            RenogyBLESensorDescription(
                key=f"cell_temp_{i}",
                name=f"Cell {i + 1} Temperature",
                native_unit_of_measurement=UnitOfTemperature.CELSIUS,
                device_class=SensorDeviceClass.TEMPERATURE,
                state_class=SensorStateClass.MEASUREMENT,
                value_fn=lambda data, idx=i: (
                    data.get("temperatures", [])[idx]
                    if "temperatures" in data and idx < len(data["temperatures"])
                    else None
                ),
            )
            for i in range(8)
        ],
        # Average cell temperature
        RenogyBLESensorDescription(
            key="average_cell_temperature",
            name="Average Cell Temperature",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda data: (
                sum(data["temperatures"]) / len(data["temperatures"])
                if "temperatures" in data and data["temperatures"]
                else None
            ),
        ),
        RenogyBLESensorDescription(
            key="bms_status",
            name="BMS Status",
            value_fn=lambda data: (
                "Alarm"
                if len(data.get("alarms", [])) > 0
                else ("Warning" if len(data.get("warnings", [])) > 0 else "Normal")
            ),
        ),
        RenogyBLESensorDescription(
            key="heater_on",
            name="Heater Active",
            value_fn=lambda data: bool(data.get("heater_on")),
            is_binary=True,
        ),
        RenogyBLESensorDescription(
            key="fully_charged",
            name="Fully Charged",
            value_fn=lambda data: bool(data.get("fully_charged")),
            is_binary=True,
        ),
        RenogyBLESensorDescription(
            key="effective_charge",
            name="Charging Active",
            value_fn=lambda data: bool(data.get("effective_charge")),
            is_binary=True,
        ),
        RenogyBLESensorDescription(
            key="effective_discharge",
            name="Discharging Active",
            value_fn=lambda data: bool(data.get("effective_discharge")),
            is_binary=True,
        ),
        RenogyBLESensorDescription(
            key="charge_enabled",
            name="Charging Enabled",
            value_fn=lambda data: bool(data.get("charge_enabled")),
            is_binary=True,
        ),
        RenogyBLESensorDescription(
            key="discharge_enabled",
            name="Discharging Enabled",
            value_fn=lambda data: bool(data.get("discharge_enabled")),
            is_binary=True,
        ),
        RenogyBLESensorDescription(
            key="using_battery_power",
            name="Using Battery Power",
            value_fn=lambda data: bool(data.get("using_battery_power")),
            is_binary=True,
        ),
        RenogyBLESensorDescription(
            key="buzzer_on",
            name="BMS Buzzer Active",
            value_fn=lambda data: bool(data.get("buzzer_on")),
            is_binary=True,
        ),
        RenogyBLESensorDescription(
            key="charge_immediately",
            name="Charge Immediately Request",
            value_fn=lambda data: bool(data.get("charge_immediately")),
            is_binary=True,
        ),
        RenogyBLESensorDescription(
            key="full_charge_request",
            name="Full Charge Request",
            value_fn=lambda data: bool(data.get("full_charge_request")),
            is_binary=True,
        ),
        RenogyBLESensorDescription(
            key="alarms_active",
            name="Alarms Present",
            value_fn=lambda data: len(data.get("alarms", [])) > 0,
            is_binary=True,
        ),
        RenogyBLESensorDescription(
            key="warnings_active",
            name="Warnings Present",
            value_fn=lambda data: len(data.get("warnings", [])) > 0,
            is_binary=True,
        ),
        RenogyBLESensorDescription(
            key="cell_voltage_alarms",
            name="Cell Voltage Alarms",
            value_fn=lambda data: (
                ", ".join(data.get("cell_voltage_alarms", []))
                if data.get("cell_voltage_alarms")
                else "None"
            ),
        ),
        RenogyBLESensorDescription(
            key="cell_temperature_alarms",
            name="Cell Temperature Alarms",
            value_fn=lambda data: (
                ", ".join(data.get("cell_temperature_alarms", []))
                if data.get("cell_temperature_alarms")
                else "None"
            ),
        ),
        RenogyBLESensorDescription(
            key="protection_alarms",
            name="Protection Alarms",
            value_fn=lambda data: (
                ", ".join(data.get("protection_alarms", []))
                if data.get("protection_alarms")
                else "None"
            ),
        ),
        RenogyBLESensorDescription(
            key="warnings",
            name="BMS Warnings",
            value_fn=lambda data: (
                ", ".join(data.get("warnings", [])) if data.get("warnings") else "None"
            ),
        ),
    ],
    "inverter": [
        RenogyBLESensorDescription(
            key="input_voltage",
            name="AC Input Voltage",
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="input_current",
            name="AC Input Current",
            native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="output_voltage",
            name="AC Output Voltage",
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="output_current",
            name="AC Output Current",
            native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="output_frequency",
            name="AC Output Frequency",
            native_unit_of_measurement="Hz",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="battery_voltage",
            name="Battery Voltage",
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="temperature",
            name="Inverter Temperature",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="fault_count",
            name="Fault Count",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="input_frequency",
            name="AC Input Frequency",
            native_unit_of_measurement="Hz",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="input_power",
            name="AC Input Power",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="output_power",
            name="AC Output Power",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="battery_charge_ah_today",
            name="Battery Charge Today",
            native_unit_of_measurement="Ah",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="battery_discharge_ah_today",
            name="Battery Discharge Today",
            native_unit_of_measurement="Ah",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="pv_generation_today",
            name="PV Generation Today",
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="load_consumption_today",
            name="Load Consumption Today",
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="battery_charge_ah_total",
            name="Battery Charge Total",
            native_unit_of_measurement="Ah",
            state_class=SensorStateClass.TOTAL_INCREASING,
        ),
        RenogyBLESensorDescription(
            key="battery_discharge_ah_total",
            name="Battery Discharge Total",
            native_unit_of_measurement="Ah",
            state_class=SensorStateClass.TOTAL_INCREASING,
        ),
        RenogyBLESensorDescription(
            key="pv_generation_total",
            name="PV Generation Total",
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
        ),
        RenogyBLESensorDescription(
            key="load_consumption_total",
            name="Load Consumption Total",
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
        ),
        RenogyBLESensorDescription(
            key="battery_soc",
            name="Battery State of Charge",
            native_unit_of_measurement=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="charge_current",
            name="Inverter Charge Current",
            native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="machine_state",
            name="Inverter Operation State",
        ),
        RenogyBLESensorDescription(
            key="bus_voltage",
            name="Bus Voltage",
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="load_current",
            name="Inverter AC Load Current",
            native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="load_active_power",
            name="Inverter AC Load Active Power",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="load_apparent_power",
            name="Inverter AC Load Apparent Power",
            native_unit_of_measurement="VA",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="load_percentage",
            name="Inverter AC Load Percentage",
            native_unit_of_measurement=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="output_priority",
            name="Inverter AC Output Priority Setting",
        ),
        RenogyBLESensorDescription(
            key="output_frequency_setting",
            name="AC Output Frequency Setting",
            native_unit_of_measurement="Hz",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        RenogyBLESensorDescription(
            key="ac_voltage_range",
            name="AC Voltage Range Setting",
        ),
        RenogyBLESensorDescription(
            key="status",
            name="Status",
            value_fn=lambda data: (
                "Fault" if len(data.get("faults", [])) > 0 else "Normal"
            ),
        ),
        RenogyBLESensorDescription(
            key="eco_mode",
            name="ECO Mode",
            value_fn=lambda data: bool(data.get("eco_mode")),
            is_binary=True,
        ),
        RenogyBLESensorDescription(
            key="ups_line_interactive",
            name="UPS Line Interactive Status",
            value_fn=lambda data: bool(data.get("ups_line_interactive")),
            is_binary=True,
        ),
        RenogyBLESensorDescription(
            key="test_in_progress",
            name="Self Test In Progress",
            value_fn=lambda data: bool(data.get("test_in_progress")),
            is_binary=True,
        ),
        RenogyBLESensorDescription(
            key="beeper_on",
            name="Beeper Active",
            value_fn=lambda data: bool(data.get("beeper_on")),
            is_binary=True,
        ),
        RenogyBLESensorDescription(
            key="power_saving_mode",
            name="Power Saving Mode",
            value_fn=lambda data: bool(data.get("power_saving_mode")),
            is_binary=True,
        ),
        RenogyBLESensorDescription(
            key="faults_active",
            name="Faults Present",
            value_fn=lambda data: len(data.get("faults", [])) > 0,
            is_binary=True,
        ),
        RenogyBLESensorDescription(
            key="inverter_faults",
            name="Inverter Faults",
            value_fn=lambda data: (
                ", ".join(data.get("faults", [])) if data.get("faults") else "None"
            ),
        ),
    ],
}


@dataclass(frozen=True)
class RenogyBatteryAggregateSensorDescription(SensorEntityDescription):
    """Describes an aggregate battery sensor."""

    value_fn: Optional[Callable[[List[Dict[str, Any]]], Any]] = None
    suggested_display_precision: int | None = 1


BATTERY_AGGREGATE_DESCRIPTIONS = [
    RenogyBatteryAggregateSensorDescription(
        key="voltage",
        name="Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda battery_datas: (
            sum(data.get("voltage", 0.0) for data in battery_datas) / len(battery_datas)
            if battery_datas
            else 0.0
        ),
    ),
    RenogyBatteryAggregateSensorDescription(
        key="battery_temperature",
        name="Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda battery_datas: (
            sum(data.get("battery_temperature", 0.0) for data in battery_datas)
            / len(battery_datas)
            if battery_datas
            else 0.0
        ),
    ),
    RenogyBatteryAggregateSensorDescription(
        key="total_capacity",
        name="Total Capacity",
        native_unit_of_measurement="Ah",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda battery_datas: (
            sum(data.get("total_capacity", 0.0) for data in battery_datas)
            if battery_datas
            else 0.0
        ),
    ),
    RenogyBatteryAggregateSensorDescription(
        key="remaining_capacity",
        name="Remaining Capacity",
        native_unit_of_measurement="Ah",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda battery_datas: (
            sum(data.get("remaining_capacity", 0.0) for data in battery_datas)
            if battery_datas
            else 0.0
        ),
    ),
    RenogyBatteryAggregateSensorDescription(
        key="current",
        name="Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda battery_datas: (
            sum(data.get("current", 0.0) for data in battery_datas)
            if battery_datas
            else 0.0
        ),
    ),
    RenogyBatteryAggregateSensorDescription(
        key="power",
        name="Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda battery_datas: (
            sum(data.get("power", 0.0) for data in battery_datas)
            if battery_datas
            else 0.0
        ),
    ),
    RenogyBatteryAggregateSensorDescription(
        key="soc",
        name="State of Charge",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda battery_datas: (
            (
                sum(data.get("remaining_capacity", 0.0) for data in battery_datas)
                / sum(data.get("total_capacity", 0.001) for data in battery_datas)
            )
            * 100
            if battery_datas
            else 0.0
        ),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Renogy BLE sensors."""
    renogy_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = renogy_data["coordinator"]

    if not coordinator.data:
        LOGGER.info("Waiting for first refresh to detect devices and entities...")
        await coordinator.async_config_entry_first_refresh()

    if not coordinator.data:
        LOGGER.warning("No Renogy devices detected during initial refresh")
        return

    entities: List[SensorEntity] = []
    battery_ids = []

    for device_id, device_data in coordinator.data.items():
        device_type = device_data["device_type"]
        if device_type == "battery":
            battery_ids.append(device_id)

        descriptions = SENSOR_DESCRIPTIONS.get(device_type, [])
        for desc in descriptions:
            if desc.is_binary:
                continue
            # Only add cell sensors if battery has those cells/temperatures
            if (
                desc.key.startswith("cell_voltage_")
                and desc.key.split("_")[-1].isdigit()
            ):
                idx = int(desc.key.split("_")[-1])
                if len(device_data.get("cell_voltages", [])) <= idx:
                    continue
            elif (
                desc.key.startswith("cell_temp_") and desc.key.split("_")[-1].isdigit()
            ):
                idx = int(desc.key.split("_")[-1])
                if len(device_data.get("temperatures", [])) <= idx:
                    continue
            elif desc.key == "average_cell_voltage":
                if not device_data.get("cell_voltages"):
                    continue
            elif desc.key == "average_cell_temperature":
                if not device_data.get("temperatures"):
                    continue

            entities.append(RenogyBLESensor(coordinator, device_id, desc))

    if len(battery_ids) > 1:
        LOGGER.info(
            "Found multiple batteries (%s); adding aggregate entities.",
            battery_ids,
        )
        for desc in BATTERY_AGGREGATE_DESCRIPTIONS:
            entities.append(
                RenogyBatteryAggregateSensor(coordinator, battery_ids, desc)
            )

    async_add_entities(entities)


class RenogyBLESensor(PassiveBluetoothCoordinatorEntity, SensorEntity):
    """Representation of a Renogy BLE sensor."""

    entity_description: RenogyBLESensorDescription
    coordinator: RenogyActiveBluetoothCoordinator

    def __init__(
        self,
        coordinator: RenogyActiveBluetoothCoordinator,
        device_id: int,
        description: RenogyBLESensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.device_id = device_id
        self.entity_description = description

        address = coordinator.address
        self._attr_unique_id = f"{address}_{device_id}_{description.key}"

        device_data = coordinator.data.get(device_id, {})
        device_type = device_data.get("device_type", "unknown")
        model = device_data.get("model", device_type.capitalize())

        self._attr_name = (
            f"Renogy {device_type.capitalize()} {device_id} {description.name}"
        )

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{address}_{device_id}")},
            name=f"Renogy {device_type.capitalize()} {device_id}",
            manufacturer=ATTR_MANUFACTURER,
            model=model,
            hw_version=f"BLE Address: {address}, ID: {device_id}",
            sw_version=device_type.capitalize(),
        )
        self._attr_suggested_display_precision = description.suggested_display_precision

    @property
    def suggested_display_precision(self) -> int | None:
        """Return the suggested display precision."""
        val = self.native_value
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            return self.entity_description.suggested_display_precision
        return None

    @property
    def native_value(self) -> Any:
        """Return the sensor's value."""
        device_data = self.coordinator.data.get(self.device_id)
        if not device_data:
            return None

        if self.entity_description.value_fn:
            return self.entity_description.value_fn(device_data)

        return device_data.get(self.entity_description.key)

    @property
    def available(self) -> bool:
        """Return if the sensor is available."""
        if not self.coordinator.last_update_success:
            return False

        device_data = self.coordinator.data.get(self.device_id)
        return device_data is not None and device_data.get("is_available", False)


class RenogyBatteryAggregateSensor(PassiveBluetoothCoordinatorEntity, SensorEntity):
    """Representation of an aggregate battery sensor."""

    entity_description: RenogyBatteryAggregateSensorDescription
    coordinator: RenogyActiveBluetoothCoordinator

    def __init__(
        self,
        coordinator: RenogyActiveBluetoothCoordinator,
        battery_ids: List[int],
        description: RenogyBatteryAggregateSensorDescription,
    ) -> None:
        """Initialize the aggregate sensor."""
        super().__init__(coordinator)
        self.battery_ids = battery_ids
        self.entity_description = description

        address = coordinator.address
        self._attr_unique_id = f"{address}_battery_aggregate_{description.key}"
        self._attr_name = f"Renogy Battery Aggregate {description.name}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{address}_battery_aggregate")},
            name="Renogy Battery Aggregate",
            manufacturer=ATTR_MANUFACTURER,
            model="Battery Aggregate",
            hw_version=f"Aggregate of {len(battery_ids)} batteries",
            sw_version="Aggregate",
        )
        self._attr_suggested_display_precision = description.suggested_display_precision

    @property
    def native_value(self) -> Any:
        """Return the aggregate sensor's value."""
        battery_datas = []
        for dev_id in self.battery_ids:
            if self.coordinator.data and dev_id in self.coordinator.data:
                battery_datas.append(self.coordinator.data[dev_id])

        if not battery_datas:
            return None

        if self.entity_description.value_fn:
            return self.entity_description.value_fn(battery_datas)

        return None

    @property
    def available(self) -> bool:
        """Return if the sensor is available."""
        if not self.coordinator.last_update_success:
            return False

        # Available if at least one underlying battery is available
        for dev_id in self.battery_ids:
            if self.coordinator.data and dev_id in self.coordinator.data:
                if self.coordinator.data[dev_id].get("is_available", False):
                    return True
        return False
