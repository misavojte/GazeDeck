# gazedeck/core/device_mocking.py

"""
Mock gaze tracker that simulates cursor position tracking at 200 Hz.

Design:
- Tracks mouse cursor position with random noise (±20px)
- Emits normalized coordinates to all labeled surfaces at 200 Hz (5ms intervals)
- Position updates are triggered by left mouse clicks
- Integrates with existing WebSocket broadcasting system
- Thread-safe and runs asynchronously

Coordinates: Normalized to surface bounds (0.0 = top/left edge, 1.0 = bottom/right edge)
- Values can be outside 0.0-1.0 range when gaze is outside surface bounds
- Always includes coordinate data regardless of surface bounds
Requires: pynput (pip install pynput)
"""

from __future__ import annotations

import asyncio
import random
import threading
import time
from typing import Dict, Optional, Iterable

from pynput import mouse
from pynput.mouse import Button

# Mouse button mapping for multiple devices
MOUSE_BUTTONS = {
    0: Button.left,
    1: Button.right,
    2: Button.middle  # mousewheel click
}

from gazedeck.core.websocket_server import broadcast_nowait
from gazedeck.core.surface_layout_labeling import SurfaceLayoutLabeled


class MockTracker:
    """
    Mock gaze tracker that simulates high-frequency cursor tracking.

    Tracks mouse position and emits gaze data with configurable noise
    to all registered surfaces at configurable frequency.
    """

    def __init__(self, noise_level: float = 20.0, device_label: str = "mock_tracker", frequency: float = 200.0, device_index: int = 0):
        """
        Initialize the mock tracker.

        Args:
            noise_level: Maximum random noise in pixels (±noise_level)
            device_label: Label for this mock device
            frequency: Tracking frequency in Hz (default: 200.0)
            device_index: Index of this device (0=left, 1=right, 2=middle mouse button)
        """
        self.noise_level = noise_level
        self.frequency = frequency
        self.sleep_interval = 1.0 / frequency if frequency > 0 else 0.005
        self.device_index = device_index
        self.mouse_button = MOUSE_BUTTONS.get(device_index, Button.left)
        self.current_position = (0.0, 0.0)
        self.surfaces: Dict[int, SurfaceLayoutLabeled] = {}
        self.device_label = device_label
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._mouse_listener = None

        # Mouse position tracking
        self._mouse_controller = mouse.Controller()

        # Threading lock for position updates
        self._position_lock = threading.Lock()

    def add_surface(self, surface: SurfaceLayoutLabeled) -> None:
        """
        Register a surface to receive mock gaze data.

        Args:
            surface: Labeled surface layout to track
        """
        self.surfaces[surface.emission_id] = surface
        print(f"📋 Mock tracker: Added surface '{surface.emission_id} {surface.label}' ({surface.size[0]}x{surface.size[1]})")

    def remove_surface(self, surface_emission_id: int) -> None:
        """
        Remove a surface from tracking.

        Args:
            surface_emission_id: Emission ID of surface to remove
        """
        if surface_emission_id in self.surfaces:
            surface = self.surfaces[surface_emission_id]
            del self.surfaces[surface_emission_id]
            print(f"📋 Mock tracker: Removed surface '{surface_emission_id} {surface.label}'")

    def _on_mouse_click(self, x: float, y: float, button: Button, pressed: bool) -> None:
        """
        Handle mouse click events to update tracked position.

        Args:
            x, y: Mouse coordinates
            button: Mouse button pressed
            pressed: True if pressed, False if released
        """
        if button == self.mouse_button and pressed:
            with self._position_lock:
                self.current_position = (float(x), float(y))
                button_name = {Button.left: "left", Button.right: "right", Button.middle: "middle"}.get(button, "unknown")
                print(f"🖱️ Mock tracker {self.device_index} ({self.device_label}): Position updated to ({x:.1f}, {y:.1f}) via {button_name} click")

    async def start_tracking(self) -> None:
        """
        Start the mock tracking loop.

        Begins mouse listener and starts emitting gaze data at configured frequency.
        """
        if self._running:
            print("⚠️ Mock tracker already running")
            return

        self._running = True

        # Start mouse listener in background thread
        self._mouse_listener = mouse.Listener(on_click=self._on_mouse_click)
        self._mouse_listener.start()

        button_name = {Button.left: "left", Button.right: "right", Button.middle: "middle"}.get(self.mouse_button, "unknown")
        print(f"🎯 Mock tracker {self.device_index} ({self.device_label}) started - click {button_name} mouse button to set gaze position")
        print(f"📊 Tracking {len(self.surfaces)} surfaces at {self.frequency} Hz with ±{self.noise_level}px noise")

        # Start the tracking loop
        self._task = asyncio.create_task(self._tracking_loop())

    async def stop_tracking(self) -> None:
        """
        Stop the mock tracking loop and cleanup resources.
        """
        if not self._running:
            return

        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None  # Clear reference

        if self._mouse_listener:
            self._mouse_listener.stop()
            self._mouse_listener = None  # Clear reference

        self.surfaces.clear()  # Clear surface references

        print("🛑 Mock tracker stopped and cleaned up")

    async def _tracking_loop(self) -> None:
        """
        Main tracking loop that emits gaze data at configured frequency.
        """
        try:
            while self._running:
                await self._emit_gaze_data()
                await asyncio.sleep(self.sleep_interval)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"❌ Mock tracker error: {e}")
            raise

    async def _emit_gaze_data(self) -> None:
        """
        Generate and emit mock gaze data for all registered surfaces.
        """
        if not self.surfaces:
            return

        # Get current position with thread safety
        with self._position_lock:
            base_x, base_y = self.current_position

        # Generate timestamp
        timestamp = time.time()

        # Create surface gaze data with noise
        surface_gaze = {}
        for surface_emission_id, surface in self.surfaces.items():
            # Add random noise (±noise_level pixels)
            noise_x = random.uniform(-self.noise_level, self.noise_level)
            noise_y = random.uniform(-self.noise_level, self.noise_level)

            # Apply noise to position
            gaze_x = base_x + noise_x
            gaze_y = base_y + noise_y

            # Always normalize coordinates (can be outside 0-1 range)
            normalized_x = gaze_x / surface.size[0] if surface.size[0] > 0 else 0.0
            normalized_y = gaze_y / surface.size[1] if surface.size[1] > 0 else 0.0

            surface_gaze[surface_emission_id] = {
                "x": normalized_x,
                "y": normalized_y
            }

        # Broadcast binary messages - one per surface (not nested JSON)
        from .websocket_server import broadcast_gaze_data

        # Use emission_id for WebSocket transmission (no runtime int conversion needed)
        device_id = self.device_index  # device_index is already the emission_id equivalent for mock devices

        # Send one binary message per surface
        for surface_emission_id, surface_result in surface_gaze.items():
            # surface_emission_id is already an integer, no conversion needed
            surface_id = surface_emission_id

            # Always include coordinates (can be outside 0-1 range)
            x, y = surface_result["x"], surface_result["y"]

            # Binary serialization - massively more efficient than JSON
            broadcast_gaze_data(device_id, surface_id, x, y, timestamp)

    def config_matches(self, noise_level, device_label, frequency, device_index) -> bool:
        return (self.noise_level == noise_level and
                self.device_label == device_label and
                self.frequency == frequency and
                self.device_index == device_index)


# Global instances for multiple trackers
_mock_trackers: Dict[int, MockTracker] = {}


def get_mock_tracker(noise_level: float = 20.0, device_label: str = "mock_tracker", frequency: float = 200.0, device_index: int = 0) -> MockTracker:
    """
    Get or create a mock tracker instance for the specified device index.

    Args:
        noise_level: Maximum random noise in pixels (±noise_level)
        device_label: Label for this mock device
        frequency: Tracking frequency in Hz (default: 200.0)
        device_index: Index of this device (0=left, 1=right, 2=middle mouse button)

    Returns:
        MockTracker instance
    """
    global _mock_trackers
    if device_index in _mock_trackers:
        existing = _mock_trackers[device_index]
        if existing.config_matches(noise_level, device_label, frequency, device_index):
            return existing
        else:
            # Stop and remove old tracker with different config
            asyncio.run(existing.stop_tracking()) # Use asyncio.run to await cancellation
            del _mock_trackers[device_index]

    # Create new tracker with correct config
    _mock_trackers[device_index] = MockTracker(noise_level, device_label, frequency, device_index)
    return _mock_trackers[device_index]


async def start_mock_tracking(surfaces: Dict[int, SurfaceLayoutLabeled] | Iterable[SurfaceLayoutLabeled],
                            noise_level: float = 20.0,
                            device_label: str = "mock_tracker",
                            frequency: float = 200.0,
                            device_index: int = 0) -> MockTracker:
    """
    Convenience function to start mock tracking for given surfaces.

    Args:
        surfaces: Dictionary of surface_emission_id -> SurfaceLayoutLabeled or iterable of SurfaceLayoutLabeled
        noise_level: Maximum random noise in pixels (±noise_level)
        device_label: Label for this mock device
        frequency: Tracking frequency in Hz (default: 200.0)
        device_index: Index of this device (0=left, 1=right, 2=middle mouse button)

    Returns:
        MockTracker instance (already started)
    """
    tracker = get_mock_tracker(noise_level, device_label, frequency, device_index)

    # Add all surfaces - handle both dict and iterable
    if isinstance(surfaces, dict):
        for surface in surfaces.values():
            tracker.add_surface(surface)
    else:
        for surface in surfaces:
            tracker.add_surface(surface)

    # Start tracking
    await tracker.start_tracking()

    return tracker


async def stop_mock_tracking(device_index: Optional[int] = None) -> None:
    """
    Convenience function to stop mock tracking.

    Args:
        device_index: Index of specific device to stop, or None to stop all
    """
    global _mock_trackers
    if device_index is not None:
        if device_index in _mock_trackers:
            await _mock_trackers[device_index].stop_tracking()
            del _mock_trackers[device_index]
    else:
        # Stop all trackers
        for tracker in list(_mock_trackers.values()):
            await tracker.stop_tracking()
        _mock_trackers.clear()


def get_active_mock_devices() -> list[int]:
    """
    Get list of active mock device indices.

    Returns:
        List of device indices that are currently active
    """
    global _mock_trackers
    return list(_mock_trackers.keys())
