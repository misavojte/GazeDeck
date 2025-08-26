"""Tests for FrameSkipper."""

import time
from unittest.mock import patch

import pytest

from ..adapters.apriltag.tracker import FrameSkipper


class TestFrameSkipper:
    """Test FrameSkipper functionality."""

    @pytest.fixture
    def skipper(self) -> FrameSkipper:
        """Create a test frame skipper."""
        return FrameSkipper()

    def test_auto_mode_processes_all_frames(self, skipper: FrameSkipper) -> None:
        """Test that auto mode (no target FPS) processes all frames."""
        # No target FPS set
        assert skipper.should_process(time.time())
        assert skipper.should_process(time.time())
        assert skipper.should_process(time.time())

    def test_high_target_fps_processes_all_frames(self, skipper: FrameSkipper) -> None:
        """Test that very high target FPS processes all frames."""
        skipper.set_target_fps(1000.0)  # Very high FPS

        current_time = time.time()
        assert skipper.should_process(current_time)
        assert skipper.should_process(current_time)  # Should still process

    def test_target_fps_throttles_frames(self, skipper: FrameSkipper) -> None:
        """Test that target FPS properly throttles frame processing."""
        skipper.set_target_fps(10.0)  # 10 FPS = 100ms intervals

        current_time = 1000.0

        # First frame should be processed
        assert skipper.should_process(current_time)

        # Second frame immediately after should not be processed
        assert not skipper.should_process(current_time + 0.01)

        # Frame after interval should be processed
        assert skipper.should_process(current_time + 0.15)

    def test_measured_60hz_desired_15hz_keeps_25_percent(self, skipper: FrameSkipper) -> None:
        """Test that 60Hz -> 15Hz keeps roughly 25% of frames."""
        skipper.set_target_fps(15.0)  # 15 FPS desired

        # Simulate 60Hz input (16.67ms intervals)
        interval = 1.0 / 60.0
        current_time = 1000.0

        processed_count = 0
        total_frames = 60  # 1 second of frames

        for i in range(total_frames):
            if skipper.should_process(current_time + i * interval):
                processed_count += 1

        # Should keep roughly 25% (15/60 = 0.25)
        expected_count = 15  # 15 frames per second
        tolerance = 3  # ±3 frames tolerance

        assert abs(processed_count - expected_count) <= tolerance, \
            f"Expected ~{expected_count} frames, got {processed_count}"

    def test_auto_mode_equals_measured_rate(self, skipper: FrameSkipper) -> None:
        """Test that auto mode processes all frames (desired = measured)."""
        # Auto mode should process all frames since desired = measured
        current_time = 1000.0
        interval = 1.0 / 30.0  # 30 FPS

        processed_count = 0
        total_frames = 30

        for i in range(total_frames):
            if skipper.should_process(current_time + i * interval):
                processed_count += 1

        # Should process all frames in auto mode
        assert processed_count == total_frames
