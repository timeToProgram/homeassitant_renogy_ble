"""Utility functions for Renogy BT integration."""

import logging

logger = logging.getLogger(__name__)


def modbus_crc16(data: bytes | bytearray) -> tuple:
    """Calculate the Modbus CRC16 checksum."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return (crc & 0xFF, (crc >> 8) & 0xFF)


def create_modbus_read_request(
    device_id: int, function_code: int, register: int, word_count: int
) -> bytearray:
    """Create a Modbus read request frame."""
    frame = bytearray(
        [
            device_id,
            function_code,
            (register >> 8) & 0xFF,
            register & 0xFF,
            (word_count >> 8) & 0xFF,
            word_count & 0xFF,
        ]
    )
    crc_low, crc_high = modbus_crc16(frame)
    frame.extend([crc_low, crc_high])
    logger.debug("Created Modbus request: register=%s, frame=%s", register, list(frame))
    return frame


def create_modbus_write_request(device_id: int, register: int, value: int) -> bytearray:
    """Create a Modbus write single register request frame."""
    frame = bytearray(
        [
            device_id,
            0x06,  # Write Single Register function code
            (register >> 8) & 0xFF,
            register & 0xFF,
            (value >> 8) & 0xFF,
            value & 0xFF,
        ]
    )
    crc_low, crc_high = modbus_crc16(frame)
    frame.extend([crc_low, crc_high])
    logger.debug(
        "Created Modbus write request: register=%s, value=%s, frame=%s",
        register,
        value,
        list(frame),
    )
    return frame


def bytes_to_int(
    data: bytes, offset: int, length: int, scale: float = 1.0, signed: bool = False
) -> int:
    """Convert bytes to integer or float value."""
    if offset + length > len(data):
        logger.warning(
            "Data too short: offset=%s, length=%s, data_len=%s",
            offset,
            length,
            len(data),
        )
        return 0

    if length == 1:
        value = data[offset]
        if signed and value > 127:
            value -= 256
    elif length == 2:
        value = (data[offset] << 8) | data[offset + 1]
        if signed and value > 32767:
            value -= 65536
    elif length == 4:
        value = (
            (data[offset] << 24)
            | (data[offset + 1] << 16)
            | (data[offset + 2] << 8)
            | data[offset + 3]
        )
        if signed and value > 2147483647:
            value -= 4294967296
    else:
        logger.warning("Unsupported byte length: %s", length)
        return 0

    if scale != 1.0:
        return round(value * scale, 3)
    return value


def bytes_to_ascii(data: bytes, offset: int, length: int) -> str:
    """Convert bytes to ASCII string."""
    if offset + length > len(data):
        return ""

    result = ""
    for i in range(length):
        char = data[offset + i]
        if 32 <= char <= 126:  # Printable ASCII
            result += chr(char)
    return result.strip()


def parse_temperature(raw_value: int, offset: int = 0) -> float:
    """Parse temperature value with sign handling."""
    if raw_value > 127:
        return -(raw_value - 128) - offset
    return raw_value - offset


def validate_modbus_response(
    data: bytes, expected_device_id: int | None = None
) -> bool:
    """Validate a Modbus response frame."""
    if len(data) < 5:
        logger.warning("Response too short: %s bytes", len(data))
        return False

    # Check for error response
    if data[1] & 0x80:
        error_code = data[2] if len(data) > 2 else 0
        logger.warning(
            "Modbus error response: function=%s, error_code=%s",
            data[1],
            error_code,
        )
        return False

    # Validate CRC
    if len(data) >= 5:
        byte_count = data[2]
        expected_len = 3 + byte_count + 2
        if len(data) < expected_len:
            logger.warning(
                "Response incomplete: got %s, expected %s", len(data), expected_len
            )
            return False

        # Verify CRC
        payload = data[: expected_len - 2]
        received_crc = (data[expected_len - 1] << 8) | data[expected_len - 2]
        crc_low, crc_high = modbus_crc16(payload)
        calculated_crc = (crc_high << 8) | crc_low

        if received_crc != calculated_crc:
            logger.warning(
                "CRC mismatch: received=%s, calculated=%s",
                hex(received_crc),
                hex(calculated_crc),
            )
            return False

    return True


def format_mac_address(mac: str) -> str:
    """Normalize MAC address format to XX:XX:XX:XX:XX:XX."""
    mac = mac.replace("-", "").replace(":", "").replace(" ", "").upper()

    if len(mac) != 12:
        raise ValueError(f"Invalid MAC address: {mac}")

    return ":".join(mac[i : i + 2] for i in range(0, 12, 2))
