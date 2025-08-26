"""Single process runner for GazeDeck."""

import asyncio
import logging
from typing import Literal

import typer

from ..adapters.apriltag.layouts import load_markers
from ..adapters.apriltag.tracker import AprilTagPoseProvider
from ..adapters.pupil_labs.frames import PupilLabsFrameProvider
from ..adapters.pupil_labs.gaze import PupilLabsGazeProvider
from ..adapters.ws.sink import WebSocketSink
from ..core.homography_store import HomographyStore
from ..core.mapping import GazeMapper
from ..ports.pose_provider import HomographyEstimate

logger = logging.getLogger(__name__)

app = typer.Typer()


def drop_oldest_helper(queue: asyncio.Queue, item) -> None:
    """Drop oldest items from queue if full.

    Args:
        queue: The asyncio queue
        item: Item to put in queue
    """
    try:
        queue.put_nowait(item)
    except asyncio.QueueFull:
        # Remove oldest item
        try:
            queue.get_nowait()
        except asyncio.QueueEmpty:
            pass
        # Try again
        try:
            queue.put_nowait(item)
        except asyncio.QueueFull:
            logger.warning("Queue still full after dropping oldest item")


async def gaze_producer(
    gaze_provider, q_gaze: asyncio.Queue, shutdown_event: asyncio.Event
) -> None:
    """Produce gaze samples and put them in queue.

    Args:
        gaze_provider: Gaze provider instance
        q_gaze: Queue for gaze samples
        shutdown_event: Event to signal shutdown
    """
    logger.info("Starting gaze producer")

    try:
        async for gaze_sample in gaze_provider.stream():
            if shutdown_event.is_set():
                break

            drop_oldest_helper(q_gaze, gaze_sample)

    except Exception as e:
        logger.error(f"Gaze producer error: {e}")
        shutdown_event.set()
    finally:
        logger.info("Gaze producer stopped")


async def frame_producer(
    frame_provider, q_frames: asyncio.Queue, shutdown_event: asyncio.Event
) -> None:
    """Produce frames and put them in queue.

    Args:
        frame_provider: Frame provider instance
        q_frames: Queue for frames
        shutdown_event: Event to signal shutdown
    """
    logger.info("Starting frame producer")

    try:
        async for frame_data in frame_provider.stream():
            if shutdown_event.is_set():
                break

            drop_oldest_helper(q_frames, frame_data)

    except Exception as e:
        logger.error(f"Frame producer error: {e}")
        shutdown_event.set()
    finally:
        logger.info("Frame producer stopped")


async def pose_provider_task(
    pose_provider,
    store: HomographyStore,
    q_frames: asyncio.Queue,
    shutdown_event: asyncio.Event,
) -> None:
    """Consume frames at configured rate and update homography store.

    Args:
        pose_provider: Pose provider instance
        store: Homography store
        q_frames: Queue for frames
        shutdown_event: Event to signal shutdown
    """
    logger.info("Starting pose provider")

    try:
        async for homography_estimate in pose_provider.stream():
            if shutdown_event.is_set():
                break

            # Convert HomographyEstimate to dict for store
            estimate_dict = {
                "ts": homography_estimate.ts_ms,
                "H": homography_estimate.H,
                "visible": homography_estimate.visible,
                "reproj_px": homography_estimate.reproj_px,
                "markers": homography_estimate.markers,
                "screen_w": homography_estimate.screen_w,
                "screen_h": homography_estimate.screen_h,
                "img_w": homography_estimate.img_w,
                "img_h": homography_estimate.img_h,
            }

            store.set(estimate_dict)

    except Exception as e:
        logger.error(f"Pose provider error: {e}")
        shutdown_event.set()
    finally:
        logger.info("Pose provider stopped")


async def mapper_task(
    mapper: GazeMapper,
    q_gaze: asyncio.Queue,
    q_out: asyncio.Queue,
    shutdown_event: asyncio.Event,
) -> None:
    """Map gaze samples and put results in output queue.

    Args:
        mapper: Gaze mapper instance
        q_gaze: Queue for gaze samples
        q_out: Output queue for gaze events
        shutdown_event: Event to signal shutdown
    """
    logger.info("Starting mapper")

    try:
        while not shutdown_event.is_set():
            try:
                # Get gaze sample with timeout
                gaze_sample = await asyncio.wait_for(q_gaze.get(), timeout=0.1)
                now_ms = int(asyncio.get_event_loop().time() * 1000)

                # Map to gaze event
                gaze_event = mapper.map(gaze_sample, now_ms)

                # Put in output queue
                drop_oldest_helper(q_out, gaze_event)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.warning(f"Mapper processing error: {e}")
                continue

    except Exception as e:
        logger.error(f"Mapper error: {e}")
        shutdown_event.set()
    finally:
        logger.info("Mapper stopped")


async def websocket_drainer(
    sink: WebSocketSink,
    q_out: asyncio.Queue,
    shutdown_event: asyncio.Event,
) -> None:
    """Drain output queue and send to WebSocket clients.

    Args:
        sink: WebSocket sink
        q_out: Output queue for gaze events
        shutdown_event: Event to signal shutdown
    """
    logger.info("Starting WebSocket drainer")

    try:
        while not shutdown_event.is_set():
            try:
                # Get gaze event with timeout
                gaze_event = await asyncio.wait_for(q_out.get(), timeout=0.1)

                # Send to WebSocket clients
                await sink.emit(gaze_event)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.warning(f"WebSocket drainer error: {e}")
                continue

    except Exception as e:
        logger.error(f"WebSocket drainer error: {e}")
        shutdown_event.set()
    finally:
        logger.info("WebSocket drainer stopped")


@app.command()
def main(
    provider: str = typer.Option("pupil-labs", help="Gaze provider type"),
    screen_w: int = typer.Option(1920, help="Screen width in pixels"),
    screen_h: int = typer.Option(1080, help="Screen height in pixels"),
    markers_json: str = typer.Option(
        "config/markers/screen_4tags.example.json",
        help="Path to markers JSON file"
    ),
    tag_rate: str = typer.Option("auto", help="Tag detection rate (auto or Hz)"),
    ttl_ms: int = typer.Option(300, help="Homography TTL in milliseconds"),
    max_err_px: float = typer.Option(2.0, help="Maximum reprojection error in pixels"),
    min_markers: int = typer.Option(3, help="Minimum markers required"),
    ws_port: int = typer.Option(8765, help="WebSocket port"),
    homography_mode: Literal["every", "change", "none"] = typer.Option(
        "every", help="Homography inclusion mode"
    ),
    pupil_url: str = typer.Option(
        "pi.local:8080", help="Pupil Labs device URL (for pupil-labs provider)"
    ),
) -> None:
    """Run GazeDeck pipeline."""
    logging.basicConfig(level=logging.INFO)

    # Validate provider
    if provider != "pupil-labs":
        typer.echo(f"Unsupported provider: {provider}", err=True)
        raise typer.Exit(1)

    # Parse tag rate
    if tag_rate == "auto":
        parsed_tag_rate = "auto"
    else:
        try:
            parsed_tag_rate = float(tag_rate)
        except ValueError:
            typer.echo(f"Invalid tag rate: {tag_rate}", err=True)
            raise typer.Exit(1)

    # Load markers
    try:
        screen_markers = load_markers(markers_json)
    except Exception as e:
        typer.echo(f"Failed to load markers: {e}", err=True)
        raise typer.Exit(1)

    # Create components
    gaze_provider = PupilLabsGazeProvider(pupil_url)
    frame_provider = PupilLabsFrameProvider(pupil_url)

    homography_store = HomographyStore(ttl_ms, max_err_px, min_markers)
    mapper = GazeMapper(homography_store, homography_mode=homography_mode)

    pose_provider = AprilTagPoseProvider(
        frame_provider=frame_provider,
        screen_markers=screen_markers,
        screen_w=screen_w,
        screen_h=screen_h,
        tag_rate=parsed_tag_rate,
        min_markers=min_markers,
    )

    ws_sink = WebSocketSink(port=ws_port)

    # Create queues
    q_gaze = asyncio.Queue(maxsize=512)
    q_frames = asyncio.Queue(maxsize=16)
    q_out = asyncio.Queue(maxsize=512)

    # Create shutdown event
    shutdown_event = asyncio.Event()

    async def run_pipeline():
        """Run the complete pipeline."""
        try:
            # Create tasks
            tasks = [
                gaze_producer(gaze_provider, q_gaze, shutdown_event),
                frame_producer(frame_provider, q_frames, shutdown_event),
                pose_provider_task(pose_provider, homography_store, q_frames, shutdown_event),
                mapper_task(mapper, q_gaze, q_out, shutdown_event),
                websocket_drainer(ws_sink, q_out, shutdown_event),
            ]

            # Start WebSocket server
            ws_task = asyncio.create_task(ws_sink.serve())

            # Run all tasks concurrently
            await asyncio.gather(*tasks, return_exceptions=True)

        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
        finally:
            shutdown_event.set()

            # Close WebSocket sink
            await ws_sink.close()

            # Cancel remaining tasks
            for task in asyncio.all_tasks():
                if not task.done():
                    task.cancel()

    # Run the pipeline
    try:
        asyncio.run(run_pipeline())
    except KeyboardInterrupt:
        logger.info("Pipeline stopped")


if __name__ == "__main__":
    app()
