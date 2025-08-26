"""Pupil Labs device provider for shared device management."""

import asyncio
import logging
from typing import Optional

try:
    from pupil_labs_realtime_api import Device, Network
except ImportError:
    Device = None
    Network = None

from ...ports.device_provider import IDeviceProvider, SensorURLs

logger = logging.getLogger(__name__)


class PupilLabsDeviceProvider(IDeviceProvider):
    """Shared device provider for Pupil Labs devices."""

    def __init__(self, discovery_timeout: float = 10.0):
        """Initialize device provider.

        Args:
            discovery_timeout: Timeout for device discovery in seconds
        """
        if Device is None or Network is None:
            raise ImportError("pupil-labs-realtime-api package is required")

        self._discovery_timeout = discovery_timeout
        self._device: Optional[Device] = None
        self._sensor_urls: Optional[SensorURLs] = None
        self._lock = asyncio.Lock()

    async def get_sensor_urls(self) -> SensorURLs:
        """Get sensor URLs, discovering device if necessary.

        Returns:
            SensorURLs containing gaze and world sensor URLs

        Raises:
            RuntimeError: If no device found or sensors not connected
        """
        async with self._lock:
            if self._sensor_urls is None:
                await self._discover_device()
            return self._sensor_urls

    async def _discover_device(self) -> None:
        """Discover Pupil Labs device and get sensor URLs."""
        logger.info("Discovering Pupil Labs device...")

        try:
            async with Network() as network:
                device_info = await network.wait_for_new_device(
                    timeout_seconds=self._discovery_timeout
                )

                if device_info is None:
                    raise RuntimeError("No Pupil Labs device found on network")

                logger.info(f"Found device: {device_info.name} at {device_info.address}")

                # Create device instance and get sensor URLs
                device = Device.from_discovered_device(device_info)
                await device.__aenter__()

                try:
                    status = await device.get_status()
                    gaze_sensor = status.direct_gaze_sensor()
                    world_sensor = status.direct_world_sensor()

                    if not gaze_sensor.connected:
                        raise RuntimeError("Gaze sensor is not connected")
                    if not world_sensor.connected:
                        raise RuntimeError("World sensor is not connected")

                    self._device = device
                    self._sensor_urls = SensorURLs(
                        gaze_url=gaze_sensor.url,
                        world_url=world_sensor.url,
                        device_name=device_info.name,
                        device_address=device_info.address,
                    )

                    logger.info(f"Gaze sensor URL: {self._sensor_urls.gaze_url}")
                    logger.info(f"World sensor URL: {self._sensor_urls.world_url}")

                except Exception:
                    await device.__aexit__(None, None, None)
                    raise

        except Exception as e:
            logger.error(f"Failed to discover Pupil Labs device: {e}")
            raise

    async def close(self) -> None:
        """Close device connection."""
        async with self._lock:
            if self._device is not None:
                await self._device.__aexit__(None, None, None)
                self._device = None
                self._sensor_urls = None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
