"""Surface pose provider interface."""

from typing import Protocol, AsyncIterator


class HomographyEstimate:
    """Homography estimate with fields required to populate HomographyInfo."""

    def __init__(
        self,
        ts_ms: int,
        H: list[list[float]],
        visible: bool,
        reproj_px: float,
        markers: int,
        screen_w: int,
        screen_h: int,
        img_w: int,
        img_h: int,
    ) -> None:
        """Initialize homography estimate.

        Args:
            ts_ms: Timestamp in milliseconds
            H: 3x3 homography matrix
            visible: Whether the homography is valid
            reproj_px: Mean reprojection error in pixels
            markers: Number of markers used
            screen_w: Screen width in pixels
            screen_h: Screen height in pixels
            img_w: Image width in pixels
            img_h: Image height in pixels
        """
        self.ts_ms = ts_ms
        self.H = H
        self.visible = visible
        self.reproj_px = reproj_px
        self.markers = markers
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.img_w = img_w
        self.img_h = img_h


class ISurfacePoseProvider(Protocol):
    """Protocol for surface pose providers."""

    async def stream(self) -> AsyncIterator[HomographyEstimate]:
        """Stream homography estimates.

        Yields:
            HomographyEstimate: Pose estimation results
        """
        ...  # pragma: no cover
