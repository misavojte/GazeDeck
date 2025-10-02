# gazedeck/cli/setup_labeled_devices.py

from __future__ import annotations

from typing import Dict
from pupil_labs.realtime_api.device import Device

from gazedeck.core.device_discovery import discover_devices_indexed
from gazedeck.core.device_labeling import LabeledDevice, label_devices
from gazedeck.cli.prompt_device_labeling import ask_label_cli


async def setup_labeled_devices_cli(duration: float = 3.0, device_ips: List[str] = None) -> Dict[int, LabeledDevice]:
    """
    Discover devices for `duration` seconds, prompt labels (blank=skip),
    and return labeled devices.

    Args:
        duration: Time in seconds for discovery (mDNS mode) or connection timeout (manual mode)
        device_ips: Optional list of IP addresses for direct connection
    """
    if device_ips:
        print(f"[DIRECT] Connecting directly to IP addresses: {device_ips}")
    else:
        print(f"[SEARCH] Discovering devices for {duration}s...")

    devices: Dict[int, Device] = await discover_devices_indexed(duration, device_ips)

    if not devices:
        if device_ips:
            print(f"[ERR] No devices found at specified IP addresses: {device_ips}")
            print("   Make sure the IP addresses are correct and devices are powered on.")
        else:
            print("[ERR] No devices found.")
            print("   Make sure Pupil Labs devices are powered on and connected to the same network.")
            print("   If you are using a multi-NIC host, please use the --device-ips flag to specify the IP addresses of the devices.")
        return {}

    labeled = await label_devices(devices, ask_label_cli)

    if labeled:
        print("[INIT] Labeled devices:")
        for idx, ld in labeled.items():
            print(f"  [{idx}] {ld.label} -> {ld.name} ({ld.ip})")
    else:
        print("[ERR] No devices labeled. This is normal if you pressed Enter/Return to skip labeling.")

    return labeled
