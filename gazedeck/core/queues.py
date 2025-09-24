# gazedeck/core/queues.py

# python
import asyncio
from typing import TypeVar, Tuple, AsyncIterator
from asyncio import QueueEmpty, QueueFull

# Generic type for sensor data items
T = TypeVar('T')

async def enqueue_sensor_data(sensor: AsyncIterator[T], queue: asyncio.Queue[T], label: str) -> None:
    print(f"🎬 Starting sensor data collection for: {label}")
    count = 0
    async for datum in sensor:
        count += 1
        try:
            queue.put_nowait((datum.timestamp_unix_seconds, datum))
        except QueueFull:
            # Queue full - drop the oldest to keep the freshest data and avoid latency build-up
            try:
                _ = queue.get_nowait()
            except QueueEmpty:
                # Rare race: became empty, just skip
                continue
            # Try to insert the newest frame after dropping the oldest
            try:
                queue.put_nowait((datum.timestamp_unix_seconds, datum))
            except QueueFull:
                # If still full due to concurrency, give up on this datum
                pass

async def get_most_recent_item(queue: asyncio.Queue[T]) -> Tuple[float, T]:
    item = await queue.get()
    while True:
        try:
            next_item = queue.get_nowait()
        except QueueEmpty:
            return item
        else:
            item = next_item

async def get_closest_item(queue: asyncio.Queue[T], timestamp: float) -> Tuple[float, T]:
    item_ts, item = await queue.get()
    # assumes monotonically increasing timestamps
    if item_ts > timestamp:
        return item_ts, item
    while True:
        try:
            next_item_ts, next_item = queue.get_nowait()
        except QueueEmpty:
            return item_ts, item
        else:
            if next_item_ts > timestamp:
                return next_item_ts, next_item
            item_ts, item = next_item_ts, next_item
