# gazedeck/cli/setup_labeled_devices.py

from __future__ import annotations

from typing import Dict
from pupil_labs.realtime_api.device import Device

from gazedeck.core.device_discovery import discover_devices_indexed
from gazedeck.core.device_labeling import LabeledDevice, label_devices
from gazedeck.cli.prompt_device_labeling import ask_label_cli


async def setup_labeled_devices_cli(duration: float = 3.0) -> Dict[int, LabeledDevice]:
    """
    Discover devices for `duration` seconds, prompt labels (blank=skip),
    and return labeled devices.
    """
    print(f"🔍 Discovering devices for {duration}s...")
    devices: Dict[int, Device] = await discover_devices_indexed(duration)

    if not devices:
        print("❌ No devices found.")
        print("   Make sure Pupil Labs devices are powered on and connected to the same network.")
        return {}

    labeled = await label_devices(devices, ask_label_cli)

    if labeled:
        print("Labeled devices:")
        for idx, ld in labeled.items():
            print(f"  [{idx}] {ld.label} -> {ld.name} ({ld.ip})")
    else:
        print("ℹ️  No devices labeled. This is normal if you pressed Enter/Return to skip labeling.")
        print("   Labeled devices will be saved automatically for future use.")

    return labeled
