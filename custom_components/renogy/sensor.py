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
            key="load_status",
            name="DC Load Status",
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
    ],
}


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

    entities = []
    for device_id, device_data in coordinator.data.items():
        device_type = device_data["device_type"]
        descriptions = SENSOR_DESCRIPTIONS.get(device_type, [])
        for desc in descriptions:
            entities.append(RenogyBLESensor(coordinator, device_id, desc))

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
