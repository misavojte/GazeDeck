"""Device provider interface for managing device discovery and connections."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol


@dataclass
class SensorURLs:
    """Container for sensor URLs."""
    gaze_url: str
    world_url: str
    device_name: str
    device_address: str


class IDeviceProvider(ABC):
    """Abstract interface for device providers."""

    @abstractmethod
    async def get_sensor_urls(self) -> SensorURLs:
        """Get sensor URLs, discovering device if necessary.

        Returns:
            SensorURLs containing gaze and world sensor URLs

        Raises:
            RuntimeError: If no device found or sensors not connected
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close device connection and cleanup resources."""
        ...
