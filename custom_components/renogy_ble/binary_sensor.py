"""Support for Renogy BLE binary sensors."""

from __future__ import annotations

import logging
from typing import List

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
)
from homeassistant.components.bluetooth.passive_update_coordinator import (
    PassiveBluetoothCoordinatorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .ble import RenogyActiveBluetoothCoordinator
from .const import ATTR_MANUFACTURER, DOMAIN
from .sensor import SENSOR_DESCRIPTIONS, RenogyBLESensorDescription

LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Renogy BLE binary sensors."""
    renogy_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = renogy_data["coordinator"]

    if not coordinator.data:
        return

    entities: List[BinarySensorEntity] = []

    for device_id, device_data in coordinator.data.items():
        device_type = device_data["device_type"]
        descriptions = SENSOR_DESCRIPTIONS.get(device_type, [])
        for desc in descriptions:
            if desc.is_binary:
                entities.append(RenogyBLEBinarySensor(coordinator, device_id, desc))

    async_add_entities(entities)


class RenogyBLEBinarySensor(PassiveBluetoothCoordinatorEntity, BinarySensorEntity):
    """Representation of a Renogy BLE binary sensor."""

    entity_description: RenogyBLESensorDescription
    coordinator: RenogyActiveBluetoothCoordinator

    def __init__(
        self,
        coordinator: RenogyActiveBluetoothCoordinator,
        device_id: int,
        description: RenogyBLESensorDescription,
    ) -> None:
        """Initialize the binary sensor."""
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
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        device_data = self.coordinator.data.get(self.device_id)
        if not device_data:
            return None

        if self.entity_description.value_fn:
            return bool(self.entity_description.value_fn(device_data))

        return bool(device_data.get(self.entity_description.key))

    @property
    def available(self) -> bool:
        """Return if the binary sensor is available."""
        if not self.coordinator.last_update_success:
            return False

        device_data = self.coordinator.data.get(self.device_id)
        return device_data is not None and device_data.get("is_available", False)
