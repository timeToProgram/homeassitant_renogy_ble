"""Tests for device data parsers."""

from custom_components.renogy.parsers import (
    DeviceType,
    get_registers_for_device,
    parse_battery_alarm_info,
    parse_battery_cell_info,
    parse_battery_device_info,
    parse_battery_info,
    parse_battery_temp_info,
    parse_controller_charging_info,
    parse_controller_device_info,
    parse_controller_faults,
    parse_inverter_main_status,
    parse_response,
)


def test_parse_controller_device_info() -> None:
    """Test controller device info parsing."""
    # Register 12 starts at offset 3
    data = b"\x01\x03\x10Rover-40A\x00\x00\x00\x00\x00\x00\x00\x00"
    parsed = parse_controller_device_info(data)
    assert parsed["model"] == "Rover-40A"


def test_parse_controller_charging_info() -> None:
    """Test controller charging info parsing."""
    # Charging info register 256
    # offset 3 is start of Modbus payload
    data = (
        b"\x01\x03\x44"  # Header
        + b"\x00\x64"  # battery SOC: 100%
        + b"\x00\x8c"  # battery voltage: 14.0V
        + b"\x00\x0a"  # charging current: 0.1A
        + b"\x19\x1e"  # controller/battery temp: 25C / 30C
        + b"\x00\x8c"  # load voltage: 14.0V
        + b"\x00\x00"  # load current: 0A
        + b"\x00\x00"  # load power: 0W
        + b"\x00\xc8"  # PV voltage: 20.0V
        + b"\x00\x07"  # PV current: 0.07A
        + b"\x00\x01"  # PV power: 1W
        + b"\x00" * 10  # pad
        + b"\x00\x00"  # max charging power today
        + b"\x00\x00"  # max discharging power today
        + b"\x00\x00"  # charging amp hours today
        + b"\x00\x00"  # discharging amp hours today
        + b"\x00\x00"  # power generation today
        + b"\x00\x00"  # power consumption today
        + b"\x00" * 14  # pad
        + b"\x00\x00\x00\x64"  # power generation total: 100Wh
        + b"\x00\x00\x00\x00"  # pad
        + b"\x00"  # load status: off
        + b"\x05"  # charging status: floating
        + b"\x00\x00"  # padding to complete 68 bytes of payload
    )
    parsed = parse_controller_charging_info(data)
    assert parsed["battery_percentage"] == 100
    assert parsed["battery_voltage"] == 14.0
    assert parsed["battery_current"] == 0.1
    assert parsed["battery_temperature"] == 30.0
    assert parsed["controller_temperature"] == 25.0
    assert parsed["pv_voltage"] == 20.0
    assert parsed["pv_power"] == 1
    assert parsed["power_generation_total"] == 100
    assert parsed["charging_status"] == "floating"


def test_parse_controller_faults() -> None:
    """Test controller faults parsing."""
    # Faults register 289
    # High word: 0x0002 (ambient_temp_too_high), Low word: 0x0000
    data = b"\x01\x03\x04\x00\x40\x00\x00"
    parsed = parse_controller_faults(data)
    assert "ambient_temp_too_high" in parsed["faults"]
    assert parsed["fault_count"] == 1
    assert parsed["warning_count"] == 0


def test_parse_battery_cell_info() -> None:
    """Test battery cell info parsing."""
    # 4 cells, each 3.2V (32 units)
    data = b"\x01\x03\x0a\x00\x04\x00\x20\x00\x20\x00\x20\x00\x20"
    parsed = parse_battery_cell_info(data)
    assert parsed["cell_count"] == 4
    assert parsed["cell_voltages"] == [3.2, 3.2, 3.2, 3.2]


def test_parse_battery_temp_info() -> None:
    """Test battery temperature info parsing."""
    # 2 sensors, 25.0C and 26.0C (250 and 260 units)
    data = b"\x01\x03\x06\x00\x02\x00\xfa\x01\x04"
    parsed = parse_battery_temp_info(data)
    assert parsed["temperature_count"] == 2
    assert parsed["temperatures"] == [25.0, 26.0]
    assert parsed["battery_temperature"] == 25.0


def test_parse_battery_info() -> None:
    """Test battery main info parsing."""
    # current: -10A (-1000 units), voltage: 12.8V (128 units), remaining: 80Ah, total: 100Ah
    data = b"\x01\x03\x0c\xfc\x18\x00\x80\x00\x01\x38\x80\x00\x01\x86\xa0"
    parsed = parse_battery_info(data)
    assert parsed["current"] == -10.0
    assert parsed["voltage"] == 12.8
    assert parsed["remaining_capacity"] == 80.0
    assert parsed["total_capacity"] == 100.0
    assert parsed["soc"] == 80.0
    assert parsed["power"] == -128.0


def test_parse_battery_alarm_info() -> None:
    """Test battery alarm info parsing."""
    # offset 3. 20 bytes payload. All normal.
    data = b"\x01\x03\x14" + b"\x00" * 20
    parsed = parse_battery_alarm_info(data)
    assert parsed["alarm_count"] == 0
    assert parsed["warning_count"] == 0
    assert parsed["discharge_mosfet"] == "off"
    assert parsed["charge_mosfet"] == "off"


def test_parse_battery_device_info() -> None:
    """Test battery device info parsing."""
    data = b"\x01\x03\x10SmartLithium\x00\x00\x00\x00"
    parsed = parse_battery_device_info(data)
    assert parsed["model"] == "SmartLithium"


def test_parse_inverter_main_status() -> None:
    """Test inverter main status parsing."""
    # input_v: 0, input_c: 0, output_v: 120.0V (1200 units), output_c: 5.0A (500 units), frequency: 60Hz (6000 units)
    # battery_v: 12.8V (128 units), temp: 25.0C (250 units), status high/low: 0, input_freq: 0
    data = (
        b"\x01\x03\x14"
        + b"\xff\xff"  # input_v
        + b"\xff\xff"  # input_c
        + b"\x04\xb0"  # output_v
        + b"\x01\xf4"  # output_c
        + b"\x17\x70"  # output_freq
        + b"\x00\x80"  # battery_v
        + b"\x00\xfa"  # temp
        + b"\x00\x00\x00\x00"  # status high / low
        + b"\xff\xff"  # input_freq
    )
    parsed = parse_inverter_main_status(data)
    assert parsed["input_voltage"] == 0.0
    assert parsed["output_voltage"] == 120.0
    assert parsed["output_current"] == 5.0
    assert parsed["output_frequency"] == 60.0
    assert parsed["battery_voltage"] == 12.8
    assert parsed["temperature"] == 25.0
    assert parsed["output_power"] == 600.0


def test_get_registers_for_device() -> None:
    """Test register definitions retrieval."""
    assert len(get_registers_for_device(DeviceType.CONTROLLER)) > 0
    assert len(get_registers_for_device(DeviceType.BATTERY)) > 0
    assert len(get_registers_for_device(DeviceType.INVERTER)) > 0


def test_parse_response_dispatch() -> None:
    """Test parse_response dispatch wrapper."""
    data = b"\x01\x03\x10Rover-40A\x00\x00\x00\x00\x00\x00\x00\x00"
    parsed = parse_response(DeviceType.CONTROLLER, 12, data)
    assert parsed["model"] == "Rover-40A"
