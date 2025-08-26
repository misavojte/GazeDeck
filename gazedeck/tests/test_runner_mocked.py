"""Tests for single process runner with mocked providers."""

import asyncio
import math
import random
from typing import AsyncIterator, Tuple
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from ..adapters.ws.sink import WebSocketSink
from ..core.homography_store import HomographyStore
from ..core.mapping import GazeMapper
from ..core.types import GazeSample, GazeEvent, SceneFrame
from ..ports.frame_provider import IFrameProvider
from ..ports.gaze_provider import IGazeProvider
from ..ports.pose_provider import ISurfacePoseProvider, HomographyEstimate


class MockGazeProvider(IGazeProvider):
    """Mock gaze provider that streams at specified rate."""

    def __init__(self, rate_hz: float = 200.0, duration_seconds: float = 1.0):
        """Initialize mock gaze provider.

        Args:
            rate_hz: Gaze sampling rate
            duration_seconds: How long to stream
        """
        self.rate_hz = rate_hz
        self.duration_seconds = duration_seconds
        self.interval = 1.0 / rate_hz

    async def stream(self) -> AsyncIterator[GazeSample]:
        """Stream mock gaze samples."""
        start_time = float(asyncio.get_event_loop().time())
        sample_count = int(self.rate_hz * self.duration_seconds)

        for i in range(sample_count):
            current_time = float(start_time + i * self.interval)
            timestamp_ms = int(current_time * 1000)

            # Generate some variation in gaze position
            sin_val = math.sin(2 * math.pi * 0.5 * current_time)
            cos_val = math.cos(2 * math.pi * 0.3 * current_time)
            rand_val = random.random()
            x = float(640.0 + 100.0 * float(sin_val))  # Oscillate around center
            y = float(360.0 + 50.0 * float(cos_val))
            conf = float(0.9 + 0.1 * float(rand_val))  # Random confidence 0.9-1.0

            yield GazeSample(
                ts_ms=timestamp_ms,
                x=x,
                y=y,
                frame="scene_norm",
                conf=conf,
            )

            # Use very short sleep for testing (100x faster)
            await asyncio.sleep(self.interval / 100.0)


class MockFrameProvider(IFrameProvider):
    """Mock frame provider that streams at specified rate."""

    def __init__(self, rate_hz: float = 30.0, duration_seconds: float = 1.0):
        """Initialize mock frame provider.

        Args:
            rate_hz: Frame rate
            duration_seconds: How long to stream
        """
        self.rate_hz = rate_hz
        self.duration_seconds = duration_seconds
        self.interval = 1.0 / rate_hz

    async def stream(self) -> AsyncIterator[Tuple[SceneFrame, np.ndarray]]:
        """Stream mock frames."""
        start_time = float(asyncio.get_event_loop().time())
        frame_count = int(self.rate_hz * self.duration_seconds)

        for i in range(frame_count):
            current_time = float(start_time + i * self.interval)
            timestamp_ms = int(current_time * 1000)

            # Create a simple test frame
            frame = np.zeros((720, 1280, 3), dtype=np.uint8)

            scene_frame = SceneFrame(
                ts_ms=timestamp_ms,
                w=1280,
                h=720,
            )

            yield scene_frame, frame

            # Use very short sleep for testing (100x faster)
            await asyncio.sleep(self.interval / 100.0)


class MockPoseProvider(ISurfacePoseProvider):
    """Mock pose provider that provides constant valid homography."""

    def __init__(self, valid: bool = True):
        """Initialize mock pose provider.

        Args:
            valid: Whether to provide valid homography
        """
        self.valid = valid

    async def stream(self) -> AsyncIterator[HomographyEstimate]:
        """Stream mock homography estimates."""
        while True:
            if self.valid:
                yield HomographyEstimate(
                    ts_ms=int(float(asyncio.get_event_loop().time()) * 1000),
                    H=[[1, 0, 0], [0, 1, 0], [0, 0, 1]],  # Identity
                    visible=True,
                    reproj_px=0.5,
                    markers=4,
                    screen_w=1920,
                    screen_h=1080,
                    img_w=1280,
                    img_h=720,
                )
            else:
                yield HomographyEstimate(
                    ts_ms=int(float(asyncio.get_event_loop().time()) * 1000),
                    H=[[1, 0, 0], [0, 1, 0], [0, 0, 1]],  # Identity
                    visible=False,
                    reproj_px=0.0,
                    markers=0,
                    screen_w=1920,
                    screen_h=1080,
                    img_w=1280,
                    img_h=720,
                )
            await asyncio.sleep(0.001)  # Emit every 1ms for fast testing


class MockWebSocketSink:
    """Mock WebSocket sink for testing."""

    def __init__(self):
        """Initialize mock sink."""
        self.events = []
        self.emit_count = 0

    async def emit(self, msg: GazeEvent) -> None:
        """Mock emit method."""
        self.events.append(msg)
        self.emit_count += 1

    async def serve(self, host: str = "localhost", port: int = 8765) -> None:
        """Mock serve method - just wait."""
        await asyncio.sleep(10)  # Run for test duration

    async def close(self) -> None:
        """Mock close method."""
        pass


@pytest.mark.asyncio
async def test_runner_with_mocked_providers():
    """Test the complete pipeline with mocked providers."""
    # Create mock providers
    gaze_provider = MockGazeProvider(rate_hz=200.0, duration_seconds=0.5)
    frame_provider = MockFrameProvider(rate_hz=30.0, duration_seconds=0.5)
    pose_provider = MockPoseProvider(valid=True)
    sink = MockWebSocketSink()

    # Create store and mapper
    store = HomographyStore(ttl_ms=300, max_err_px=2.0, min_markers=3)
    mapper = GazeMapper(store)

    # Create queues
    q_gaze = asyncio.Queue(maxsize=512)
    q_frames = asyncio.Queue(maxsize=16)
    q_out = asyncio.Queue(maxsize=512)

    # Create shutdown event
    shutdown_event = asyncio.Event()

    # Helper function to drop oldest item from queue
    def drop_oldest_helper(queue: asyncio.Queue, item):
        try:
            queue.put_nowait(item)
        except asyncio.QueueFull:
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            try:
                queue.put_nowait(item)
            except asyncio.QueueFull:
                pass  # Skip if still full

    # Producer tasks
    async def gaze_producer():
        try:
            async for gaze_sample in gaze_provider.stream():
                if shutdown_event.is_set():
                    break
                drop_oldest_helper(q_gaze, gaze_sample)
        except Exception:
            shutdown_event.set()

    async def frame_producer():
        try:
            async for frame_data in frame_provider.stream():
                if shutdown_event.is_set():
                    break
                drop_oldest_helper(q_frames, frame_data)
        except Exception:
            shutdown_event.set()

    async def pose_consumer():
        try:
            async for homography_estimate in pose_provider.stream():
                if shutdown_event.is_set():
                    break
                estimate_dict = {
                    "ts": homography_estimate.ts_ms,
                    "H": homography_estimate.H,
                    "visible": homography_estimate.visible,
                    "reproj_px": homography_estimate.reproj_px,
                    "markers": homography_estimate.markers,
                    "screen_w": homography_estimate.screen_w,
                    "screen_h": homography_estimate.screen_h,
                    "img_w": homography_estimate.img_w,
                    "img_h": homography_estimate.img_h,
                }
                store.set(estimate_dict)
                await asyncio.sleep(0.0001)  # Very small delay for fast testing
        except Exception:
            shutdown_event.set()

    async def gaze_mapper():
        try:
            while not shutdown_event.is_set():
                try:
                    gaze_sample = await asyncio.wait_for(q_gaze.get(), timeout=0.01)
                    now_ms = int(asyncio.get_event_loop().time() * 1000)
                    gaze_event = mapper.map(gaze_sample, now_ms)
                    drop_oldest_helper(q_out, gaze_event)
                except asyncio.TimeoutError:
                    continue
        except Exception:
            shutdown_event.set()

    async def output_consumer():
        try:
            while not shutdown_event.is_set():
                try:
                    gaze_event = await asyncio.wait_for(q_out.get(), timeout=0.01)
                    await sink.emit(gaze_event)
                except asyncio.TimeoutError:
                    continue
        except Exception:
            shutdown_event.set()

    # Run all tasks for a short duration
    tasks = []
    try:
        tasks = [
            asyncio.create_task(gaze_producer()),
            asyncio.create_task(frame_producer()),
            asyncio.create_task(pose_consumer()),
            asyncio.create_task(gaze_mapper()),
            asyncio.create_task(output_consumer()),
        ]

        # Let tasks run for enough time to produce expected samples
        # 200Hz * 0.5s = 100 samples, each with 0.005/100 = 0.00005s sleep
        # Total time needed: 100 * 0.00005 = 0.005s, plus processing overhead
        await asyncio.sleep(0.05)

    finally:
        # Set shutdown and wait for tasks to complete
        shutdown_event.set()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    # Verify results
    assert sink.emit_count > 0, "Should have emitted some events"

    # Check that events have valid structure
    for event in sink.events:
        assert isinstance(event, GazeEvent)
        assert event.plane.visible is True  # Homography is valid
        assert event.plane.x is not None
        assert event.plane.y is not None
        assert event.plane.on_surface is not None
        assert event.plane.homography is not None

    # Check that we got a reasonable number of events (pipeline is working)
    # With the current fast mock providers and timing, we expect some events
    min_expected_events = 3  # At least a few events should be produced
    assert sink.emit_count >= min_expected_events, \
        f"Expected at least {min_expected_events} events, got {sink.emit_count}"


@pytest.mark.asyncio
async def test_runner_with_invalid_homography():
    """Test pipeline behavior when homography becomes invalid."""
    # Create providers with invalid homography
    gaze_provider = MockGazeProvider(rate_hz=100.0, duration_seconds=0.3)
    frame_provider = MockFrameProvider(rate_hz=30.0, duration_seconds=0.3)
    pose_provider = MockPoseProvider(valid=False)  # Invalid homography
    sink = MockWebSocketSink()

    # Create store and mapper
    store = HomographyStore(ttl_ms=300, max_err_px=2.0, min_markers=3)
    mapper = GazeMapper(store)

    # Create queues
    q_gaze = asyncio.Queue(maxsize=512)
    q_frames = asyncio.Queue(maxsize=16)
    q_out = asyncio.Queue(maxsize=512)

    # Create shutdown event
    shutdown_event = asyncio.Event()

    # Helper function to drop oldest item from queue
    def drop_oldest_helper(queue: asyncio.Queue, item):
        try:
            queue.put_nowait(item)
        except asyncio.QueueFull:
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            try:
                queue.put_nowait(item)
            except asyncio.QueueFull:
                pass

    # Simplified pipeline for this test
    async def gaze_producer():
        try:
            async for gaze_sample in gaze_provider.stream():
                if shutdown_event.is_set():
                    break
                drop_oldest_helper(q_gaze, gaze_sample)
        except Exception:
            shutdown_event.set()

    async def pose_consumer():
        try:
            async for homography_estimate in pose_provider.stream():
                if shutdown_event.is_set():
                    break
                estimate_dict = {
                    "ts": homography_estimate.ts_ms,
                    "H": homography_estimate.H,
                    "visible": homography_estimate.visible,
                    "reproj_px": homography_estimate.reproj_px,
                    "markers": homography_estimate.markers,
                    "screen_w": homography_estimate.screen_w,
                    "screen_h": homography_estimate.screen_h,
                    "img_w": homography_estimate.img_w,
                    "img_h": homography_estimate.img_h,
                }
                store.set(estimate_dict)
                await asyncio.sleep(0.01)
        except Exception:
            shutdown_event.set()

    async def gaze_mapper():
        try:
            while not shutdown_event.is_set():
                try:
                    gaze_sample = await asyncio.wait_for(q_gaze.get(), timeout=0.01)
                    now_ms = int(asyncio.get_event_loop().time() * 1000)
                    gaze_event = mapper.map(gaze_sample, now_ms)
                    drop_oldest_helper(q_out, gaze_event)
                except asyncio.TimeoutError:
                    continue
        except Exception:
            shutdown_event.set()

    async def output_consumer():
        try:
            while not shutdown_event.is_set():
                try:
                    gaze_event = await asyncio.wait_for(q_out.get(), timeout=0.01)
                    await sink.emit(gaze_event)
                except asyncio.TimeoutError:
                    continue
        except Exception:
            shutdown_event.set()

    # Run pipeline
    try:
        await asyncio.wait_for(
            asyncio.gather(
                gaze_producer(),
                pose_consumer(),
                gaze_mapper(),
                output_consumer(),
                return_exceptions=True
            ),
            timeout=0.4
        )
    except asyncio.TimeoutError:
        pass
    finally:
        shutdown_event.set()

    # Verify results - all events should have invisible planes
    assert sink.emit_count > 0, "Should have emitted some events"

    for event in sink.events:
        assert isinstance(event, GazeEvent)
        assert event.plane.visible is False, "Plane should be invisible when homography is invalid"
        assert event.plane.x is None, "X coordinate should be None when invisible"
        assert event.plane.y is None, "Y coordinate should be None when invisible"
        assert event.plane.homography is None, "Homography should be None when invisible"
