"""Homography storage with quality gates and TTL."""

from typing import Any


class HomographyStore:
    """Stores homography estimates with quality gates and TTL."""

    def __init__(self, ttl_ms: int, max_err_px: float, min_markers: int) -> None:
        """Initialize homography store.

        Args:
            ttl_ms: Time-to-live in milliseconds
            max_err_px: Maximum reprojection error in pixels
            min_markers: Minimum number of markers required
        """
        self._ttl_ms = ttl_ms
        self._max_err_px = max_err_px
        self._min_markers = min_markers
        self._latest: dict[str, Any] | None = None

    def set(self, homography_estimate: dict[str, Any]) -> None:
        """Store the latest homography estimate.

        Args:
            homography_estimate: Homography estimate with fields used by HomographyInfo
        """
        self._latest = homography_estimate

    def get_latest(self, now_ms: int) -> dict[str, Any] | None:
        """Get latest valid homography estimate.

        Returns the latest estimate only if all validity gates pass:
        - visible is True
        - markers ≥ min_markers
        - reproj_px ≤ max_err_px
        - age_ms ≤ ttl_ms

        Args:
            now_ms: Current timestamp in milliseconds

        Returns:
            Valid homography estimate or None if invalid
        """
        if self._latest is None:
            return None

        # Check visibility
        if not self._latest.get("visible", False):
            return None

        # Check minimum markers
        if self._latest.get("markers", 0) < self._min_markers:
            return None

        # Check reprojection error
        if self._latest.get("reproj_px", float("inf")) > self._max_err_px:
            return None

        # Check TTL
        age_ms = now_ms - self._latest.get("ts", 0)
        if age_ms > self._ttl_ms:
            return None

        # Update age_ms in the returned estimate
        result = self._latest.copy()
        result["age_ms"] = age_ms
        return result
