"""AprilTag pose tracker with FPS control and homography estimation."""

import asyncio
import time
from typing import Dict, AsyncIterator, Literal

import cv2
import numpy as np
import pupil_apriltags

from ...core.types import SceneFrame
from ...core.geometry import undistort_points
from ...ports.pose_provider import ISurfacePoseProvider, HomographyEstimate
from .layouts import ScreenConfig


class FPSMeter:
    """FPS meter using exponential weighted moving average."""

    def __init__(self, alpha: float = 0.1) -> None:
        """Initialize FPS meter.

        Args:
            alpha: Smoothing factor for EWMA (0 < alpha <= 1)
        """
        self._alpha = alpha
        self._last_time: float | None = None
        self._ewma_fps: float | None = None

    def update(self, timestamp_ms: int) -> float | None:
        """Update FPS estimate with new timestamp.

        Args:
            timestamp_ms: Current timestamp in milliseconds

        Returns:
            Current FPS estimate or None if not enough data
        """
        current_time = timestamp_ms / 1000.0  # Convert to seconds

        if self._last_time is None:
            self._last_time = current_time
            return None

        dt = current_time - self._last_time
        if dt <= 0:
            return self._ewma_fps

        instant_fps = 1.0 / dt

        if self._ewma_fps is None:
            self._ewma_fps = instant_fps
        else:
            self._ewma_fps = self._alpha * instant_fps + (1 - self._alpha) * self._ewma_fps

        self._last_time = current_time
        return self._ewma_fps

    def get_fps(self) -> float | None:
        """Get current FPS estimate."""
        return self._ewma_fps


class FrameSkipper:
    """Frame skipper to achieve desired processing rate."""

    def __init__(self) -> None:
        """Initialize frame skipper."""
        self._last_processed_time: float | None = None
        self._interval_seconds: float | None = None

    def set_target_fps(self, target_fps: float) -> None:
        """Set target processing FPS.

        Args:
            target_fps: Desired frames per second
        """
        if target_fps > 0:
            self._interval_seconds = 1.0 / target_fps
        else:
            self._interval_seconds = None

    def should_process(self, current_time_seconds: float) -> bool:
        """Check if frame should be processed.

        Args:
            current_time_seconds: Current time in seconds

        Returns:
            True if frame should be processed
        """
        if self._interval_seconds is None:
            return True

        if self._last_processed_time is None:
            self._last_processed_time = current_time_seconds
            return True

        # For very high FPS (interval < 1ms), process all frames
        if self._interval_seconds is None or self._interval_seconds < 0.001:
            return True

        # Allow processing if timestamp is same as last processed (handles identical timestamps)
        if current_time_seconds == self._last_processed_time:
            return True

        if current_time_seconds - self._last_processed_time >= self._interval_seconds:
            self._last_processed_time = current_time_seconds
            return True

        return False


class AprilTagPoseProvider(ISurfacePoseProvider):
    """AprilTag-based pose provider with configurable detection rate."""

    def __init__(
        self,
        frame_provider,  # Type will be IFrameProvider when we import it
        screen_config: ScreenConfig,
        tag_rate: Literal["auto"] | float = "auto",
        ransac_px: float = 50.0,
        min_markers: int = 3,
    ) -> None:
        """Initialize AprilTag pose provider.

        Args:
            frame_provider: Frame provider instance
            screen_config: Screen configuration containing markers, dimensions, and plane ID
            tag_rate: Detection rate ("auto" or Hz)
            ransac_px: RANSAC threshold in pixels
            min_markers: Minimum markers required for homography
        """
        self._frame_provider = frame_provider
        self._screen_config = screen_config
        self._screen_markers = screen_config.markers
        self._screen_w = screen_config.screen_width
        self._screen_h = screen_config.screen_height
        self._ransac_px = ransac_px
        self._min_markers = min_markers

        # FPS control
        self._fps_meter = FPSMeter()
        self._frame_skipper = FrameSkipper()
        self._target_rate = tag_rate
        self._measured_fps: float | None = None

        # Calibration (optional)
        self._K: list[list[float]] | None = None
        self._D: list[float] | None = None

        # AprilTag detector
        self._detector = pupil_apriltags.Detector(
            families="tag36h11",
            nthreads=1,
            quad_decimate=1.0,
            quad_sigma=0.0,
            refine_edges=True,
            decode_sharpening=0.25,
            debug=False,
        )

    def set_calibration(self, K: list[list[float]] | None, D: list[float] | None) -> None:
        """Provide camera intrinsics and distortion for undistortion before homography."""
        self._K = K
        self._D = D

    async def stream(self) -> AsyncIterator[HomographyEstimate]:
        """Stream homography estimates.

        Yields:
            HomographyEstimate: Pose estimation results
        """
        async for scene_frame, frame_bgr in self._frame_provider.stream():
            current_time_seconds = scene_frame.ts_ms / 1000.0

            # Update FPS estimate
            measured_fps = self._fps_meter.update(scene_frame.ts_ms)
            if measured_fps is not None:
                self._measured_fps = measured_fps

            # Update target rate if auto
            if self._target_rate == "auto" and self._measured_fps is not None:
                self._frame_skipper.set_target_fps(self._measured_fps)
            elif isinstance(self._target_rate, (int, float)):
                self._frame_skipper.set_target_fps(self._target_rate)

            # Check if we should process this frame
            if not self._frame_skipper.should_process(current_time_seconds):
                continue

            # Detect AprilTags
            gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
            tags = self._detector.detect(gray)
            
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Detected {len(tags)} AprilTags")

            # Build correspondences
            image_points = []
            screen_points = []
            matched_tags = []

            for tag in tags:
                tag_id = tag.tag_id
                logger.debug(f"Found tag ID {tag_id}")
                if tag_id in self._screen_markers:
                    # Use detected corners in image
                    image_corners = tag.corners
                    screen_corners = self._screen_markers[tag_id]

                    image_points.extend(image_corners)
                    screen_points.extend(screen_corners)
                    matched_tags.append(tag_id)
                else:
                    logger.debug(f"Tag ID {tag_id} not in screen markers config")
            
            logger.info(f"Matched {len(matched_tags)} tags: {matched_tags}")

            # Compute homography if enough points
            if len(image_points) >= self._min_markers * 4:
                image_points_np = np.array(image_points, dtype=np.float32)
                # Undistort detected corners if calibration available
                if self._K is not None and self._D is not None:
                    image_points_np = undistort_points(image_points_np, self._K, self._D)

                screen_points_np = np.array(screen_points, dtype=np.float32)

                # Find homography using RANSAC
                logger.info(f"Computing homography with {len(image_points_np)} points from {len(matched_tags)} tags")
                logger.info(f"RANSAC threshold: {self._ransac_px}px")
                
                H, mask = cv2.findHomography(
                    image_points_np,
                    screen_points_np,
                    cv2.RANSAC,
                    self._ransac_px,
                    confidence=0.99,
                    maxIters=2000
                )

                if H is not None:
                    # Compute reprojection error
                    projected_points = cv2.perspectiveTransform(
                        image_points_np.reshape(-1, 1, 2), H
                    )
                    reproj_errors = np.linalg.norm(
                        projected_points.reshape(-1, 2) - screen_points_np, axis=1
                    )
                    mean_reproj_px = float(np.mean(reproj_errors))

                    # Count inliers
                    inliers = int(np.sum(mask).item())
                    markers_used = inliers // 4  # 4 corners per marker
                    
                    logger.info(f"RANSAC inliers: {inliers}/{len(image_points_np)} points")
                    logger.info(f"Homography computed: {markers_used} markers, reproj_error={mean_reproj_px:.2f}px")
                    
                    # Log which points were rejected
                    outliers = len(image_points_np) - inliers
                    if outliers > 0:
                        logger.warning(f"RANSAC rejected {outliers} points as outliers (threshold={self._ransac_px}px)")

                    yield HomographyEstimate(
                        ts_ms=scene_frame.ts_ms,
                        H=H.tolist(),
                        visible=True,
                        reproj_px=mean_reproj_px,
                        markers=markers_used,
                        screen_w=self._screen_w,
                        screen_h=self._screen_h,
                        img_w=scene_frame.w,
                        img_h=scene_frame.h,
                    )
                else:
                    # Homography computation failed
                    logger.warning(f"Homography computation failed with {len(matched_tags)} matched tags")
                    yield HomographyEstimate(
                        ts_ms=scene_frame.ts_ms,
                        H=[[1, 0, 0], [0, 1, 0], [0, 0, 1]],  # Identity matrix
                        visible=False,
                        reproj_px=0.0,
                        markers=0,
                        screen_w=self._screen_w,
                        screen_h=self._screen_h,
                        img_w=scene_frame.w,
                        img_h=scene_frame.h,
                    )
            else:
                # Not enough markers detected
                logger.info(f"Not enough markers: need {self._min_markers}, got {len(matched_tags)} matched tags")
                yield HomographyEstimate(
                    ts_ms=scene_frame.ts_ms,
                    H=[[1, 0, 0], [0, 1, 0], [0, 0, 1]],  # Identity matrix
                    visible=False,
                    reproj_px=0.0,
                    markers=len(tags),
                    screen_w=self._screen_w,
                    screen_h=self._screen_h,
                    img_w=scene_frame.w,
                    img_h=scene_frame.h,
                )
