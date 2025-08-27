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
        import logging
        logger = logging.getLogger(__name__)
        
        visible = homography_estimate.get("visible", False)
        markers = homography_estimate.get("markers", 0)
        reproj_px = homography_estimate.get("reproj_px", 0.0)
        
        logger.info(f"HomographyStore.set: visible={visible}, markers={markers}, reproj_px={reproj_px:.2f}")
        
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
        import logging
        logger = logging.getLogger(__name__)
        
        if self._latest is None:
            logger.debug("HomographyStore.get_latest: No estimate stored")
            return None

        # Check visibility
        visible = self._latest.get("visible", False)
        if not visible:
            logger.debug("HomographyStore.get_latest: Rejected - not visible")
            return None

        # Check minimum markers
        markers = self._latest.get("markers", 0)
        if markers < self._min_markers:
            logger.debug(f"HomographyStore.get_latest: Rejected - insufficient markers ({markers} < {self._min_markers})")
            return None

        # Check reprojection error
        reproj_px = self._latest.get("reproj_px", float("inf"))
        if reproj_px > self._max_err_px:
            logger.debug(f"HomographyStore.get_latest: Rejected - high reprojection error ({reproj_px:.2f} > {self._max_err_px})")
            return None

        # Check TTL
        age_ms = now_ms - self._latest.get("ts", 0)
        if age_ms > self._ttl_ms:
            logger.debug(f"HomographyStore.get_latest: Rejected - too old ({age_ms}ms > {self._ttl_ms}ms)")
            return None

        logger.debug(f"HomographyStore.get_latest: Valid estimate - markers={markers}, reproj_px={reproj_px:.2f}, age_ms={age_ms}")
        
        # Update age_ms in the returned estimate
        result = self._latest.copy()
        result["age_ms"] = age_ms
        return result
