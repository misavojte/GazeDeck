# gazedeck/core/device_senzors.py

from gazedeck.core.device_labeling import LabeledDevice


async def get_sensor_urls(labeled_device: LabeledDevice) -> tuple[str, str, str]:
    """
    Connect to a labeled device's sensors and return their URLs.

    Args:
        labeled_device: The labeled device to connect to

    Returns:
        A tuple of (sensor_gaze_url, sensor_video_url, sensor_imu_url)

    Raises:
        RuntimeError: If any sensor cannot be connected
    """
    print(f"🔗 Connecting to device: {labeled_device.emission_id} {labeled_device.label}")
    status = await labeled_device.device.get_status()

    # Gaze sensor
    sensor_gaze = status.direct_gaze_sensor()
    print(f"👁️ Gaze sensor connected: {sensor_gaze.connected}, URL: {sensor_gaze.url}")
    if not sensor_gaze.connected:
        raise RuntimeError("Could not connect to direct gaze sensor for device %d (%s)", labeled_device.emission_id, labeled_device.label)

    # Video sensor
    sensor_video = status.direct_world_sensor()
    print(f"📹 Video sensor connected: {sensor_video.connected}, URL: {sensor_video.url}")
    if not sensor_video.connected:
        raise RuntimeError("Could not connect to direct world sensor (FPV camera) for device %d (%s)", labeled_device.emission_id, labeled_device.label)

    # IMU sensor
    sensor_imu = status.direct_imu_sensor()
    print(f"🧭 IMU sensor connected: {sensor_imu.connected}, URL: {sensor_imu.url}")
    if not sensor_imu.connected:
        raise RuntimeError("Could not connect to direct IMU sensor for device %d (%s)", labeled_device.emission_id, labeled_device.label)

    return sensor_gaze.url, sensor_video.url, sensor_imu.url
