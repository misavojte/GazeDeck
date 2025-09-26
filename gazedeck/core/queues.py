# gazedeck/core/queues.py

# python
import asyncio
from typing import TypeVar, Tuple, Optional
from asyncio import QueueEmpty

# Generic type for sensor data items
T = TypeVar('T')

async def get_most_recent_item(queue: asyncio.Queue[T], timeout: Optional[float] = None) -> Tuple[float, T]:
    """
    Get the most recent item from a queue, discarding older items.
    
    This function is optimized for real-time processing where only the latest
    data is relevant. It efficiently drains the queue to get the newest item.
    
    Args:
        queue: Asyncio queue containing (timestamp, data) tuples
        timeout: Optional timeout in seconds to prevent indefinite blocking
        
    Returns:
        Tuple of (timestamp, data) for the most recent item
        
    Raises:
        asyncio.TimeoutError: If timeout is specified and exceeded
    """
    try:
        if timeout is not None:
            item = await asyncio.wait_for(queue.get(), timeout=timeout)
        else:
            item = await queue.get()
            
        # Validate that item is a tuple (timestamp, data)
        if not isinstance(item, tuple) or len(item) != 2:
            raise ValueError(f"Expected (timestamp, data) tuple, got: {type(item)} with value: {item}")
            
        # Drain queue to get the most recent item
        while True:
            try:
                next_item = queue.get_nowait()
                # Validate next item as well
                if not isinstance(next_item, tuple) or len(next_item) != 2:
                    print(f"[WARN] Invalid queue item format: {type(next_item)} with value: {next_item}")
                    continue
                item = next_item  # Keep the newer item
            except QueueEmpty:
                return item
                
    except asyncio.CancelledError:
        # Re-raise cancellation for proper async cleanup
        raise
    except asyncio.TimeoutError:
        # Timeout occurred - this is expected in real-time processing
        raise
    except Exception as e:
        # Log error with more context for unexpected errors
        print(f"[WARN] Unexpected error getting most recent item: {type(e).__name__}: {e}")
        raise

async def get_closest_item(queue: asyncio.Queue[T], target_timestamp: float, timeout: Optional[float] = None) -> Tuple[float, T]:
    """
    Get the item from queue with timestamp closest to (but not before) target_timestamp.
    
    This function is optimized for synchronizing different data streams in real-time
    processing. It assumes monotonically increasing timestamps for efficiency.
    
    Args:
        queue: Asyncio queue containing (timestamp, data) tuples
        target_timestamp: Target timestamp to find closest match for
        timeout: Optional timeout in seconds to prevent indefinite blocking
        
    Returns:
        Tuple of (timestamp, data) for the closest item
        
    Raises:
        asyncio.TimeoutError: If timeout is specified and exceeded
    """
    try:
        # Get first item with optional timeout
        if timeout is not None:
            first_item = await asyncio.wait_for(queue.get(), timeout=timeout)
        else:
            first_item = await queue.get()
            
        # Validate that item is a tuple (timestamp, data)
        if not isinstance(first_item, tuple) or len(first_item) != 2:
            raise ValueError(f"Expected (timestamp, data) tuple, got: {type(first_item)} with value: {first_item}")
            
        item_ts, item = first_item
        
        # If first item is already past target, return it
        if item_ts > target_timestamp:
            return item_ts, item
            
        # Find the closest item by draining queue until we pass target_timestamp
        while True:
            try:
                next_item_tuple = queue.get_nowait()
                
                # Validate next item format
                if not isinstance(next_item_tuple, tuple) or len(next_item_tuple) != 2:
                    print(f"[WARN] Invalid queue item format in closest search: {type(next_item_tuple)} with value: {next_item_tuple}")
                    continue
                    
                next_item_ts, next_item = next_item_tuple
                
                # If next item passes target timestamp, return it
                if next_item_ts > target_timestamp:
                    return next_item_ts, next_item
                    
                # Keep the newer item and continue
                item_ts, item = next_item_ts, next_item
                
            except QueueEmpty:
                # No more items, return the last one we found
                return item_ts, item
                
    except asyncio.CancelledError:
        # Re-raise cancellation for proper async cleanup
        raise
    except asyncio.TimeoutError:
        # Timeout occurred - this is expected in real-time processing
        raise
    except Exception as e:
        # Log error with more context for unexpected errors
        print(f"[WARN] Unexpected error getting closest item for timestamp {target_timestamp}: {type(e).__name__}: {e}")
        raise
