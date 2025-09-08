# gazedeck/core/binary_messages.py

"""
Binary message serialization for high-performance WebSocket communication.

Design:
- ArrayBuffer format: [device_id:int32, surface_id:int32, x:float32, y:float32, timestamp:float64]
- NaN values indicate invalid/missing surface detection
- Zero-copy serialization for maximum throughput
"""

import struct
import math
from typing import Tuple
from datetime import datetime

# Message format constants
MESSAGE_FORMAT = 'iiffd'  # device_id, surface_id, x, y, timestamp
MESSAGE_SIZE = struct.calcsize(MESSAGE_FORMAT)


def serialize_gaze_message(
    device_id: int,
    surface_id: int,
    x: float,
    y: float,
    timestamp: datetime
) -> bytes:
    """
    Serialize gaze data to binary format.

    Uses NaN for invalid/missing surface detection to maintain mathematical
    correctness while minimizing message size.

    Args:
        device_id: Integer device identifier (stable across sessions)
        surface_id: Integer surface identifier (stable across sessions)
        x: X coordinate (0.0-1.0 normalized, or NaN if invalid)
        y: Y coordinate (0.0-1.0 normalized, or NaN if invalid)
        timestamp: Gaze timestamp

    Returns:
        Binary message bytes (24 bytes total)
    """
    return struct.pack(
        MESSAGE_FORMAT,
        device_id,
        surface_id,
        x,
        y,
        timestamp.timestamp()  # Convert to Unix timestamp (float64)
    )


def is_valid_coordinates(x: float, y: float) -> bool:
    """
    Check if coordinates are valid (not NaN).

    This is the client-side equivalent check for determining if
    surface detection was successful.

    Args:
        x: X coordinate value
        y: Y coordinate value

    Returns:
        True if coordinates are valid numbers, False if NaN/invalid
    """
    return not (math.isnan(x) or math.isnan(y))


def deserialize_gaze_message(buffer: bytes) -> Tuple[int, int, float, float, datetime]:
    """
    Deserialize binary gaze message (primarily for testing/debugging).

    Args:
        buffer: Binary message bytes

    Returns:
        Tuple of (device_id, surface_id, x, y, timestamp)
    """
    device_id, surface_id, x, y, timestamp_unix = struct.unpack(MESSAGE_FORMAT, buffer)
    return device_id, surface_id, x, y, datetime.fromtimestamp(timestamp_unix)
