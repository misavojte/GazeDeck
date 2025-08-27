"""Gaze mapping with homography transformation and sequence tracking."""

import numpy as np
from typing import Literal

from .geometry import apply_homography, undistort_points
from .homography_store import HomographyStore
from .types import GazeSample, GazeEvent, SceneCoords, PlaneCoords, HomographyInfo


class GazeMapper:
    """Maps gaze samples to screen coordinates using homography."""

    def __init__(
        self,
        store: HomographyStore,
        plane_uid: str = "screen-1",
        homography_mode: Literal["every", "change", "none"] = "every",
    ) -> None:
        """Initialize gaze mapper.

        Args:
            store: Homography store instance
            plane_uid: Unique identifier for the plane
            homography_mode: When to include homography info ('every', 'change', 'none')
        """
        self._store = store
        self._plane_uid = plane_uid
        self._homography_mode = homography_mode
        self._last_homography_seq = -1
        self._last_homography_matrix: list[list[float]] | None = None
        self._K: list[list[float]] | None = None
        self._D: list[float] | None = None

    def set_calibration(self, K: list[list[float]] | None, D: list[float] | None) -> None:
        """Provide calibration to undistort gaze points before mapping."""
        self._K = K
        self._D = D

    def map(self, gaze: GazeSample, now_ms: int) -> GazeEvent:
        """Map gaze sample to screen coordinates.

        Args:
            gaze: Raw gaze sample
            now_ms: Current timestamp in milliseconds

        Returns:
            GazeEvent with scene and plane coordinates
        """
        # Get latest valid homography
        homography_data = self._store.get_latest(now_ms)

        # Convert scene coordinates to pixels if needed
        scene_coords = self._convert_scene_coords(gaze, homography_data)

        # Optionally undistort using calibration
        if (
            homography_data is not None
            and scene_coords.frame == "scene_px"
            and self._K is not None
            and self._D is not None
        ):
            undist = undistort_points([(scene_coords.x, scene_coords.y)], self._K, self._D)
            scene_coords = SceneCoords(x=float(undist[0, 0]), y=float(undist[0, 1]), frame="scene_px")

        if homography_data is None:
            # No valid homography - return event with invisible plane
            plane_coords = PlaneCoords(
                uid=self._plane_uid,
                x=None,
                y=None,
                on_surface=False,
                visible=False,
                homography=None,
            )
        else:
            # Valid homography - apply transformation
            homography_info = self._create_homography_info(homography_data)

            # Apply homography transformation
            screen_x, screen_y = apply_homography((scene_coords.x, scene_coords.y), homography_data["H"])

            # Check bounds
            screen_w = homography_data["screen_w"]
            screen_h = homography_data["screen_h"]
            on_surface = bool(0 <= screen_x <= screen_w and 0 <= screen_y <= screen_h)

            # Determine if we should include homography based on mode
            include_homography = self._should_include_homography(homography_info)

            plane_coords = PlaneCoords(
                uid=self._plane_uid,
                x=screen_x,  # Always preserve mapped coordinates
                y=screen_y,  # Always preserve mapped coordinates
                on_surface=on_surface,
                visible=True,
                homography=homography_info if include_homography else None,
            )

        return GazeEvent(
            ts=gaze.ts_ms,
            conf=gaze.conf,
            scene=scene_coords,
            plane=plane_coords,
        )

    def _convert_scene_coords(self, gaze: GazeSample, homography_data: dict | None) -> SceneCoords:
        """Convert scene coordinates to pixels if needed."""
        if gaze.frame == "scene_px":
            return SceneCoords(x=gaze.x, y=gaze.y, frame="scene_px")
        elif gaze.frame == "scene_norm" and homography_data is not None:
            # Convert normalized coordinates to pixels
            img_w = homography_data["img_w"]
            img_h = homography_data["img_h"]
            return SceneCoords(
                x=float(gaze.x * img_w),
                y=float(gaze.y * img_h),
                frame="scene_px",
            )
        else:
            # Fallback - keep as is
            return SceneCoords(x=gaze.x, y=gaze.y, frame=gaze.frame)

    def _create_homography_info(self, homography_data: dict) -> HomographyInfo:
        """Create HomographyInfo from homography data."""
        return HomographyInfo(
            H=homography_data["H"],
            ts=homography_data["ts"],
            age_ms=homography_data["age_ms"],
            reproj_px=homography_data["reproj_px"],
            markers=homography_data["markers"],
            screen_w=homography_data["screen_w"],
            screen_h=homography_data["screen_h"],
            img_w=homography_data["img_w"],
            img_h=homography_data["img_h"],
            seq=self._get_homography_seq(homography_data["H"]),
        )

    def _get_homography_seq(self, current_matrix: list[list[float]]) -> int:
        """Get sequence number for homography matrix, incrementing only on meaningful change."""
        if self._last_homography_matrix is None:
            # First homography
            self._last_homography_matrix = current_matrix
            self._last_homography_seq = 0
            return 0

        # Check if matrices are meaningfully different
        current_np = np.array(current_matrix, dtype=np.float64)
        last_np = np.array(self._last_homography_matrix, dtype=np.float64)

        allclose_result = np.allclose(current_np, last_np, rtol=1e-6, atol=1e-8)
        if not bool(allclose_result.item() if hasattr(allclose_result, 'item') else allclose_result):
            # Meaningful change detected
            self._last_homography_matrix = current_matrix
            self._last_homography_seq += 1

        return self._last_homography_seq

    def _should_include_homography(self, homography_info: HomographyInfo) -> bool:
        """Determine if homography should be included based on mode."""
        if self._homography_mode == "every":
            return True
        elif self._homography_mode == "change":
            return homography_info.seq != self._last_homography_seq
        elif self._homography_mode == "none":
            return False
        else:
            return True
