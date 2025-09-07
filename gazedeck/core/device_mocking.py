# gazedeck/core/device_mocking.py

"""
Mock gaze tracker that simulates cursor position tracking at 200 Hz.

Design:
- Tracks mouse cursor position with random noise (±20px)
- Emits normalized coordinates (0.0-1.0) to all labeled surfaces at 200 Hz (5ms intervals)
- Position updates are triggered by left mouse clicks
- Integrates with existing WebSocket broadcasting system
- Thread-safe and runs asynchronously

Coordinates: Normalized to surface bounds (0.0 = top/left edge, 1.0 = bottom/right edge)
Requires: pynput (pip install pynput)
"""

from __future__ import annotations

import asyncio
import json
import random
import threading
from datetime import datetime
from typing import Dict, Optional, Iterable

from pynput import mouse
from pynput.mouse import Button

from gazedeck.core.websocket_server import broadcast_nowait
from gazedeck.core.surface_layout_labeling import SurfaceLayoutLabeled


class MockTracker:
    """
    Mock gaze tracker that simulates high-frequency cursor tracking.

    Tracks mouse position and emits gaze data with configurable noise
    to all registered surfaces at configurable frequency.
    """

    def __init__(self, noise_level: float = 20.0, device_label: str = "mock_tracker", frequency: float = 200.0):
        """
        Initialize the mock tracker.

        Args:
            noise_level: Maximum random noise in pixels (±noise_level)
            device_label: Label for this mock device
            frequency: Tracking frequency in Hz (default: 200.0)
        """
        self.noise_level = noise_level
        self.frequency = frequency
        self.sleep_interval = 1.0 / frequency if frequency > 0 else 0.005
        self.current_position = (0.0, 0.0)
        self.surfaces: Dict[str, SurfaceLayoutLabeled] = {}
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
        self.surfaces[surface.label] = surface
        print(f"📋 Mock tracker: Added surface '{surface.label}' ({surface.size[0]}x{surface.size[1]})")

    def remove_surface(self, surface_label: str) -> None:
        """
        Remove a surface from tracking.

        Args:
            surface_label: Label of surface to remove
        """
        if surface_label in self.surfaces:
            del self.surfaces[surface_label]
            print(f"📋 Mock tracker: Removed surface '{surface_label}'")

    def _on_mouse_click(self, x: float, y: float, button: Button, pressed: bool) -> None:
        """
        Handle mouse click events to update tracked position.

        Args:
            x, y: Mouse coordinates
            button: Mouse button pressed
            pressed: True if pressed, False if released
        """
        if button == Button.left and pressed:
            with self._position_lock:
                self.current_position = (float(x), float(y))
                print(f"🖱️ Mock tracker: Position updated to ({x:.1f}, {y:.1f})")

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

        print("🎯 Mock tracker started - click left mouse button to set gaze position")
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

        if self._mouse_listener:
            self._mouse_listener.stop()

        print("🛑 Mock tracker stopped")

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
        timestamp = datetime.now()

        # Create surface gaze data with noise
        surface_gaze = {}
        for surface_label, surface in self.surfaces.items():
            # Add random noise (±noise_level pixels)
            noise_x = random.uniform(-self.noise_level, self.noise_level)
            noise_y = random.uniform(-self.noise_level, self.noise_level)

            # Apply noise to position
            gaze_x = base_x + noise_x
            gaze_y = base_y + noise_y

            # Check if gaze is within surface bounds
            is_on_surface = (
                0 <= gaze_x <= surface.size[0] and
                0 <= gaze_y <= surface.size[1]
            )

            if is_on_surface:
                # Normalize coordinates to 0.0-1.0 range
                normalized_x = gaze_x / surface.size[0] if surface.size[0] > 0 else 0.0
                normalized_y = gaze_y / surface.size[1] if surface.size[1] > 0 else 0.0

                surface_gaze[surface_label] = {
                    "x": normalized_x,
                    "y": normalized_y,
                    "is_on_surface": True
                }
            else:
                # Output null when gaze is not on surface (matches real stream behavior)
                surface_gaze[surface_label] = None

        # Create message in same format as real gaze data
        message = {
            "timestamp": timestamp.isoformat(),
            "device": self.device_label,
            "surface_gaze": surface_gaze
        }

        # Broadcast via WebSocket
        broadcast_nowait(json.dumps(message))


# Global instance for easy access
_mock_tracker: Optional[MockTracker] = None


def get_mock_tracker(noise_level: float = 20.0, device_label: str = "mock_tracker", frequency: float = 200.0) -> MockTracker:
    """
    Get or create the global mock tracker instance.

    Args:
        noise_level: Maximum random noise in pixels (±noise_level)
        device_label: Label for this mock device
        frequency: Tracking frequency in Hz (default: 200.0)

    Returns:
        MockTracker instance
    """
    global _mock_tracker
    if _mock_tracker is None:
        _mock_tracker = MockTracker(noise_level, device_label, frequency)
    return _mock_tracker


async def start_mock_tracking(surfaces: Dict[str, SurfaceLayoutLabeled] | Iterable[SurfaceLayoutLabeled],
                            noise_level: float = 20.0,
                            device_label: str = "mock_tracker",
                            frequency: float = 200.0) -> MockTracker:
    """
    Convenience function to start mock tracking for given surfaces.

    Args:
        surfaces: Dictionary of surface_label -> SurfaceLayoutLabeled or iterable of SurfaceLayoutLabeled
        noise_level: Maximum random noise in pixels (±noise_level)
        device_label: Label for this mock device
        frequency: Tracking frequency in Hz (default: 200.0)

    Returns:
        MockTracker instance (already started)
    """
    tracker = get_mock_tracker(noise_level, device_label, frequency)

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


async def stop_mock_tracking() -> None:
    """
    Convenience function to stop global mock tracking.
    """
    global _mock_tracker
    if _mock_tracker:
        await _mock_tracker.stop_tracking()
        _mock_tracker = None
