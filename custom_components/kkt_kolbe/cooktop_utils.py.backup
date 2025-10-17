"""Utility functions for KKT IND7705HC cooktop bitfield operations."""
import logging
from typing import Dict, List, Tuple

_LOGGER = logging.getLogger(__name__)

def encode_zone_bitfield(zone_values: Dict[int, int], bits_per_zone: int = 8) -> bytes:
    """
    Encode zone values into a bitfield.

    Args:
        zone_values: Dict mapping zone number (1-5) to value
        bits_per_zone: Number of bits per zone (default 8)

    Returns:
        Encoded bytes for Tuya raw data point

    Example:
        {1: 5, 2: 3, 3: 0, 4: 0, 5: 7} -> bytes with proper bitfield
    """
    result = 0
    for zone, value in zone_values.items():
        if 1 <= zone <= 5:
            shift = (zone - 1) * bits_per_zone
            result |= (value & ((1 << bits_per_zone) - 1)) << shift

    # Convert to bytes (5 zones * 8 bits = 40 bits = 5 bytes)
    byte_count = (5 * bits_per_zone + 7) // 8
    return result.to_bytes(byte_count, byteorder='little')

def decode_zone_bitfield(data: bytes, bits_per_zone: int = 8) -> Dict[int, int]:
    """
    Decode a bitfield into zone values.

    Args:
        data: Raw bytes from Tuya
        bits_per_zone: Number of bits per zone (default 8)

    Returns:
        Dict mapping zone number to value

    Example:
        b'\\x05\\x03\\x00\\x00\\x07' -> {1: 5, 2: 3, 3: 0, 4: 0, 5: 7}
    """
    result = {}
    value = int.from_bytes(data, byteorder='little')
    mask = (1 << bits_per_zone) - 1

    for zone in range(1, 6):
        shift = (zone - 1) * bits_per_zone
        result[zone] = (value >> shift) & mask

    return result

def encode_zone_flags(zone_flags: Dict[int, bool]) -> bytes:
    """
    Encode boolean flags for zones into a single byte.

    Args:
        zone_flags: Dict mapping zone number (1-5) to boolean

    Returns:
        Single byte with bit flags

    Example:
        {1: True, 2: False, 3: True, 4: False, 5: False} -> b'\\x05'
    """
    result = 0
    for zone, flag in zone_flags.items():
        if 1 <= zone <= 5 and flag:
            result |= 1 << (zone - 1)

    return bytes([result])

def decode_zone_flags(data: bytes) -> Dict[int, bool]:
    """
    Decode a byte into zone boolean flags.

    Args:
        data: Single byte or more from Tuya

    Returns:
        Dict mapping zone number to boolean

    Example:
        b'\\x05' -> {1: True, 2: False, 3: True, 4: False, 5: False}
    """
    if not data:
        return {i: False for i in range(1, 6)}

    value = data[0] if isinstance(data, bytes) else data
    result = {}

    for zone in range(1, 6):
        result[zone] = bool(value & (1 << (zone - 1)))

    return result

def encode_bbq_timer(left_minutes: int, right_minutes: int) -> bytes:
    """
    Encode BBQ timer for left and right zones.

    Args:
        left_minutes: Timer for left BBQ zone (0-255)
        right_minutes: Timer for right BBQ zone (0-255)

    Returns:
        Two bytes for BBQ timer
    """
    return bytes([left_minutes & 0xFF, right_minutes & 0xFF])

def decode_bbq_timer(data: bytes) -> Tuple[int, int]:
    """
    Decode BBQ timer data.

    Args:
        data: Two or more bytes from Tuya

    Returns:
        Tuple of (left_minutes, right_minutes)
    """
    if len(data) < 2:
        return (0, 0)

    return (data[0], data[1])

def encode_flex_zones(left_flex: bool, right_flex: bool) -> bytes:
    """
    Encode flex zone status.

    Args:
        left_flex: Left flex zone active
        right_flex: Right flex zone active

    Returns:
        Single byte for flex zones
    """
    result = 0
    if left_flex:
        result |= 1
    if right_flex:
        result |= 2

    return bytes([result])

def decode_flex_zones(data: bytes) -> Tuple[bool, bool]:
    """
    Decode flex zone status.

    Args:
        data: Single byte or more from Tuya

    Returns:
        Tuple of (left_flex, right_flex)
    """
    if not data:
        return (False, False)

    value = data[0] if isinstance(data, bytes) else data
    return (bool(value & 1), bool(value & 2))

def get_zone_power_level(zone_levels: Dict[int, int], zone: int) -> int:
    """
    Get power level for a specific zone (0-25).

    Args:
        zone_levels: Dict from decode_zone_bitfield
        zone: Zone number (1-5)

    Returns:
        Power level (0-25)
    """
    return zone_levels.get(zone, 0)

def set_zone_power_level(zone_levels: Dict[int, int], zone: int, level: int) -> Dict[int, int]:
    """
    Set power level for a specific zone.

    Args:
        zone_levels: Current zone levels
        zone: Zone number (1-5)
        level: Power level (0-25)

    Returns:
        Updated zone levels dict
    """
    new_levels = zone_levels.copy()
    if 1 <= zone <= 5:
        new_levels[zone] = max(0, min(25, level))
    return new_levels