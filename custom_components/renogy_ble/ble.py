"""BLE communication module for Renogy devices."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from bleak import BleakClient
from bleak_retry_connector import establish_connection
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import (
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
)
from homeassistant.components.bluetooth.active_update_coordinator import (
    ActiveBluetoothDataUpdateCoordinator,
)
from homeassistant.core import CoreState, HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    DEFAULT_SCAN_INTERVAL,
)
from .parsers import DeviceType, get_registers_for_device, parse_response
from .utils import (
    create_modbus_read_request,
    create_modbus_write_request,
    validate_modbus_response,
)


class RenogyActiveBluetoothCoordinator(
    ActiveBluetoothDataUpdateCoordinator[Dict[int, Any]]
):
    """Class to manage fetching Renogy BLE data via active connections."""

    def __init__(
        self,
        hass: HomeAssistant,
        logger: logging.Logger,
        *,
        address: str,
        device_ids: List[int],
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
        device_data_callback: Optional[
            Callable[[RenogyActiveBluetoothCoordinator], Any]
        ] = None,
    ):
        """Initialize the coordinator."""
        super().__init__(
            hass=hass,
            logger=logger,
            address=address,
            needs_poll_method=self._needs_poll,
            poll_method=self._async_poll_device,
            mode=BluetoothScanningMode.ACTIVE,
            connectable=True,
        )
        self.device_ids = device_ids
        self.scan_interval = scan_interval
        self.last_poll_time: Optional[datetime] = None
        self.device_data_callback = device_data_callback

        self.client: Optional[BleakClient] = None
        self._connected = False
        self._notify_char: str = "0000fff1-0000-1000-8000-00805f9b34fb"
        self._write_char: str = "0000ffd1-0000-1000-8000-00805f9b34fb"
        self._notification_data = bytearray()
        self._notification_event = asyncio.Event()

        self.detected_types: Dict[int, DeviceType] = {}
        self.device_models: Dict[int, str] = {}

        # Add required properties for Home Assistant CoordinatorEntity compatibility
        self.last_update_success = True
        self._update_listeners: List[Callable[[], None]] = []
        self.update_interval = timedelta(seconds=scan_interval)
        self._unsub_refresh: Optional[Callable[[], None]] = None

        # Add connection lock to prevent multiple concurrent operations
        self._connection_lock = asyncio.Lock()
        self._connection_in_progress = False

    @property
    def is_connected(self) -> bool:
        """Return True if BLE client is connected."""
        return self._connected and self.client is not None and self.client.is_connected

    def _notification_handler(self, sender: Any, data: bytearray) -> None:
        """Handle incoming notification data."""
        self.logger.debug("Received notification: %s", data.hex())
        self._notification_data.extend(data)
        self._notification_event.set()

    def _on_disconnect(self, client: BleakClient) -> None:
        """Callback when BLE disconnected."""
        self.logger.warning("Disconnected from %s", self.address)
        self._connected = False

    async def async_connect(self) -> Optional[BleakClient]:
        """Establish BLE connection using establish_connection."""
        if self.is_connected:
            return self.client

        ble_device = bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )
        if not ble_device:
            self.logger.warning(
                "No connectable device found for address %s", self.address
            )
            return None

        try:
            self.logger.info("Connecting to %s...", self.address)
            self.client = await establish_connection(
                BleakClient,
                ble_device,
                ble_device.name or self.address,
                max_attempts=3,
                disconnected_callback=self._on_disconnect,
            )

            # Setup characteristics
            for service in self.client.services:
                for char in service.characteristics:
                    if (
                        char.uuid.lower()
                        == "0000ffd1-0000-1000-8000-00805f9b34fb".lower()
                    ):
                        self._write_char = char.uuid
                    elif (
                        char.uuid.lower()
                        == "0000fff1-0000-1000-8000-00805f9b34fb".lower()
                    ):
                        self._notify_char = char.uuid

            if not self._notify_char:
                self._notify_char = "0000fff1-0000-1000-8000-00805f9b34fb"
            if not self._write_char:
                self._write_char = "0000ffd1-0000-1000-8000-00805f9b34fb"

            # Start notifications
            await self.client.start_notify(
                self._notify_char, self._notification_handler
            )
            self._connected = True
            self.logger.info("Connected successfully to %s", self.address)
            return self.client
        except Exception as e:
            self.logger.error("Failed to connect to %s: %s", self.address, e)
            self._connected = False
            self.client = None
            return None

    async def async_probe_device_types(self) -> Dict[int, str]:
        """Probe all configured device IDs to determine their types."""
        device_types = {}
        client = await self.async_connect()
        if not client:
            return {}

        for device_id in self.device_ids:
            detected = await self._async_detect_device_type(device_id)
            if detected:
                device_types[device_id] = detected.value
                self.detected_types[device_id] = detected

        return device_types

    async def read_registers(
        self, device_id: int, register: int, word_count: int
    ) -> Optional[bytes]:
        """Read holding registers from a device using Modbus RTU over BLE."""
        async with self._connection_lock:
            client = await self.async_connect()
            if not client:
                return None

            self._notification_data.clear()
            self._notification_event.clear()

            request = create_modbus_read_request(device_id, 0x03, register, word_count)
            self.logger.debug(
                "Sending request: dev=%s, reg=%s, words=%s, bytes=%s",
                device_id,
                register,
                word_count,
                request.hex(),
            )

            try:
                await client.write_gatt_char(self._write_char, request)
            except Exception as e:
                self.logger.error("Write failed: %s", e)
                self._connected = False
                return None

            # Wait for response
            try:
                await asyncio.wait_for(self._notification_event.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.logger.warning(
                    "Timeout waiting for response (device=%s, register=%s)",
                    device_id,
                    register,
                )
                return None

            # Let all data arrive
            await asyncio.sleep(0.3)
            response = bytes(self._notification_data)

            if len(response) >= 5 and validate_modbus_response(response, device_id):
                return response

            self.logger.warning(
                "Invalid response: %s", response.hex() if response else "None"
            )
            return None

    async def async_write_register(
        self, device_id: int, register: int, value: int
    ) -> bool:
        """Write to a register."""
        async with self._connection_lock:
            client = await self.async_connect()
            if not client:
                return False

            self._notification_data.clear()
            self._notification_event.clear()

            request = create_modbus_write_request(device_id, register, value)
            self.logger.debug("Sending write request: %s", request.hex())

            try:
                await client.write_gatt_char(self._write_char, request)
            except Exception as e:
                self.logger.error("Write register failed: %s", e)
                self._connected = False
                return False

            # Wait for response
            try:
                await asyncio.wait_for(self._notification_event.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.logger.warning("Timeout waiting for write response")
                return False

            await asyncio.sleep(0.3)
            response = bytes(self._notification_data)
            if len(response) >= 5 and validate_modbus_response(response, device_id):
                return True
            return False

    async def _async_detect_device_type(self, device_id: int) -> Optional[DeviceType]:
        """Proactively probe the device to determine type.

        Checks if it is a battery, inverter, or controller.
        """
        # Probe Battery info (register 5042, words 8)
        self.logger.debug("Probing device %s as Battery...", device_id)
        response = await self.read_registers(device_id, 5042, 8)
        if response:
            self.logger.info("Device %s detected as BATTERY", device_id)
            return DeviceType.BATTERY

        # Probe Inverter main status (register 4000, words 10)
        self.logger.debug("Probing device %s as Inverter...", device_id)
        response = await self.read_registers(device_id, 4000, 10)
        if response:
            self.logger.info("Device %s detected as INVERTER", device_id)
            return DeviceType.INVERTER

        # Probe Controller charging info (register 256, words 34)
        self.logger.debug("Probing device %s as Controller...", device_id)
        response = await self.read_registers(device_id, 256, 34)
        if response:
            self.logger.info("Device %s detected as CONTROLLER", device_id)
            return DeviceType.CONTROLLER

        self.logger.warning("Could not auto-detect type for device ID %s", device_id)
        return None

    async def _async_fetch_device_model(
        self, device_id: int, device_type: DeviceType
    ) -> str:
        """Fetch the device model name from its info registers."""
        if device_type == DeviceType.BATTERY:
            response = await self.read_registers(device_id, 5122, 8)
            if response:
                parsed = parse_response(device_type, 5122, response)
                if "model" in parsed:
                    return parsed["model"]
        elif device_type == DeviceType.INVERTER:
            response = await self.read_registers(device_id, 4303, 24)
            if response:
                parsed = parse_response(device_type, 4303, response)
                if "model" in parsed:
                    return parsed["model"]
        elif device_type == DeviceType.CONTROLLER:
            response = await self.read_registers(device_id, 12, 8)
            if response:
                parsed = parse_response(device_type, 12, response)
                if "model" in parsed:
                    return parsed["model"]
        return f"Renogy {device_type.value.capitalize()}"

    async def async_config_entry_first_refresh(self) -> None:
        """Perform first refresh for config entry setup."""
        await self.async_request_refresh()
        if not self.last_update_success:
            from homeassistant.exceptions import ConfigEntryNotReady

            raise ConfigEntryNotReady(
                f"Failed to connect to Renogy device {self.address}"
            )

    async def async_request_refresh(self) -> None:
        """Request a refresh."""
        self.logger.debug("Manual refresh requested for device %s", self.address)

        if self._connection_in_progress:
            self.logger.debug(
                "Connection already in progress, skipping refresh request"
            )
            return

        service_info = bluetooth.async_last_service_info(self.hass, self.address)
        try:
            await self._async_poll_device(service_info)
            self.async_update_listeners()
        except Exception as err:
            self.last_update_success = False
            self.logger.error("Error refreshing device %s: %s", self.address, err)

    def async_add_listener(
        self, update_callback: Callable[[], None], context: Any = None
    ) -> Callable[[], None]:
        """Listen for data updates."""
        if update_callback not in self._update_listeners:
            self._update_listeners.append(update_callback)

        def remove_listener() -> None:
            """Remove update callback."""
            if update_callback in self._update_listeners:
                self._update_listeners.remove(update_callback)

        return remove_listener

    def async_update_listeners(self) -> None:
        """Update all registered listeners."""
        for update_callback in self._update_listeners:
            update_callback()

    def _schedule_refresh(self) -> None:
        """Schedule a refresh with the update interval."""
        if self._unsub_refresh:
            self._unsub_refresh()
            self._unsub_refresh = None

        self._unsub_refresh = async_track_time_interval(
            self.hass, self._handle_refresh_interval, self.update_interval
        )
        self.logger.debug("Scheduled next refresh in %s seconds", self.scan_interval)

    async def _handle_refresh_interval(self, _now=None):
        """Handle a refresh interval occurring."""
        self.logger.debug("Regular interval refresh for %s", self.address)
        await self.async_request_refresh()

    def async_start(self) -> Callable[[], None]:
        """Start polling."""
        self.logger.debug("Starting polling for device %s", self.address)

        def _unsub() -> None:
            """Unsubscribe from updates."""
            if self._unsub_refresh:
                self._unsub_refresh()
                self._unsub_refresh = None

        _unsub()

        result = super().async_start()
        self._schedule_refresh()
        self.hass.async_create_task(self.async_request_refresh())
        return result

    def async_stop(self) -> None:
        """Stop polling."""
        if self._unsub_refresh:
            self._unsub_refresh()
            self._unsub_refresh = None
        self._update_listeners = []

    async def async_shutdown(self) -> None:
        """Stop polling and release any persistent BLE sessions."""
        self.async_stop()
        if self.client:
            try:
                await self.client.disconnect()
            except Exception:
                pass
            self.client = None

    @callback
    def _needs_poll(
        self,
        service_info: BluetoothServiceInfoBleak,
        last_poll: float | None,
    ) -> bool:
        """Determine if device needs polling based on time since last poll."""
        if self.hass.state != CoreState.running:
            return False

        connectable_device = bluetooth.async_ble_device_from_address(
            self.hass, service_info.device.address, connectable=True
        )
        if not connectable_device:
            self.logger.warning(
                "No connectable device found for %s", service_info.address
            )
            return False

        if self._connection_in_progress:
            return False

        if last_poll is None:
            return True

        time_since_poll = datetime.now().timestamp() - last_poll
        return time_since_poll >= self.scan_interval

    async def _async_poll_device(
        self, service_info: BluetoothServiceInfoBleak | None = None
    ) -> Dict[int, Any]:
        """Poll all configured device IDs and aggregate their parsed data."""
        if self._connection_in_progress:
            return self.data if self.data else {}

        self.last_poll_time = datetime.now()
        self._connection_in_progress = True

        try:
            client = await self.async_connect()
            if not client:
                self.last_update_success = False
                return self.data if self.data else {}

            all_devices_data = {}
            for device_id in self.device_ids:
                # Auto-detect type if not already known
                if device_id not in self.detected_types:
                    detected_type = await self._async_detect_device_type(device_id)
                    if not detected_type:
                        continue
                    self.detected_types[device_id] = detected_type

                    # Fetch model name
                    model_name = await self._async_fetch_device_model(
                        device_id, detected_type
                    )
                    self.device_models[device_id] = model_name

                device_type = self.detected_types[device_id]
                model_name = self.device_models[device_id]
                registers = get_registers_for_device(device_type)

                device_data = {
                    "device_id": device_id,
                    "device_type": device_type.value,
                    "model": model_name,
                    "mac_address": self.address,
                    "is_available": True,
                }

                for reg_info in registers:
                    self.logger.debug(
                        "Reading register %s for device %s", reg_info["name"], device_id
                    )
                    response = await self.read_registers(
                        device_id, reg_info["register"], reg_info["words"]
                    )
                    if response:
                        parsed = parse_response(
                            device_type, reg_info["register"], response
                        )
                        device_data.update(parsed)
                    await asyncio.sleep(0.1)

                all_devices_data[device_id] = device_data

            if all_devices_data:
                self.data = all_devices_data
                self.last_update_success = True
                self.logger.debug("Poll successful: %s", self.data)

                # Call callback if available
                if self.device_data_callback:
                    try:
                        res = self.device_data_callback(self)
                        if asyncio.iscoroutine(res):
                            await res
                    except Exception as e:
                        self.logger.error("Error in device data callback: %s", e)
            else:
                self.last_update_success = False

            return self.data if self.data else {}

        finally:
            self._connection_in_progress = False
