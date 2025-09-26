# gazedeck/cli/prompt_device_labeling.py

import asyncio
from typing import Optional
from pupil_labs.realtime_api.device import Device

async def _describe(dev: Device) -> str:
    """
    Create a detailed description of the device using its status information.
    Returns device name, IP, battery level, hardware serials, and sensor status.
    """
    try:
        # Get comprehensive device status with timeout to prevent hanging
        status = await asyncio.wait_for(dev.get_status(), timeout=5.0)

        # Basic identification
        device_name = status.phone.device_name or "Unknown Device"
        ip = status.phone.ip
        battery = status.phone.battery_level

        # Hardware information
        glasses_sn = status.hardware.glasses_serial
        world_camera_sn = status.hardware.world_camera_serial
        module_sn = status.hardware.module_serial

        # Sensor status
        world_sensor = status.direct_world_sensor()
        gaze_sensor = status.direct_gaze_sensor()

        # Build description parts
        parts = [f"{device_name}"]

        # Add IP and battery
        if ip:
            parts.append(f"IP: {ip}")
        if battery is not None:
            parts.append(f"Battery: {battery}%")

        # Add hardware serials if available
        hw_info = []
        if glasses_sn and glasses_sn != "-1":
            hw_info.append(f"Glasses: {glasses_sn}")
        if world_camera_sn and world_camera_sn != "-1":
            hw_info.append(f"World Cam: {world_camera_sn}")
        if module_sn:
            hw_info.append(f"Module: {module_sn}")
        if hw_info:
            parts.append(" | ".join(hw_info))

        # Add sensor status
        sensor_info = []
        if world_sensor:
            sensor_info.append(f"World: {'✓' if world_sensor.connected else '✗'}")
        if gaze_sensor:
            sensor_info.append(f"Gaze: {'✓' if gaze_sensor.connected else '✗'}")
        if sensor_info:
            parts.append("Sensors: " + ", ".join(sensor_info))

        return " | ".join(parts)

    except asyncio.TimeoutError:
        # Device didn't respond within timeout - likely not running Pupil software
        host = getattr(dev, "dns_name", None) or getattr(dev, "address", None) or "device"
        port = getattr(dev, "port", None)
        name = getattr(dev, "full_name", None)
        if name:
            return f"{name} ({host}:{port}) - [WARN] Device not responding"
        return f"{host}:{port} - [WARN] Device not responding"
    except Exception as e:
        # Other error - fallback to basic description
        host = getattr(dev, "dns_name", None) or getattr(dev, "address", None) or "device"
        port = getattr(dev, "port", None)
        name = getattr(dev, "full_name", None)
        if name:
            return f"{name} ({host}:{port}) - [WARN] Status unavailable"
        return f"{host}:{port} - [WARN] Status unavailable"

async def ask_label_cli(idx: int, dev: Device) -> Optional[str]:
    """
    Return label from stdin; blank → skip.
    Uses a thread to avoid blocking the asyncio loop.

    This is indented to be used with the label_devices function in gazedeck/core/device_labeling.py
    """
    # Get detailed device description
    description = await _describe(dev)

    def _prompt() -> str:
        try:
            import sys

            # Check if we have a TTY (interactive terminal)
            if not sys.stdin.isatty():
                print(f"[WARN] Non-interactive terminal detected for device {idx}, auto-skipping...")
                return ""

            # Simple input with basic timeout handling
            try:
                result = input(f"Label for device {idx} [{description}] (blank=skip): ")
                return result.strip()  # Strip whitespace from input
            except (EOFError, KeyboardInterrupt):
                print(f"\n[ERR] Input interrupted for device {idx}, skipping...")
                return ""

        except Exception as e:
            print(f"\n[ERR] Error getting input for device {idx}: {e}, skipping...")
            return ""

    try:
        return await asyncio.wait_for(asyncio.to_thread(_prompt), timeout=30.0)
    except asyncio.TimeoutError:
        print(f"\n⏰ Async timeout for device {idx}, skipping...")
        return ""
