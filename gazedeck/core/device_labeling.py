# gazedeck/core/device_labeling.py

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, Optional
from pupil_labs.realtime_api.device import Device, Calibration


@dataclass(frozen=True)
class LabeledDevice:
    """
    Simple value object combining a user-defined label with a Device instance.

    Notes:
        - Other methods and properties are available on the Device instance (see Pupil Labs Realtime ASYNC API documentation).
    """
    label: str
    device: Device
    camera_calibration: Calibration # not an eye-tracking calibration! this is used to correct the distortion of the FPV camera


async def label_devices(
    devices: Dict[int, Device],
    ask_label: Callable[[int, Device], Awaitable[Optional[str]]],
) -> Dict[int, LabeledDevice]:
    """
    Ask the UI layer for labels per device; return only those that were labeled.

    Args:
        devices: {index -> Device} from discovery.
        ask_label: async function supplied by CLI/GUI that returns a label string
                   (or None / '' to skip this device).

    Returns:
        {index -> LabeledDevice} containing only labeled entries.
    """
    labeled: Dict[int, LabeledDevice] = {}
    for idx, dev in devices.items():
        raw = await ask_label(idx, dev)
        label = (raw or "").strip()
        if label:  # skip if user left it blank / None
            labeled[idx] = LabeledDevice(label=label, device=dev)
            # get the calibration of the camera (THIS IS AVAILABLE ONLY FOR NEON DEVICES)
            # this is not the eye tracking calibration! this is used to correct the distortion of the FPV camera
            camera_calibration = await dev.get_calibration()
            # if not available, raise an error immediately
            if camera_calibration is None:
                raise ValueError("Camera calibration is not available for this device. Please check if the device is a Neon device.")
            labeled[idx].camera_calibration = camera_calibration

    return labeled
