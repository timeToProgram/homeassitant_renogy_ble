"""Support for Renogy BLE switches."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.bluetooth.passive_update_coordinator import (
    PassiveBluetoothCoordinatorEntity,
)
from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .ble import RenogyActiveBluetoothCoordinator
from .const import ATTR_MANUFACTURER, DOMAIN

KEY_LOAD_STATUS = "load_status"


@dataclass(frozen=True)
class RenogyBLESwitchDescription(SwitchEntityDescription):
    """Describes a Renogy BLE switch."""


LOAD_SWITCH = RenogyBLESwitchDescription(
    key=KEY_LOAD_STATUS,
    name="DC Load",
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Renogy BLE switches."""
    renogy_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = renogy_data["coordinator"]

    if not coordinator.data:
        await coordinator.async_config_entry_first_refresh()

    entities = []
    for device_id, device_data in coordinator.data.items():
        if device_data.get("device_type") == "controller":
            entities.append(RenogyLoadSwitch(coordinator, device_id))

    async_add_entities(entities)


class RenogyLoadSwitch(PassiveBluetoothCoordinatorEntity, SwitchEntity):
    """Representation of a Renogy DC load switch."""

    entity_description: RenogyBLESwitchDescription
    coordinator: RenogyActiveBluetoothCoordinator

    def __init__(
        self,
        coordinator: RenogyActiveBluetoothCoordinator,
        device_id: int,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self.device_id = device_id
        self.entity_description = LOAD_SWITCH

        address = coordinator.address
        self._attr_unique_id = f"{address}_{device_id}_{LOAD_SWITCH.key}"

        device_data = coordinator.data.get(device_id, {})
        model = device_data.get("model", "Controller")

        self._attr_name = f"Renogy Controller {device_id} {LOAD_SWITCH.name}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{address}_{device_id}")},
            name=f"Renogy Controller {device_id}",
            manufacturer=ATTR_MANUFACTURER,
            model=model,
            hw_version=f"BLE Address: {address}, ID: {device_id}",
            sw_version="Controller",
        )

    @property
    def available(self) -> bool:
        """Return if the switch is available."""
        if not self.coordinator.last_update_success:
            return False

        device_data = self.coordinator.data.get(self.device_id)
        return device_data is not None and device_data.get("is_available", False)

    @property
    def is_on(self) -> bool | None:
        """Return True if the load is on."""
        device_data = self.coordinator.data.get(self.device_id)
        if not device_data:
            return None
        value = device_data.get("load_status")
        if isinstance(value, str):
            return value.lower() == "on"
        return bool(value)

    async def async_turn_on(self, **_kwargs: Any) -> None:
        """Turn the load on."""
        await self._async_set_state(True)

    async def async_turn_off(self, **_kwargs: Any) -> None:
        """Turn the load off."""
        await self._async_set_state(False)

    async def _async_set_state(self, state: bool) -> None:
        """Set load state and refresh entity state."""
        # 0x010A is the load control register (LOAD_CONTROL_REGISTER)
        success = await self.coordinator.async_write_register(
            self.device_id, 0x010A, 1 if state else 0
        )
        if success:
            # Optimistically update the state in coordinator data
            device_data = self.coordinator.data.get(self.device_id)
            if device_data:
                device_data["load_status"] = "on" if state else "off"
            self.async_write_ha_state()
