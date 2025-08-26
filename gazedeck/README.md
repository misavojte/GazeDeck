# GazeDeck

A vendor-agnostic, async Python pipeline for gaze tracking with AprilTag pose estimation.

## Overview

GazeDeck processes gaze data and scene frames to detect AprilTags at a configurable rate and maps every gaze sample using the cached homography, emitting nested JSON over WebSocket.

Key features:
- Decoupled stages preserve original gaze rate
- AprilTag detection is throttled
- Vendor-agnostic core with adapter pattern
- Async architecture with bounded queues

## Installation and Setup

```bash
make setup
```

This creates a virtual environment, installs dependencies, and sets up the package in editable mode.

## Usage

### Quick Start

```bash
make run
```

This runs the pipeline with default settings (1920x1080 screen, auto tag rate, WebSocket on port 8765). The system will automatically discover and connect to available Pupil Labs devices on your network.

### Command Line Options

```bash
python -m gazedeck.runners.single_process --help
```

Available options:
- `--provider`: Gaze provider type (default: pupil-labs)
- `--screen-w`, `--screen-h`: Screen dimensions in pixels
- `--markers-json`: Path to AprilTag marker layout JSON file
- `--tag-rate`: Tag detection rate ("auto" or Hz)
- `--ttl-ms`: Homography time-to-live in milliseconds (default: 300)
- `--max-err-px`: Maximum reprojection error in pixels (default: 2.0)
- `--min-markers`: Minimum markers required for homography (default: 3)
- `--ws-port`: WebSocket server port (default: 8765)
- `--homography-mode`: Homography inclusion mode ("every", "change", "none")

**Note**: Pupil Labs devices are automatically discovered on the network. No manual URL configuration is required.

### Device Discovery

GazeDeck automatically discovers Pupil Labs devices on your network using the official Pupil Labs Real-Time API discovery mechanism:

1. **Network Scanning**: Scans for available Pupil Labs devices
2. **Device Selection**: Automatically connects to the first available device
3. **Sensor Validation**: Verifies that required sensors (gaze and world camera) are connected
4. **URL Retrieval**: Gets the proper streaming URLs from the device status

#### Shared Device Provider Architecture

GazeDeck uses a **shared device provider** pattern following hexagonal architecture principles:

**Abstract Interface** (`ports/device_provider.py`):
- **`IDeviceProvider`**: Abstract interface for device providers
- **`SensorURLs`**: Data structure containing sensor URLs and device information

**Concrete Implementation** (`adapters/pupil_labs/device.py`):
- **`PupilLabsDevice`**: Pupil Labs specific implementation of IDeviceProvider

**Provider Usage**:
- **`PupilLabsGazeProvider`**: Uses shared device provider for gaze streaming
- **`PupilLabsFrameProvider`**: Uses shared device provider for video streaming

This architecture ensures:
- **Consistency**: Both providers connect to the same device
- **Efficiency**: Single device discovery operation
- **Maintainability**: Centralized device management logic
- **Extensibility**: Easy to add new device provider implementations
- **Resource Management**: Proper cleanup of device connections

If multiple devices are present, GazeDeck will connect to the first device it discovers. For more advanced multi-device scenarios, the codebase can be extended to support device selection.

#### Troubleshooting Device Discovery

If device discovery fails:

1. **Ensure Pupil Labs Companion App is running** on the device
2. **Check network connectivity** between your computer and the Pupil Labs device
3. **Verify firewall settings** allow network discovery
4. **Check device logs** for connection issues
5. **Try restarting** both the Pupil Labs device and Companion App

The system will timeout after 10 seconds if no device is found and provide clear error messages.

### Configuration File

You can also configure the pipeline using `config/default.yaml`:

```yaml
provider: pupil-labs
screen:
  width_px: 1920
  height_px: 1080
homography:
  ttl_ms: 300
  max_reproj_px: 2.0
  min_markers: 3
tag_rate: auto
ws:
  port: 8765
markers_json: config/markers/screen_4tags.example.json
homography_mode: every
```

## WebSocket Message Schema

Every message is a `GazeEvent` object with the following nested JSON structure:

```json
{
  "ts": 1724662105123,
  "conf": 0.94,
  "scene": {
    "x": 842.3,
    "y": 512.9,
    "frame": "scene_px"
  },
  "plane": {
    "uid": "screen-1",
    "x": 1291.7,
    "y": 603.2,
    "on_surface": true,
    "visible": true,
    "homography": {
      "H": [[1.01,0.02,-14.3],[-0.01,1.03,8.7],[0.00002,0.00001,1]],
      "ts": 1724662105093,
      "age_ms": 30,
      "reproj_px": 0.8,
      "markers": 4,
      "screen_w": 1920,
      "screen_h": 1080,
      "img_w": 1280,
      "img_h": 720,
      "seq": 42
    }
  }
}
```

When pose is invalid:

```json
{
  "ts": 1724662105980,
  "conf": 0.92,
  "scene": {
    "x": 901.0,
    "y": 540.0,
    "frame": "scene_px"
  },
  "plane": {
    "uid": "screen-1",
    "x": null,
    "y": null,
    "on_surface": false,
    "visible": false,
    "homography": null
  }
}
```

## Architecture

### Core Components

- **core/**: Business logic, types, and geometry operations
  - `types.py`: Pydantic v2 models for all data structures
  - `geometry.py`: Homography transformation utilities
  - `homography_store.py`: Homography caching with quality gates
  - `mapping.py`: Gaze-to-screen mapping with configurable homography inclusion

- **ports/**: Interfaces for providers and sinks
  - `gaze_provider.py`: Gaze data provider protocol
  - `frame_provider.py`: Scene frame provider protocol
  - `pose_provider.py`: Surface pose provider protocol
  - `device_provider.py`: Device provider protocol for device discovery and management
  - `sink.py`: Event sink protocol

- **adapters/**: Vendor-specific implementations
  - `pupil_labs/`: Pupil Labs Real-Time API adapters
    - `device.py`: Shared device management and discovery
    - `gaze.py`: Gaze data streaming using shared device provider
    - `frames.py`: Video frame streaming using shared device provider
    - `timebase.py`: Timebase utilities
  - `apriltag/`: AprilTag detection and pose estimation
  - `ws/`: WebSocket event broadcasting

- **runners/**: Application entry points
  - `single_process.py`: Main CLI application with async pipeline orchestration

## Development

### Testing

```bash
make test
```

Run tests without requiring real hardware devices.

### Linting and Type Checking

```bash
make lint
make typecheck
```

### Adding New Providers

To support a new eye tracking vendor:

1. Implement `IGazeProvider` in `adapters/your_vendor/gaze.py`
2. Implement `IFrameProvider` in `adapters/your_vendor/frames.py`
3. Update the provider selection logic in `runners/single_process.py`
4. Add any vendor-specific configuration options

### Modifying Tag Detection Rate

- **auto**: Match measured scene FPS (recommended)
- **N**: Fixed rate in Hz (e.g., 15 for lower CPU usage)
- Configure via `--tag-rate` CLI flag or config file

### Adjusting Homography Quality Gates

- **ttl_ms**: Maximum age of homography before invalidation
- **max_reproj_px**: Maximum reprojection error threshold
- **min_markers**: Minimum detected markers required
- Lower values increase accuracy but may reduce stability

### Homography Modes

- **every**: Include full homography in every event (maximum precision)
- **change**: Include homography only when it changes (reduced payload)
- **none**: Omit homography (minimum payload, assumes client-side caching)

## Dependencies

Runtime dependencies are pinned for CI stability:
- `pydantic >= 2.6, < 3`
- `websockets >= 12, < 13`
- `opencv-python >= 4.9, < 5`
- `pupil-apriltags >= 1.0, < 2`
- `pupil-labs-realtime-api >= 1.0, < 2`
- `numpy >= 1.26, < 3`
- `typer[all] >= 0.12, < 1`
- `pyyaml >= 6, < 7`

Development dependencies:
- `pytest >= 8, < 9`
- `pytest-asyncio >= 0.23, < 1`
- `ruff >= 0.4, < 1`
- `mypy >= 1.10, < 2`
