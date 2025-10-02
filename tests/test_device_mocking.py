"""
Unit tests for the simplified device mocking functionality.

Tests the MockTracker class to ensure it:
- Updates position only on mouse clicks
- Reuses the same position until next click
- Emits gaze data correctly with noise
- Handles surface registration/removal properly
"""

import asyncio
import time
import unittest
from unittest.mock import Mock, MagicMock

from gazedeck.core.device_mocking import MockTracker
from gazedeck.core.surface_layout_labeling import SurfaceLayoutLabeled


class TestMockTracker(unittest.IsolatedAsyncioTestCase):
    """Test cases for the simplified MockTracker implementation."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_ws_server = Mock()
        self.mock_shutdown_event = Mock()
        self.mock_shutdown_event.is_set.return_value = False

        # Create a mock surface
        self.mock_surface = Mock(spec=SurfaceLayoutLabeled)
        self.mock_surface.emission_id = 1
        self.mock_surface.label = "test_surface"
        self.mock_surface.size = (1920, 1080)

    def test_initialization(self):
        """Test that MockTracker initializes correctly."""
        tracker = MockTracker(
            noise_level=10.0,
            device_label="test_tracker",
            frequency=100.0,
            device_index=0,
            ws_server=self.mock_ws_server,
            shutdown_event=self.mock_shutdown_event
        )

        self.assertEqual(tracker.noise_level, 10.0)
        self.assertEqual(tracker.device_label, "test_tracker")
        self.assertEqual(tracker.frequency, 100.0)
        self.assertEqual(tracker.device_index, 0)
        self.assertEqual(tracker.current_position, (0.0, 0.0))
        self.assertFalse(tracker._running)

    def test_add_surface(self):
        """Test adding a surface to the tracker."""
        tracker = MockTracker()
        tracker.add_surface(self.mock_surface)

        self.assertIn(1, tracker.surfaces)
        self.assertEqual(tracker.surfaces[1], self.mock_surface)

    def test_remove_surface(self):
        """Test removing a surface from the tracker."""
        tracker = MockTracker()
        tracker.add_surface(self.mock_surface)
        self.assertIn(1, tracker.surfaces)

        tracker.remove_surface(1)
        self.assertNotIn(1, tracker.surfaces)

    def test_remove_nonexistent_surface(self):
        """Test removing a surface that doesn't exist."""
        tracker = MockTracker()
        # Should not raise an exception
        tracker.remove_surface(999)

    async def test_mouse_click_updates_position(self):
        """Test that mouse clicks update the current position."""
        tracker = MockTracker()

        # Simulate a mouse click at position (100, 200)
        tracker._on_mouse_click(100.0, 200.0, tracker.mouse_button, True)

        self.assertEqual(tracker.current_position, (100.0, 200.0))

    async def test_mouse_click_only_updates_on_press(self):
        """Test that position only updates on mouse press, not release."""
        tracker = MockTracker()
        tracker._on_mouse_click(100.0, 200.0, tracker.mouse_button, True)
        self.assertEqual(tracker.current_position, (100.0, 200.0))

        # Release should not change position
        tracker._on_mouse_click(100.0, 200.0, tracker.mouse_button, False)
        self.assertEqual(tracker.current_position, (100.0, 200.0))

    async def test_mouse_click_only_updates_with_correct_button(self):
        """Test that only the correct mouse button updates position."""
        # Create tracker for right mouse button (device_index=1)
        tracker = MockTracker(device_index=1)

        # Left click should not update position
        tracker._on_mouse_click(100.0, 200.0, Mock(), True)  # Wrong button
        self.assertEqual(tracker.current_position, (0.0, 0.0))

        # Right click should update position
        from pynput.mouse import Button
        tracker._on_mouse_click(100.0, 200.0, Button.right, True)
        self.assertEqual(tracker.current_position, (100.0, 200.0))

    async def test_emit_gaze_data_without_surfaces(self):
        """Test that emit_gaze_data handles empty surfaces gracefully."""
        tracker = MockTracker(ws_server=self.mock_ws_server)
        tracker.current_position = (100.0, 200.0)

        # Should not raise an exception or call ws_server
        await tracker._emit_gaze_data()
        self.mock_ws_server.broadcast_gaze_data.assert_not_called()

    async def test_emit_gaze_data_with_noise(self):
        """Test that gaze data is emitted with proper noise and normalization."""
        tracker = MockTracker(
            noise_level=5.0,
            ws_server=self.mock_ws_server
        )
        tracker.add_surface(self.mock_surface)
        tracker.current_position = (960.0, 540.0)  # Center of 1920x1080

        # Mock random to return predictable values
        import random
        original_uniform = random.uniform
        random.uniform = Mock(side_effect=[2.0, 3.0])  # Add 2px noise to x, 3px to y

        try:
            await tracker._emit_gaze_data()

            # Verify that broadcast_gaze_data was called
            self.mock_ws_server.broadcast_gaze_data.assert_called_once()
            call_args = self.mock_ws_server.broadcast_gaze_data.call_args

            device_id, surface_id, x, y, timestamp = call_args[0]

            self.assertEqual(device_id, 0)  # device_index
            self.assertEqual(surface_id, 1)  # surface emission_id
            self.assertIsInstance(timestamp, float)

            # Check coordinates with noise: (960+2)/1920 = 0.501041666..., (540+3)/1080 = 0.502777...
            self.assertAlmostEqual(x, 0.501041666, places=3)
            self.assertAlmostEqual(y, 0.502777, places=3)

        finally:
            random.uniform = original_uniform

    async def test_tracking_loop_stops_on_shutdown_event(self):
        """Test that tracking loop stops when shutdown event is set."""
        tracker = MockTracker(shutdown_event=self.mock_shutdown_event)
        tracker.add_surface(self.mock_surface)

        # Set shutdown event
        self.mock_shutdown_event.is_set.return_value = True

        # Start tracking loop - it should exit immediately due to shutdown event
        await tracker._tracking_loop()

        # Should not have emitted any data since loop exited immediately
        self.mock_ws_server.broadcast_gaze_data.assert_not_called()

    async def test_tracking_loop_integration(self):
        """Integration test for the tracking loop by calling _emit_gaze_data directly."""
        tracker = MockTracker(
            frequency=10.0,  # 10 Hz for faster testing
            ws_server=self.mock_ws_server,
            shutdown_event=self.mock_shutdown_event
        )
        tracker.add_surface(self.mock_surface)

        # Set initial position
        tracker.current_position = (100.0, 200.0)

        # Mock random for predictable results
        import random
        original_uniform = random.uniform
        random.uniform = Mock(side_effect=[0.0, 0.0])  # No noise for predictable test

        try:
            # Test that _emit_gaze_data works correctly
            await tracker._emit_gaze_data()

            # Verify that broadcast_gaze_data was called once
            self.assertEqual(self.mock_ws_server.broadcast_gaze_data.call_count, 1)

            # Check the call arguments
            call_args = self.mock_ws_server.broadcast_gaze_data.call_args[0]
            device_id, surface_id, x, y, timestamp = call_args

            self.assertEqual(device_id, 0)  # device_index
            self.assertEqual(surface_id, 1)  # surface emission_id
            self.assertIsInstance(timestamp, float)

            # Check coordinates: 100/1920 = 0.052083, 200/1080 = 0.185185
            self.assertAlmostEqual(x, 0.052083, places=3)
            self.assertAlmostEqual(y, 0.185185, places=3)

        finally:
            random.uniform = original_uniform

    async def test_start_stop_tracking(self):
        """Test starting and stopping the tracking process."""
        tracker = MockTracker(ws_server=self.mock_ws_server)

        # Should not be running initially
        self.assertFalse(tracker._running)

        # Start tracking (would normally start mouse listener, but we can't easily test that)
        # In a real scenario, this would also start the mouse listener
        # For testing, we'll just verify the state changes
        await tracker.start_tracking()
        self.assertTrue(tracker._running)
        self.assertIsNotNone(tracker._task)

        # Stop tracking
        await tracker.stop_tracking()
        self.assertFalse(tracker._running)
        self.assertIsNone(tracker._task)


if __name__ == '__main__':
    unittest.main()