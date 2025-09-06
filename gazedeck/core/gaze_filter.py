# gazedeck/core/gaze_filter.py
"""Simple gaze filtering system with chaining support."""

from typing import Optional, Tuple

class GazeFilter:
    """Base gaze filter class."""
    def __init__(self, next_filter: Optional['GazeFilter'] = None):
        self.next_filter = next_filter

    def filter(self, x: float, y: float) -> Tuple[float, float]:
        """Filter gaze coordinates, optionally chaining to next filter."""
        filtered_x, filtered_y = self._filter_impl(x, y)
        if self.next_filter:
            return self.next_filter.filter(filtered_x, filtered_y)
        return filtered_x, filtered_y

    def _filter_impl(self, x: float, y: float) -> Tuple[float, float]:
        """Implementation of filtering logic."""
        raise NotImplementedError

    def reset(self):
        """Reset filter state."""
        if self.next_filter:
            self.next_filter.reset()

class ExponentialFilter(GazeFilter):
    """Exponential smoothing filter."""
    def __init__(self, alpha: float = 0.25, next_filter: Optional[GazeFilter] = None):
        super().__init__(next_filter)
        self.alpha = alpha
        self.smooth_x: Optional[float] = None
        self.smooth_y: Optional[float] = None

    def _filter_impl(self, x: float, y: float) -> Tuple[float, float]:
        if self.smooth_x is None:
            self.smooth_x = x
            self.smooth_y = y
        else:
            self.smooth_x = self.alpha * x + (1 - self.alpha) * self.smooth_x
            self.smooth_y = self.alpha * y + (1 - self.alpha) * self.smooth_y
        return self.smooth_x, self.smooth_y

    def reset(self):
        self.smooth_x = None
        self.smooth_y = None
        super().reset()

class NoFilter(GazeFilter):
    """Pass-through filter."""
    def _filter_impl(self, x: float, y: float) -> Tuple[float, float]:
        return x, y
