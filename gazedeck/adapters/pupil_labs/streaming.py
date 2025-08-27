"""Base streaming utilities with reconnection logic for Pupil Labs adapters."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import AsyncIterator, Any, Optional, TypeVar
from dataclasses import dataclass

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class ReconnectionConfig:
    """Configuration for reconnection behavior."""
    max_attempts: int = 5
    initial_delay: float = 1.0
    max_delay: float = 30.0
    backoff_factor: float = 2.0
    retry_on_connection_error: bool = True


class StreamingError(Exception):
    """Base exception for streaming errors."""
    pass


class ConnectionLostError(StreamingError):
    """Raised when connection to sensor is lost."""
    pass


class MaxRetriesExceededError(StreamingError):
    """Raised when maximum reconnection attempts are exceeded."""
    pass


class BaseStreamer(ABC):
    """Base class for streaming data with automatic reconnection.

    This class provides a DRY approach for implementing streaming with reconnection
    logic that can be reused across different types of Pupil Labs data streams.
    """

    def __init__(self, url: str, config: Optional[ReconnectionConfig] = None):
        """Initialize the streamer.

        Args:
            url: Sensor URL to connect to
            config: Reconnection configuration
        """
        self.url = url
        self.config = config or ReconnectionConfig()
        self._shutdown_event = asyncio.Event()
        self._connection_attempts = 0
        self._is_streaming = False

    async def stream_with_reconnect(self) -> AsyncIterator[Any]:
        """Stream data with automatic reconnection on connection failures.

        Yields:
            Stream data items

        Raises:
            MaxRetriesExceededError: When max reconnection attempts are exceeded
        """
        self._connection_attempts = 0

        while not self._shutdown_event.is_set():
            try:
                async for item in self._stream_once():
                    self._connection_attempts = 0  # Reset on successful yield
                    yield item

            except ConnectionLostError as e:
                if not self.config.retry_on_connection_error:
                    logger.error(f"Connection lost and retries disabled: {e}")
                    raise

                self._connection_attempts += 1
                if self._connection_attempts > self.config.max_attempts:
                    logger.error(f"Max reconnection attempts ({self.config.max_attempts}) exceeded")
                    raise MaxRetriesExceededError(
                        f"Failed to reconnect after {self.config.max_attempts} attempts"
                    ) from e

                delay = min(
                    self.config.initial_delay * (self.config.backoff_factor ** (self._connection_attempts - 1)),
                    self.config.max_delay
                )

                logger.warning(f"Connection lost (attempt {self._connection_attempts}/{self.config.max_attempts}). "
                              f"Retrying in {delay:.1f}s...")

                await asyncio.sleep(delay)
                continue

            except Exception as e:
                # For non-connection errors, don't retry automatically
                logger.error(f"Streaming error: {e}")
                raise StreamingError(f"Streaming failed: {e}") from e

    @abstractmethod
    async def _stream_once(self) -> AsyncIterator[Any]:
        """Implement the actual streaming logic for one connection attempt.

        This method should:
        1. Establish connection to the sensor
        2. Stream data until connection is lost
        3. Raise ConnectionLostError when connection fails

        Yields:
            Stream data items
        """
        pass

    async def shutdown(self) -> None:
        """Shutdown the streamer gracefully."""
        logger.info("Shutting down streamer...")
        self._shutdown_event.set()

    def _should_retry(self, error: Exception) -> bool:
        """Determine if an error should trigger reconnection.

        Args:
            error: The exception that occurred

        Returns:
            True if should retry, False otherwise
        """
        # Check for common connection-related error patterns
        error_msg = str(error).lower()
        connection_indicators = [
            'connection',
            'network',
            'timeout',
            'disconnected',
            'reset',
            'broken pipe',
            'connection lost'
        ]

        return any(indicator in error_msg for indicator in connection_indicators)

    def _wrap_streaming_error(self, error: Exception) -> Exception:
        """Wrap streaming errors appropriately.

        Args:
            error: Original exception

        Returns:
            Wrapped exception (ConnectionLostError or original)
        """
        if self._should_retry(error):
            connection_error = ConnectionLostError(f"Connection lost: {error}")
            connection_error.__cause__ = error
            return connection_error
        return error


class ExponentialBackoff:
    """Utility class for calculating exponential backoff delays."""

    @staticmethod
    def calculate_delay(attempt: int, initial_delay: float = 1.0,
                       backoff_factor: float = 2.0, max_delay: float = 30.0) -> float:
        """Calculate delay for exponential backoff.

        Args:
            attempt: Current attempt number (1-based)
            initial_delay: Initial delay in seconds
            backoff_factor: Factor to multiply delay by on each attempt
            max_delay: Maximum delay in seconds

        Returns:
            Delay in seconds for this attempt
        """
        delay = initial_delay * (backoff_factor ** (attempt - 1))
        return min(delay, max_delay)
