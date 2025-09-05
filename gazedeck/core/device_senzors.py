# gazedeck/core/device_senzors.py

from gazedeck.core.device_labeling import LabeledDevice


async def get_sensor_urls(labeled_device: LabeledDevice) -> tuple[str, str]:
    """
    Connect to a labeled device's sensors and return their URLs.

    Args:
        labeled_device: The labeled device to connect to

    Returns:
        A tuple of (sensor_gaze_url, sensor_video_url)

    Raises:
        RuntimeError: If either sensor cannot be connected
    """
    print(f"🔗 Connecting to device: {labeled_device.label}")
    status = await labeled_device.device.get_status()
    sensor_gaze = status.direct_gaze_sensor()
    print(f"👁️ Gaze sensor connected: {sensor_gaze.connected}, URL: {sensor_gaze.url}")
    if not sensor_gaze.connected:
        raise RuntimeError("Could not connect to direct gaze sensor for device labeled as %s", labeled_device.label)

    sensor_video = status.direct_world_sensor()
    print(f"📹 Video sensor connected: {sensor_video.connected}, URL: {sensor_video.url}")
    if not sensor_video.connected:
        raise RuntimeError("Could not connect to direct world sensor (FPV camera) for device labeled as %s", labeled_device.label)

    return sensor_gaze.url, sensor_video.url
