from __future__ import annotations

from typing import Dict
from pupil_labs.realtime_api.device import Device

from gazedeck.core.device_discovery import discover_devices_indexed
from gazedeck.core.device_labeling import LabeledDevice, label_devices
from gazedeck.cli.prompt_device_labeling import ask_label_cli


async def run_cli_discovery_and_label(duration: float = 3.0) -> Dict[int, LabeledDevice]:
    """
    Discover devices for `duration` seconds, prompt labels (blank=skip),
    and store labeled devices into global process state.
    """
    devices: Dict[int, Device] = await discover_devices_indexed(duration)

    if not devices:
        print("No devices found.")
        return {}

    labeled = await label_devices(devices, ask_label_cli)

    if labeled:
        print("Labeled devices:")
        for idx, ld in labeled.items():
            print(f"  [{idx}] {ld.label} -> {ld.name} ({ld.ip})")
    else:
        print("No devices labeled (nothing stored).")

    return labeled
