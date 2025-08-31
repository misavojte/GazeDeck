# gazedeck/core/device_discovery.py
from __future__ import annotations

import asyncio
from typing import Dict

from pupil_labs.realtime_api.discovery import Network
from pupil_labs.realtime_api.device import Device


async def discover_devices_indexed(duration: float = 3.0) -> Dict[int, Device]:
    """
    Scan for `duration` seconds and return a dict mapping discovery index -> Device.

    Notes:
        - Index order reflects the snapshot order at the end of the scan window.
        - Caller is responsible for closing devices (e.g., `await dev.close()` or `async with dev:`).
    """
    async with Network() as network:
        print(f"Scanning for {duration} seconds...")
        await asyncio.sleep(duration)
        return {
            i: Device.from_discovered_device(info)
            for i, info in enumerate(network.devices)
        }
