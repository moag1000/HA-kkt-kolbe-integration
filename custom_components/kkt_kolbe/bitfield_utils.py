"""Bitfield utilities for KKT Kolbe RAW data point handling."""
from __future__ import annotations

import base64
import logging
from typing import Any, Union

_LOGGER = logging.getLogger(__name__)

def decode_base64_to_bytes(base64_data: str) -> bytes:
    """Decode Base64 string to bytes."""
    try:
        return base64.b64decode(base64_data)
    except Exception as e:
        _LOGGER.error(f"Failed to decode Base64 data '{base64_data}': {e}")
        return b''

def encode_bytes_to_base64(data: bytes) -> str:
    """Encode bytes to Base64 string."""
    try:
        return base64.b64encode(data).decode('utf-8')
    except Exception as e:
        _LOGGER.error(f"Failed to encode bytes to Base64: {e}")
        return ""

def extract_zone_value_from_bitfield(base64_data: str, zone: int, bits_per_zone: int = 8) -> int:
    """
    Extract zone-specific value from bitfield data.

    Args:
        base64_data: Base64 encoded bitfield data
        zone: Zone number (1-5)
        bits_per_zone: Number of bits per zone (default 8)

    Returns:
        Zone-specific value (0-255 for 8-bit zones)
    """
    if not base64_data:
        return 0

    try:
        # Decode Base64 to bytes
        data = decode_base64_to_bytes(base64_data)
        if not data:
            return 0

        # Calculate byte index for zone (zone 1 = index 0)
        byte_index = zone - 1

        # Check if we have enough data
        if byte_index >= len(data):
            _LOGGER.debug(f"Zone {zone} byte index {byte_index} exceeds data length {len(data)}")
            return 0

        # Extract byte value for the zone
        value = data[byte_index]
        _LOGGER.debug(f"Zone {zone}: extracted value {value} from byte index {byte_index}")
        return value

    except Exception as e:
        _LOGGER.error(f"Failed to extract zone {zone} value from bitfield '{base64_data}': {e}")
        return 0

def extract_zone_bit_from_bitfield(base64_data: str, zone: int) -> bool:
    """
    Extract zone-specific bit from bitfield data (for boolean states).

    Args:
        base64_data: Base64 encoded bitfield data
        zone: Zone number (1-5)

    Returns:
        True if zone bit is set, False otherwise
    """
    if not base64_data:
        return False

    try:
        # Decode Base64 to bytes
        data = decode_base64_to_bytes(base64_data)
        if not data:
            return False

        # For bit-based fields, zones are individual bits
        # Zone 1 = bit 0, Zone 2 = bit 1, etc.
        bit_index = zone - 1
        byte_index = bit_index // 8
        bit_position = bit_index % 8

        # Check if we have enough data
        if byte_index >= len(data):
            _LOGGER.debug(f"Zone {zone} byte index {byte_index} exceeds data length {len(data)}")
            return False

        # Extract bit value
        byte_value = data[byte_index]
        bit_value = bool(byte_value & (1 << bit_position))
        _LOGGER.debug(f"Zone {zone}: extracted bit {bit_value} from byte {byte_value} bit position {bit_position}")
        return bit_value

    except Exception as e:
        _LOGGER.error(f"Failed to extract zone {zone} bit from bitfield '{base64_data}': {e}")
        return False

def update_zone_value_in_bitfield(base64_data: str, zone: int, new_value: int, bits_per_zone: int = 8) -> str:
    """
    Update zone-specific value in bitfield data.

    Args:
        base64_data: Base64 encoded bitfield data
        zone: Zone number (1-5)
        new_value: New value for the zone (0-255 for 8-bit zones)
        bits_per_zone: Number of bits per zone (default 8)

    Returns:
        Updated Base64 encoded bitfield data
    """
    try:
        # Decode existing data or create new
        if base64_data:
            data = bytearray(decode_base64_to_bytes(base64_data))
        else:
            data = bytearray(5)  # 5 zones = 5 bytes for 8-bit zones

        # Ensure we have enough bytes for the zone
        byte_index = zone - 1
        while len(data) <= byte_index:
            data.append(0)

        # Update the zone value
        data[byte_index] = new_value & 0xFF  # Ensure 8-bit value

        # Encode back to Base64
        result = encode_bytes_to_base64(bytes(data))
        _LOGGER.debug(f"Zone {zone}: updated value to {new_value}, new bitfield: {result}")
        return result

    except Exception as e:
        _LOGGER.error(f"Failed to update zone {zone} value {new_value} in bitfield '{base64_data}': {e}")
        return base64_data or ""

def update_zone_bit_in_bitfield(base64_data: str, zone: int, new_value: bool) -> str:
    """
    Update zone-specific bit in bitfield data.

    Args:
        base64_data: Base64 encoded bitfield data
        zone: Zone number (1-5)
        new_value: New bit value for the zone

    Returns:
        Updated Base64 encoded bitfield data
    """
    try:
        # Decode existing data or create new
        if base64_data:
            data = bytearray(decode_base64_to_bytes(base64_data))
        else:
            data = bytearray(1)  # At least 1 byte for 5 bits

        # Calculate bit position
        bit_index = zone - 1
        byte_index = bit_index // 8
        bit_position = bit_index % 8

        # Ensure we have enough bytes
        while len(data) <= byte_index:
            data.append(0)

        # Update the bit
        if new_value:
            data[byte_index] |= (1 << bit_position)  # Set bit
        else:
            data[byte_index] &= ~(1 << bit_position)  # Clear bit

        # Encode back to Base64
        result = encode_bytes_to_base64(bytes(data))
        _LOGGER.debug(f"Zone {zone}: updated bit to {new_value}, new bitfield: {result}")
        return result

    except Exception as e:
        _LOGGER.error(f"Failed to update zone {zone} bit {new_value} in bitfield '{base64_data}': {e}")
        return base64_data or ""

# Bitfield configuration for IND7705HC data points
BITFIELD_CONFIG = {
    # Value-based bitfields (8 bits per zone)
    162: {  # oem_hob_level_num - Zone power levels
        "type": "value",
        "bits_per_zone": 8,
        "description": "bit0-7 -> hob1, bit8-15 -> hob2, bit16-23 -> hob3, bit24-31 -> hob4, bit32-39 -> hob5"
    },
    167: {  # oem_hob_timer_num - Zone timers
        "type": "value",
        "bits_per_zone": 8,
        "description": "bit0-7 -> hob1, bit8-15 -> hob2, bit16-23 -> hob3, bit24-31 -> hob4, bit32-39 -> hob5"
    },
    168: {  # oem_hob_set_core_sensor - Zone core sensor settings
        "type": "value",
        "bits_per_zone": 8,
        "description": "bit0-7 -> hob1, bit8-15 -> hob2, bit16-23 -> hob3, bit24-31 -> hob4, bit32-39 -> hob5"
    },
    169: {  # oem_hob_disp_coresensor - Zone core sensor display
        "type": "value",
        "bits_per_zone": 8,
        "description": "bit0-7 -> hob1, bit8-15 -> hob2, bit16-23 -> hob3, bit24-31 -> hob4, bit32-39 -> hob5"
    },

    # Bit-based bitfields (1 bit per zone)
    161: {  # oem_hob_selected_switch - Zone selection
        "type": "bit",
        "description": "bit0->hob1 bit1->hob2 bit2->hob3 bit3->hob4 bit4->hob5"
    },
    163: {  # oem_hob_boost_switch - Zone boost status
        "type": "bit",
        "description": "bit0->hob1 bit1->hob2 bit2->hob3 bit3->hob4 bit4->hob5"
    },
    164: {  # oem_hob_warm_switch - Zone keep warm status
        "type": "bit",
        "description": "bit0->hob1 bit1->hob2 bit2->hob3 bit3->hob4 bit4->hob5"
    },
    165: {  # oem_hob_flex_switch - Flex zone status
        "type": "bit",
        "description": "bit0->left bit1->right"
    },
    166: {  # oem_hob_bbq_switch - BBQ mode status
        "type": "bit",
        "description": "bit0->left bit1->right"
    },

    # Special bitfields for errors (boolean states)
    105: {  # oem_hob_error_num - Zone errors
        "type": "bit",
        "description": "bit0->hob1 bit1->hob2 bit2->hob3 bit3->hob4 bit4->hob5"
    },
    106: {  # oem_device_chef_level - Chef function levels
        "type": "value",
        "bits_per_zone": 8,
        "description": "bit0-7 -> hob1, bit8-15 -> hob2, bit16-23 -> hob3, bit24-31 -> hob4, bit32-39 -> hob5"
    },
    107: {  # oem_hob_bbq_timer - BBQ timer
        "type": "value",
        "bits_per_zone": 8,
        "description": "bit0-7 left_bbq, bit8-15 right_bbq"
    }
}

def get_zone_value_from_coordinator(coordinator: Any, dp_id: int, zone: int) -> int | bool:
    """
    Get zone-specific value from coordinator data.

    Args:
        coordinator: KKT Kolbe coordinator instance
        dp_id: Data point ID
        zone: Zone number (1-5)

    Returns:
        Zone-specific value or default
    """
    try:
        # Debug: Log all available data keys
        if coordinator.data:
            available_keys = list(coordinator.data.keys())
            _LOGGER.debug(f"Coordinator data keys: {available_keys}")
        else:
            _LOGGER.debug("Coordinator data is None")

        # Get the DPS dictionary - coordinator may return data with DPs under 'dps' key
        dps_data = coordinator.data.get("dps", coordinator.data)

        # Try both string and integer keys (fix falsy value bug)
        raw_data = dps_data.get(str(dp_id))
        if raw_data is None:
            raw_data = dps_data.get(dp_id)
        if raw_data is None:
            _LOGGER.debug(f"DP {dp_id} not in current update (tried both str and int keys). Zone entities will use cached values.")
            return 0 if BITFIELD_CONFIG.get(dp_id, {}).get("type") == "value" else False

        _LOGGER.debug(f"DP {dp_id} raw data: {raw_data} (type: {type(raw_data)})")

        # Get bitfield configuration
        config = BITFIELD_CONFIG.get(dp_id)
        if not config:
            _LOGGER.warning(f"No bitfield configuration for DP {dp_id}")
            return 0 if isinstance(raw_data, (int, float)) else False

        # Extract zone value based on type
        if config["type"] == "value":
            return extract_zone_value_from_bitfield(str(raw_data), zone, config.get("bits_per_zone", 8))
        elif config["type"] == "bit":
            return extract_zone_bit_from_bitfield(str(raw_data), zone)
        else:
            return 0

    except Exception as e:
        _LOGGER.error(f"Failed to get zone {zone} value for DP {dp_id}: {e}")
        return 0 if BITFIELD_CONFIG.get(dp_id, {}).get("type") == "value" else False

async def set_zone_value_in_coordinator(coordinator: Any, dp_id: int, zone: int, value: int | bool) -> None:
    """
    Set zone-specific value in coordinator data.

    Args:
        coordinator: KKT Kolbe coordinator instance
        dp_id: Data point ID
        zone: Zone number (1-5)
        value: New value for the zone
    """
    try:
        # Get the DPS dictionary - coordinator may return data with DPs under 'dps' key
        dps_data = coordinator.data.get("dps", coordinator.data)

        # Get current raw bitfield data
        current_data = dps_data.get(str(dp_id), "")

        # Get bitfield configuration
        config = BITFIELD_CONFIG.get(dp_id)
        if not config:
            _LOGGER.warning(f"No bitfield configuration for DP {dp_id}")
            return

        # Update bitfield based on type
        if config["type"] == "value":
            new_data = update_zone_value_in_bitfield(str(current_data), zone, int(value), config.get("bits_per_zone", 8))
        elif config["type"] == "bit":
            new_data = update_zone_bit_in_bitfield(str(current_data), zone, bool(value))
        else:
            return

        # Send update to device via coordinator
        await coordinator.async_set_data_point(dp_id, new_data)
        _LOGGER.info(f"Set zone {zone} DP {dp_id} to {value}, new bitfield: {new_data}")

    except Exception as e:
        _LOGGER.error(f"Failed to set zone {zone} value {value} for DP {dp_id}: {e}")