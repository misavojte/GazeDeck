#!/usr/bin/env python3

from pupil_labs.realtime_api.simple import discover_one_device

def discover_device():
    """Discover and return the Pupil Labs device."""
    print("Discovering device...")
    device = discover_one_device()
    return device

def get_calibration(device):
    """Get calibration data from the device."""
    print("Getting calibration...")
    calibration = device.get_calibration()
    return calibration

def close_device(device):
    """Close the device connection."""
    try:
        if device:
            device.close()
            print("Device connection closed successfully")
    except Exception as e:
        print(f"Error during device cleanup: {e}")

class DeviceManager:
    """Manages Pupil Labs device discovery, calibration, and cleanup."""

    def __init__(self):
        self.device = None
        self.calibration = None

    def initialize(self):
        """Initialize device and get calibration."""
        self.device = discover_device()
        self.calibration = get_calibration(self.device)
        return self.device, self.calibration

    def cleanup(self):
        """Clean up device connection."""
        close_device(self.device)

    def __enter__(self):
        """Context manager entry."""
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()
