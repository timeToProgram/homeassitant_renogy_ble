"""Config flow for Renogy BLE integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
)
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_ADDRESS, CONF_SCAN_INTERVAL

from .const import (
    CONF_DEVICE_IDS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .device_name import (
    has_real_device_name,
    is_supported_renogy_ble_name,
)

UNKNOWN_DEVICE_NAME = "Unknown Renogy Device"

SCAN_INTERVAL_SCHEMA = {
    vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
        vol.Coerce(int),
        vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
    ),
}


def _display_name_for_discovery(discovery_info: BluetoothServiceInfoBleak) -> str:
    """Return a stable display name for a discovered BLE device."""
    if has_real_device_name(discovery_info.name):
        return discovery_info.name

    return UNKNOWN_DEVICE_NAME


class RenogyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Renogy BLE."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_devices: dict[str, BluetoothServiceInfoBleak] = {}
        self._discovered_device: BluetoothServiceInfoBleak | None = None

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> RenogyOptionsFlowHandler:
        """Return the options flow for this handler."""
        return RenogyOptionsFlowHandler(config_entry)

    def _is_renogy_device(self, discovery_info: BluetoothServiceInfoBleak) -> bool:
        """Check if a BLE device advertises a supported Renogy name."""
        manufacturer_data = getattr(
            discovery_info.advertisement, "manufacturer_data", {}
        )
        return is_supported_renogy_ble_name(
            discovery_info.name,
            manufacturer_data=manufacturer_data,
        )

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle the bluetooth discovery step."""
        # Check if this is a Renogy device based on the name
        if not self._is_renogy_device(discovery_info):
            return self.async_abort(reason="not_supported_device")

        LOGGER.debug(
            "Bluetooth auto-discovery for Renogy device: %s (%s)",
            discovery_info.name,
            discovery_info.address,
        )
        discovery_name = _display_name_for_discovery(discovery_info)

        # Set unique ID and check if already configured
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        # Store the discovered device for later
        self._discovered_device = discovery_info

        # Set title to user-readable name
        self.context["title_placeholders"] = {
            "name": discovery_name,
            "address": discovery_info.address,
        }

        # Proceed to configuration options
        return await self.async_step_user()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the user step to pick discovered device or configure options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if self._discovered_device:
                # Coming from bluetooth discovery with device already selected
                user_input[CONF_ADDRESS] = self._discovered_device.address

                # Create a config entry
                return self.async_create_entry(
                    title=_display_name_for_discovery(self._discovered_device),
                    data=user_input,
                )
            elif CONF_ADDRESS in user_input:
                # Manual device selection
                address = user_input[CONF_ADDRESS]
                discovery_info = self._discovered_devices[address]

                await self.async_set_unique_id(address, raise_on_progress=False)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=_display_name_for_discovery(discovery_info),
                    data=user_input,
                )

        # If we have a discovered device from bluetooth auto-discovery,
        # just show config options (device ids, scan interval)
        if self._discovered_device:
            discovered_schema = vol.Schema(
                {
                    vol.Required(CONF_DEVICE_IDS, default="255"): str,
                    **SCAN_INTERVAL_SCHEMA,
                }
            )
            return self.async_show_form(
                step_id="user",
                data_schema=discovered_schema,
                description_placeholders={
                    "device_name": _display_name_for_discovery(self._discovered_device),
                    "default_interval": str(DEFAULT_SCAN_INTERVAL),
                },
                errors=errors,
            )

        # Otherwise, scan for available devices to let the user pick one
        await self._async_discover_devices()

        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")

        # Show form to select a discovered device
        address_schema = vol.Schema(
            {
                vol.Required(CONF_ADDRESS): vol.In(
                    {
                        address: (f"{_display_name_for_discovery(info)} ({address})")
                        for address, info in self._discovered_devices.items()
                    }
                ),
                vol.Required(CONF_DEVICE_IDS, default="255"): str,
                **SCAN_INTERVAL_SCHEMA,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=address_schema,
            description_placeholders={
                "device_name": "Select below",
                "default_interval": str(DEFAULT_SCAN_INTERVAL),
            },
            errors=errors,
        )

    async def _async_discover_devices(self) -> None:
        """Discover Bluetooth devices."""
        LOGGER.debug("Scanning for Renogy BLE devices")

        self._discovered_devices = {}

        for discovery_info in bluetooth.async_discovered_service_info(self.hass):
            # Skip devices that don't match our pattern
            if not self._is_renogy_device(discovery_info):
                continue

            # Skip devices that are already configured
            address = discovery_info.address
            if address in self._async_current_ids():
                continue

            # Add to list of discovered devices
            self._discovered_devices[address] = discovery_info
            LOGGER.debug("Found Renogy device: %s (%s)", discovery_info.name, address)

        LOGGER.debug(
            "Found %s unconfigured Renogy devices", len(self._discovered_devices)
        )

    async def async_step_manual_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle manual configuration of a Renogy BLE device."""
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            # Validate address format
            try:
                from .utils import format_mac_address

                address = format_mac_address(address)
            except ValueError:
                errors[CONF_ADDRESS] = "invalid_mac"

            if not errors:
                await self.async_set_unique_id(address, raise_on_progress=False)
                self._abort_if_unique_id_configured()

                # Parse and validate device IDs
                device_ids_str = user_input.get(CONF_DEVICE_IDS, "255")
                device_ids = [
                    int(id_str.strip())
                    for id_str in device_ids_str.split(",")
                    if id_str.strip().isdigit()
                ]
                if not device_ids:
                    device_ids = [255]

                # Validate connection & probe
                error = await self._async_validate_device(address, device_ids)
                if not error:
                    return self.async_create_entry(
                        title=f"Renogy BLE ({address})",
                        data={
                            CONF_ADDRESS: address,
                            CONF_DEVICE_IDS: device_ids,
                            CONF_SCAN_INTERVAL: user_input.get(
                                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                            ),
                        },
                    )
                errors.update(error)

        schema = vol.Schema(
            {
                vol.Required(CONF_ADDRESS): str,
                vol.Required(CONF_DEVICE_IDS, default="255"): str,
                **SCAN_INTERVAL_SCHEMA,
            }
        )
        return self.async_show_form(
            step_id="manual_device",
            data_schema=schema,
            errors=errors,
        )

    async def _async_validate_device(
        self, address: str, device_ids: list[int]
    ) -> dict[str, str]:
        """Validate connection and probe device types."""
        from .ble import RenogyActiveBluetoothCoordinator

        coordinator = RenogyActiveBluetoothCoordinator(
            self.hass,
            LOGGER,
            address=address,
            device_ids=device_ids,
        )
        try:
            device_types = await coordinator.async_probe_device_types()
            if not device_types:
                return {"base": "no_devices_found"}
        except Exception:
            return {"base": "cannot_connect"}
        finally:
            await coordinator.async_shutdown()

        return {}


class RenogyOptionsFlowHandler(OptionsFlow):
    """Handle Renogy BLE options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage integration options."""
        if user_input is not None:
            # Update the config entry data directly or via options
            self.hass.config_entries.async_update_entry(
                self._config_entry, data={**self._config_entry.data, **user_input}
            )
            return self.async_create_entry(title="", data={})

        current_ids = self._config_entry.data.get(CONF_DEVICE_IDS, "255")
        current_interval = self._config_entry.data.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )

        schema = vol.Schema(
            {
                vol.Required(CONF_DEVICE_IDS, default=current_ids): str,
                vol.Optional(CONF_SCAN_INTERVAL, default=current_interval): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                ),
            }
        )
        return self.async_show_form(
            step_id="init",
            data_schema=schema,
        )
