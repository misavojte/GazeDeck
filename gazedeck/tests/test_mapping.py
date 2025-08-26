"""Tests for GazeMapper."""

import pytest

from ..core.homography_store import HomographyStore
from ..core.mapping import GazeMapper
from ..core.types import GazeSample, SceneCoords


class TestGazeMapper:
    """Test GazeMapper functionality."""

    @pytest.fixture
    def store(self) -> HomographyStore:
        """Create a test store."""
        return HomographyStore(ttl_ms=300, max_err_px=2.0, min_markers=3)

    @pytest.fixture
    def mapper(self, store: HomographyStore) -> GazeMapper:
        """Create a test mapper."""
        return GazeMapper(store, plane_uid="screen-1")

    def test_identity_homography_same_coordinates(self, store: HomographyStore, mapper: GazeMapper) -> None:
        """Test that identity homography returns same coordinates."""
        # Set up identity homography
        homography = {
            "ts": 1000,
            "H": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],  # Identity matrix
            "visible": True,
            "reproj_px": 1.0,
            "markers": 4,
            "screen_w": 1920,
            "screen_h": 1080,
            "img_w": 1280,
            "img_h": 720,
        }
        store.set(homography)

        # Create gaze sample with pixel coordinates
        gaze = GazeSample(
            ts_ms=1001,
            x=640.0,  # Center of 1280px width
            y=360.0,  # Center of 720px height
            frame="scene_px",
            conf=1.0,
        )

        result = mapper.map(gaze, 1001)

        # Should map to same coordinates (identity transformation)
        assert result.plane.x == 640.0
        assert result.plane.y == 360.0
        assert result.plane.on_surface is True
        assert result.plane.visible is True
        assert result.scene.x == 640.0
        assert result.scene.y == 360.0
        assert result.scene.frame == "scene_px"

    def test_out_of_bounds_coordinates(self, store: HomographyStore, mapper: GazeMapper) -> None:
        """Test that out-of-bounds coordinates have on_surface=false."""
        # Set up identity homography
        homography = {
            "ts": 1000,
            "H": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
            "visible": True,
            "reproj_px": 1.0,
            "markers": 4,
            "screen_w": 1920,
            "screen_h": 1080,
            "img_w": 1280,
            "img_h": 720,
        }
        store.set(homography)

        # Create gaze sample outside screen bounds
        gaze = GazeSample(
            ts_ms=1001,
            x=2000.0,  # Beyond screen width
            y=1200.0,  # Beyond screen height
            frame="scene_px",
            conf=1.0,
        )

        result = mapper.map(gaze, 1001)

        # Should be mapped but not on surface
        assert result.plane.x == 2000.0
        assert result.plane.y == 1200.0
        assert result.plane.on_surface is False
        assert result.plane.visible is True

    def test_normalized_coordinates_conversion(self, store: HomographyStore, mapper: GazeMapper) -> None:
        """Test conversion from normalized to pixel coordinates."""
        # Set up identity homography
        homography = {
            "ts": 1000,
            "H": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
            "visible": True,
            "reproj_px": 1.0,
            "markers": 4,
            "screen_w": 1920,
            "screen_h": 1080,
            "img_w": 1280,
            "img_h": 720,
        }
        store.set(homography)

        # Create gaze sample with normalized coordinates
        gaze = GazeSample(
            ts_ms=1001,
            x=0.5,  # Center normalized
            y=0.5,  # Center normalized
            frame="scene_norm",
            conf=1.0,
        )

        result = mapper.map(gaze, 1001)

        # Should convert to pixel coordinates: 0.5 * 1280 = 640, 0.5 * 720 = 360
        assert result.plane.x == 640.0
        assert result.plane.y == 360.0
        assert result.plane.on_surface is True
        assert result.plane.visible is True
        # Scene coords should remain as pixels after conversion
        assert result.scene.x == 640.0
        assert result.scene.y == 360.0
        assert result.scene.frame == "scene_px"

    def test_no_valid_homography_returns_invisible(self, mapper: GazeMapper) -> None:
        """Test that invalid/missing homography returns invisible plane."""
        gaze = GazeSample(
            ts_ms=1001,
            x=640.0,
            y=360.0,
            frame="scene_px",
            conf=1.0,
        )

        result = mapper.map(gaze, 1001)

        # Should return event with invisible plane
        assert result.plane.x is None
        assert result.plane.y is None
        assert result.plane.on_surface is False
        assert result.plane.visible is False
        assert result.plane.homography is None
