"""Tests for HomographyStore."""

import pytest

from ..core.homography_store import HomographyStore


class TestHomographyStore:
    """Test HomographyStore functionality."""

    @pytest.fixture
    def store(self) -> HomographyStore:
        """Create a test store with typical parameters."""
        return HomographyStore(ttl_ms=300, max_err_px=2.0, min_markers=3)

    def test_valid_homography_passes_gates(self, store: HomographyStore) -> None:
        """Test that valid homography passes all gates."""
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
        result = store.get_latest(1001)  # 1ms later

        assert result is not None
        assert result["ts"] == 1000
        assert result["age_ms"] == 1

    def test_stale_homography_returns_none(self, store: HomographyStore) -> None:
        """Test that stale homography (age > ttl_ms) returns None."""
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
        result = store.get_latest(1400)  # 400ms later (> 300ms TTL)

        assert result is None

    def test_insufficient_markers_returns_none(self, store: HomographyStore) -> None:
        """Test that homography with markers < min_markers returns None."""
        homography = {
            "ts": 1000,
            "H": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
            "visible": True,
            "reproj_px": 1.0,
            "markers": 2,  # Less than min_markers (3)
            "screen_w": 1920,
            "screen_h": 1080,
            "img_w": 1280,
            "img_h": 720,
        }

        store.set(homography)
        result = store.get_latest(1001)

        assert result is None

    def test_high_reprojection_error_returns_none(self, store: HomographyStore) -> None:
        """Test that homography with reproj_px > max_err_px returns None."""
        homography = {
            "ts": 1000,
            "H": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
            "visible": True,
            "reproj_px": 3.0,  # Higher than max_err_px (2.0)
            "markers": 4,
            "screen_w": 1920,
            "screen_h": 1080,
            "img_w": 1280,
            "img_h": 720,
        }

        store.set(homography)
        result = store.get_latest(1001)

        assert result is None

    def test_invisible_homography_returns_none(self, store: HomographyStore) -> None:
        """Test that invisible homography returns None."""
        homography = {
            "ts": 1000,
            "H": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
            "visible": False,  # Not visible
            "reproj_px": 1.0,
            "markers": 4,
            "screen_w": 1920,
            "screen_h": 1080,
            "img_w": 1280,
            "img_h": 720,
        }

        store.set(homography)
        result = store.get_latest(1001)

        assert result is None

    def test_no_homography_stored_returns_none(self, store: HomographyStore) -> None:
        """Test that get_latest returns None when no homography is stored."""
        result = store.get_latest(1000)

        assert result is None
