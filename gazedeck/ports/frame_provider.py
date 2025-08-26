"""Frame provider interface."""

import numpy as np
from typing import Protocol, AsyncIterator, Tuple

from ..core.types import SceneFrame


class IFrameProvider(Protocol):
    """Protocol for scene frame providers."""

    async def stream(self) -> AsyncIterator[Tuple[SceneFrame, np.ndarray]]:
        """Stream scene frames with pixel data.

        Yields:
            Tuple of (SceneFrame metadata, BGR pixel array)
        """
        ...  # pragma: no cover
