"""Tests for utility functions."""

import pytest

from custom_components.renogy_ble.utils import (
    bytes_to_ascii,
    bytes_to_int,
    create_modbus_read_request,
    create_modbus_write_request,
    format_mac_address,
    modbus_crc16,
    parse_temperature,
    validate_modbus_response,
)


def test_modbus_crc16() -> None:
    """Test Modbus CRC16 calculation."""
    data = b"\x01\x03\x01\x00\x00\x01"
    crc_low, crc_high = modbus_crc16(data)
    assert crc_low == 0x85
    assert crc_high == 0xF6


def test_create_modbus_read_request() -> None:
    """Test creation of Modbus read request frame."""
    frame = create_modbus_read_request(1, 3, 0x0100, 1)
    assert bytes(frame) == b"\x01\x03\x01\x00\x00\x01\x85\xf6"


def test_create_modbus_write_request() -> None:
    """Test creation of Modbus write request frame."""
    frame = create_modbus_write_request(1, 0x010A, 1)
    assert bytes(frame) == b"\x01\x06\x01\x0a\x00\x01\x69\xf4"


def test_bytes_to_int() -> None:
    """Test bytes to int/float conversion."""
    # 2 bytes unsigned
    assert bytes_to_int(b"\x00\x0a", 0, 2) == 10
    # 2 bytes signed negative
    assert bytes_to_int(b"\xff\xf6", 0, 2, signed=True) == -10
    # Scaling
    assert bytes_to_int(b"\x00\x64", 0, 2, scale=0.1) == 10.0


def test_bytes_to_ascii() -> None:
    """Test bytes to ASCII string conversion."""
    assert bytes_to_ascii(b"Renogy\x00\x00", 0, 8) == "Renogy"


def test_parse_temperature() -> None:
    """Test parsing temperature value."""
    # Positive
    assert parse_temperature(25) == 25
    # Negative with sign bit (128 offset)
    assert parse_temperature(138) == -10


def test_validate_modbus_response() -> None:
    """Test validation of Modbus response frame."""
    # Valid response: dev_id=1, func=3, bytes=2, value=10, CRC
    valid_data = b"\x01\x03\x02\x00\x0a\x38\x43"
    assert validate_modbus_response(valid_data, 1) is True

    # Too short
    assert validate_modbus_response(b"\x01\x03", 1) is False

    # Error response (bit 7 set on function code)
    assert validate_modbus_response(b"\x01\x83\x02\x01\x02", 1) is False

    # Invalid CRC
    assert validate_modbus_response(b"\x01\x03\x02\x00\x0a\x00\x00", 1) is False


def test_format_mac_address() -> None:
    """Test MAC address normalization."""
    assert format_mac_address("aabbccddeeff") == "AA:BB:CC:DD:EE:FF"
    assert format_mac_address("AA-BB-CC-DD-EE-FF") == "AA:BB:CC:DD:EE:FF"
    with pytest.raises(ValueError):
        format_mac_address("invalidmac")
