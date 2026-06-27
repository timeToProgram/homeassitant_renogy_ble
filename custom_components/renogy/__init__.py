"""Renogy BLE integration for Home Assistant."""

from __future__ import annotations

import asyncio
from typing import Protocol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import async_get as async_get_device_registry

from .ble import RenogyActiveBluetoothCoordinator
from .const import (
    CONF_DEVICE_IDS,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER,
)

# List of platforms this integration supports
PLATFORMS = [Platform.SENSOR, Platform.SWITCH]


class _CoordinatorShutdownProtocol(Protocol):
    """Coordinator interface needed for deferred shutdown."""

    async def async_shutdown(self) -> None:
        """Release coordinator resources."""


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Renogy BLE from a config entry."""

    LOGGER.info("Setting up Renogy BLE integration with entry %s", entry.entry_id)

    # Get configuration from entry
    scan_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    device_address = entry.data.get(CONF_ADDRESS)
    device_ids_raw = entry.data.get(CONF_DEVICE_IDS, "255")

    # Parse device IDs which might be a list or a comma-separated string
    if isinstance(device_ids_raw, list):
        device_ids = [int(x) for x in device_ids_raw]
    elif isinstance(device_ids_raw, str):
        device_ids = [
            int(id_str.strip())
            for id_str in device_ids_raw.split(",")
            if id_str.strip().isdigit()
        ]
    else:
        device_ids = [int(device_ids_raw)]

    if not device_ids:
        device_ids = [255]

    if not device_address:
        LOGGER.error("No device address provided in config entry")
        return False

    LOGGER.info(
        "Configuring Renogy BLE device %s with device IDs %s and scan interval %ss",
        device_address,
        device_ids,
        scan_interval,
    )

    # Create a coordinator for this entry
    coordinator = RenogyActiveBluetoothCoordinator(
        hass=hass,
        logger=LOGGER,
        address=device_address,
        device_ids=device_ids,
        scan_interval=scan_interval,
        device_data_callback=lambda coord: _handle_device_update(hass, entry, coord),
    )
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    # Store coordinator in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
    }

    # Forward entry setups to platforms
    LOGGER.info("Setting up platforms for Renogy BLE device %s", device_address)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Start the coordinator after all platforms are set up
    LOGGER.info("Starting coordinator for Renogy BLE device %s", device_address)
    try:
        start_func = coordinator.async_start()
        entry.async_on_unload(start_func)
    except Exception as e:
        LOGGER.error("Error starting coordinator for %s: %s", device_address, e)

    # Force an immediate refresh
    LOGGER.info("Requesting initial refresh for Renogy BLE device %s", device_address)
    hass.async_create_task(coordinator.async_request_refresh())

    return True


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


def _handle_device_update(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: RenogyActiveBluetoothCoordinator,
) -> None:
    """Handle device update callback."""
    LOGGER.debug("Device update for address %s", coordinator.address)

    if entry.entry_id in hass.data[DOMAIN] and coordinator.data:
        # Update the device registry for each detected device
        for device_id, device_data in coordinator.data.items():
            device_type = device_data["device_type"]
            model = device_data.get("model", device_type.capitalize())
            device_name = f"Renogy {device_type.capitalize()} {device_id}"

            hass.async_create_task(
                update_device_registry(
                    hass,
                    entry,
                    coordinator.address,
                    device_id,
                    device_name,
                    model,
                    device_type,
                )
            )


async def update_device_registry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    address: str,
    device_id: int,
    device_name: str,
    model: str,
    device_type: str,
) -> None:
    """Update device in registry."""
    try:
        device_registry = async_get_device_registry(hass)
        device_entry = device_registry.async_get_device(
            {(DOMAIN, f"{address}_{device_id}")}
        )

        if device_entry:
            LOGGER.debug("Updating device registry entry: %s", device_name)
            device_registry.async_update_device(
                device_entry.id, name=device_name, model=model
            )
    except Exception as e:
        LOGGER.error("Error updating device in registry: %s", e)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    LOGGER.debug("Unloading Renogy BLE integration for %s", entry.entry_id)

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok and entry.entry_id in hass.data[DOMAIN]:
        # Stop the coordinator
        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        coordinator.async_stop()
        hass.async_create_task(_async_shutdown_coordinator(coordinator, entry.entry_id))

        # Remove entry from hass.data
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def _async_shutdown_coordinator(
    coordinator: _CoordinatorShutdownProtocol, entry_id: str
) -> None:
    """Attempt coordinator shutdown without blocking entry unload."""
    try:
        await asyncio.wait_for(coordinator.async_shutdown(), timeout=5)
    except TimeoutError:
        LOGGER.warning(
            "Timed out shutting down Renogy BLE coordinator for %s; "
            "persistent session cleanup will continue in the background",
            entry_id,
        )
    except Exception:
        LOGGER.exception(
            "Error shutting down Renogy BLE coordinator for %s",
            entry_id,
        )
