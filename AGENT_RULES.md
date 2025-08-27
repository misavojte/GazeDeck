# AGENT_RULES.md

## Mission

Build a vendor-agnostic, async Python pipeline that:

- ingests gaze (device-rate, for example 120–200 Hz) and scene frames
- detects AprilTags at a configurable rate (default “auto” = measured scene FPS)
- caches the latest homography (image→screen) under quality gates: TTL, reprojection error, marker count
- maps every gaze sample using the cached homography (so output ≈ original gaze rate)
- emits nested JSON over WebSocket containing scene coords, plane coords, and the homography on every sample

Architecture must follow ports & adapters (hexagonal): core logic is provider-neutral; device-specific code lives in adapters. Keep it non-spaghetti and testable.

---

## Deliverables (repository layout)

Create this structure and implement each file as specified below.

gaze_pipeline/
• core/
 • types.py
 • geometry.py
 • homography_store.py
 • mapping.py
• ports/
 • gaze_provider.py
 • frame_provider.py
 • pose_provider.py
 • sink.py
• adapters/
 • pupil_labs/
  • gaze.py
  • frames.py
  • timebase.py
 • apriltag/
  • tracker.py
  • layouts.py
 • ws/
  • sink.py
• runners/
 • single_process.py
• config/
 • default.yaml
 • markers/screen_4tags.example.json
• tests/
 • test_store.py
 • test_mapping.py
 • test_fpskip.py
 • test_runner_mocked.py
• pyproject.toml
• README.md
• Makefile

---

## Dependencies (pin ranges)

Use Python 3.11 or newer. Pin major versions to avoid CI flakiness.

Runtime:
- pydantic >= 2.6, < 3
- websockets >= 12, < 13
- opencv-python >= 4.9, < 5
- pupil-apriltags >= 1.0, < 2
- numpy >= 1.26, < 3
- typer[all] >= 0.12, < 1
- pyyaml >= 6, < 7

Dev:
- pytest >= 8, < 9
- pytest-asyncio >= 0.23, < 1
- ruff >= 0.4, < 1
- mypy >= 1.10, < 2

---

## Architecture & runtime contracts (hard rules)

1) Decoupled stages as asyncio tasks connected by bounded queues. On QueueFull, drop oldest; never block producers.

2) Preserve original gaze rate. AprilTag detection is throttled; mapping runs at the gaze stream’s rate using the latest valid homography.

3) Provider-neutral core. Only adapters import vendor SDKs. Nothing vendor-specific may appear under core/ or ports/.

4) Nested JSON per sample (non-flat), schema below. When pose is invalid: plane.visible = false, plane.x/y = null, plane.homography = null.

5) Homography validity gates enforced in HomographyStore:
 • visible is True
 • markers ≥ min_markers
 • reproj_px ≤ max_err_px
 • age_ms ≤ ttl_ms

6) Tag rate: CLI/config flag “--tag-rate auto|N”. “auto” means match measured scene FPS (EWMA). Implement a frame-skipper to meet the desired rate.

7) Timebase: carry timestamps as device milliseconds. If a provider lacks device time, use host time in ms. Provide a stub timebase adapter; do not hard-couple core to any vendor sync.

8) Inter-steps ready: new processors can be inserted between queues without changing core types.

---

## WebSocket wire schema (nested JSON)

Every message is a GazeEvent object.

Required fields:

- ts: integer, device timestamp in milliseconds
- conf: float, confidence [0..1]
- scene: object
 • x: float (scene image coordinate)
 • y: float
 • frame: “scene_px” or “scene_norm”
- plane: object
 • uid: string (default single plane “screen-1”)
 • x: float or null (screen pixels)
 • y: float or null
 • on_surface: boolean
 • visible: boolean
 • homography: object or null
  • H: 3x3 matrix (list of lists), image→screen
  • ts: integer ms when estimated
  • age_ms: integer (now − ts)
  • reproj_px: float (mean reprojection error)
  • markers: integer (number of tags used)
  • screen_w, screen_h: integers (screen pixels)
  • img_w, img_h: integers (scene image pixels)
  • seq: integer that increments when homography meaningfully changes

Example (valid mapping):

{
 "ts": 1724662105123,
 "conf": 0.94,
 "scene": { "x": 842.3, "y": 512.9, "frame": "scene_px" },
 "plane": {
  "uid": "screen-1",
  "x": 1291.7, "y": 603.2, "on_surface": true, "visible": true,
  "homography": {
   "H": [[1.01,0.02,-14.3],[-0.01,1.03,8.7],[0.00002,0.00001,1]],
   "ts": 1724662105093, "age_ms": 30, "reproj_px": 0.8, "markers": 4,
   "screen_w": 1920, "screen_h": 1080, "img_w": 1280, "img_h": 720, "seq": 42
  }
 }
}

Example (plane temporarily lost):

{
 "ts": 1724662105980,
 "conf": 0.92,
 "scene": { "x": 901.0, "y": 540.0, "frame": "scene_px" },
 "plane": {
  "uid": "screen-1",
  "x": null, "y": null, "on_surface": false, "visible": false, "homography": null
 }
}

Notes:
- Default single plane UID: “screen-1”.
- If a provider yields normalized scene coords, set frame = “scene_norm” and let the mapper convert using img_w/h from the homography.

---

## Core modules (specifications)

core/types.py (Pydantic v2, frozen models)
- Use ConfigDict(frozen=True) on each model.
- Models and fields:

SceneCoords: x float; y float; frame literal “scene_px” or “scene_norm” (default “scene_px”).

HomographyInfo: H list[list[float]] 3x3; ts int; age_ms int; reproj_px float; markers int; screen_w int; screen_h int; img_w int; img_h int; seq int.

PlaneCoords: uid string; x float or None; y float or None; on_surface bool; visible bool; homography HomographyInfo or None.

GazeSample: ts_ms int; x float; y float; frame literal “scene_px” or “scene_norm” (default “scene_px”); conf float default 1.0.

SceneFrame: ts_ms int; w int; h int. Raw pixel buffer is not included here (it’s yielded alongside this struct by the frame provider).

GazeEvent: ts int; conf float; scene SceneCoords; plane PlaneCoords.

core/geometry.py
- Provide a pure function apply_homography(img_xy, H) → (x, y). Internally use OpenCV perspective transform. No side effects; deterministic.

core/homography_store.py
- Class HomographyStore(ttl_ms, max_err_px, min_markers).
- Methods:
 • set(h) stores the latest homography estimate (model with fields used by HomographyInfo).
 • get_latest(now_ms) returns the latest estimate only if all validity gates pass: visible True; markers ≥ min_markers; reproj_px ≤ max_err_px; age ≤ ttl_ms. Otherwise returns None.

core/mapping.py
- Class GazeMapper(store, plane_uid, homography_mode). homography_mode is one of: every, change, none (default every).
- Method map(g, now_ms) returns a GazeEvent:
 • Convert scene coords to pixels if frame == “scene_norm” using img_w/h from the latest homography.
 • If no valid homography: return event with plane.visible false, x/y null, homography null.
 • Else: apply homography to scene pixel coords; bounds check vs screen_w/h; assemble PlaneCoords with HomographyInfo.
 • Maintain a tolerant homography change detector: two 3×3 matrices are considered the same if allclose with rtol 1e-6 and atol 1e-8. Increment seq only when a meaningful change occurs.
 • Honor homography_mode:
  – every: include full HomographyInfo every sample
  – change: include full HomographyInfo only when seq changes; otherwise include a minimal object that at least carries the current seq (document in README)
  – none: set plane.homography = null even when visible (payload reduction)

---

## Ports (interfaces)

ports/gaze_provider.py
- Protocol IGazeProvider with async method stream() yielding GazeSample.

ports/frame_provider.py
- Protocol IFrameProvider with async method stream() yielding tuples (SceneFrame, ndarray_bgr). Do not serialize frames.

ports/pose_provider.py
- Protocol ISurfacePoseProvider with async method stream() yielding HomographyEstimate objects (fields required to populate HomographyInfo plus img_w/h). The adapter may define HomographyEstimate as a Pydantic model or dataclass.

ports/sink.py
- Protocol ISink with async method emit(msg: GazeEvent).

---

## Adapters (specifications)

adapters/pupil_labs/gaze.py
- Implement PupilLabsGazeProvider (IGazeProvider).
- Use the official async iterator receive_gaze_data(url, run_loop=True) with auto-reconnect; yield GazeSample with ts_ms from timestamp_unix_seconds (ms), x, y, frame = “scene_px”, and available confidence.

adapters/pupil_labs/frames.py
- Implement PupilLabsFrameProvider (IFrameProvider).
- Use receive_video_frames(url, run_loop=True). For each frame, read timestamp_unix_seconds (ms), width/height, and convert to an ndarray in BGR. Yield (SceneFrame, ndarray_bgr).

adapters/apriltag/layouts.py
- Load screen config JSON: contains plane_id, screen_width/height, and markers dict mapping tag id to four screen pixel corners in the order TL, TR, BR, BL.
- Provide load_screen_config(path) returning ScreenConfig NamedTuple with plane_id, screen_width, screen_height, and markers dict.

adapters/apriltag/tracker.py
- Implement AprilTagPoseProvider (ISurfacePoseProvider).
- Constructor parameters: frame_provider; screen_config (ScreenConfig); tag_rate ("auto" or float Hz); ransac_px; min_markers.
- Internals:
 • FPSMeter using EWMA to estimate measured scene FPS from frame timestamps
 • FrameSkipper to keep a fraction of frames so effective processed rate ≈ desired; desired = measured if tag_rate is “auto”, else desired = tag_rate
 • Detect tags with pupil_apriltags.Detector (family “tag36h11”).
 • Build correspondences between image corners and screen corners for tag ids present in screen_markers.
 • Compute homography H for image→screen using cv2.findHomography with RANSAC threshold ransac_px.
 • Compute mean reprojection error in screen pixels.
 • Emit HomographyEstimate with: ts_ms now; H_img_to_screen; visible True; reproj_px; markers used; screen_w/h; img_w/h.
 • If not enough points or homography fails, you may skip emitting or emit visible False.

adapters/ws/sink.py
- Implement WebSocketSink (ISink).
- Provide serve(host, port) that accepts clients and keeps a set of active connections; ignore inbound messages; send ping periodically.
- emit(msg) JSON-encodes the provided GazeEvent and sends to all active clients; remove dead clients on error.
- No subscription protocol initially; all clients receive the same stream.

---

## Runner (single process)

runners/single_process.py
- Implement a Typer CLI with flags:
 • --provider (default pupil-labs)
 • --screen-w INT, --screen-h INT
 • --markers-json PATH
 • --tag-rate auto or FLOAT
 • --ttl-ms INT (default 300)
 • --max-err-px FLOAT (default 2.0)
 • --min-markers INT (default 3)
 • --ws-port INT (default 8765)
 • --homography-mode one of: every, change, none (default every)

- Queues and sizes:
 • q_gaze capacity 512
 • q_frames capacity 16
 • q_out capacity 512

- Drop-oldest policy: define a helper that attempts put_nowait; on QueueFull, get_nowait once (ignore if empty) and then put_nowait. Use this helper in every producing task.

- Tasks:
 1) Gaze producer: iterate IGazeProvider.stream() and push to q_gaze with drop-oldest.
 2) Frame producer: iterate IFrameProvider.stream() and push (SceneFrame, ndarray) to q_frames with drop-oldest.
 3) Pose provider: consume the most recent frame at configured tag rate (using FPSMeter and FrameSkipper), compute homography, and call store.set(h).
 4) Mapper: drain q_gaze; for each GazeSample call GazeMapper.map(sample, now_ms) and push the resulting GazeEvent to q_out with drop-oldest.
 5) WebSocket: run WebSocketSink.serve(host, port) concurrently with a queue-drainer that consumes q_out and calls sink.emit(event).

- Measured scene FPS for auto tag rate: update EWMA using frame timestamps; target rate = measured FPS. If desired rate ≥ measured, process every frame; otherwise skip fractionally.

---

## Config files

config/default.yaml (example values)

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

config/markers/screen_4tags.example.json

Note: order MUST be TL, TR, BR, BL in screen pixels.

{
 "42": [[0,0],[960,0],[960,540],[0,540]],
 "43": [[960,0],[1920,0],[1920,540],[960,540]],
 "44": [[0,540],[960,540],[960,1080],[0,1080]],
 "45": [[960,540],[1920,540],[1920,1080],[960,1080]]
}

---

## Makefile targets (required)

setup: create venv, upgrade pip, install package in editable mode with dev extras
fmt: ruff format the repository
lint: ruff check (lint)
typecheck: mypy on gaze_pipeline
test: pytest in quiet mode
run: invoke runners.single_process with typical arguments (screen size, markers, tag-rate auto, ws-port, homography-mode)

---

## Tests (must pass without a real device)

test_store.py
- Valid homography passes gates; stale (age > ttl_ms) returns None.
- markers < min_markers or reproj_px > max_err_px returns None.

test_mapping.py
- With identity homography (image equals screen), mapping returns same coordinates; on_surface true for in-bounds and false for out-of-bounds.
- With frame = scene_norm, verify pixel conversion using img_w/h from homography.

test_fpskip.py
- Given measured 60 Hz and desired 15 Hz, FrameSkipper keeps roughly 25 percent ± 10 percent.
- For auto mode, desired equals measured so the skipper keeps all frames.

test_runner_mocked.py
- Mock gaze stream at 200 Hz (async generator).
- Mock frame stream at 30 Hz with constant valid homography.
- Assert the sink (use a fake sink) receives GazeEvent messages at approximately the gaze rate while homography is valid.
- Invalidate the homography (for example set markers to 0) and assert subsequent events have plane.visible false and plane.x/y null.

---

## README content (minimum)

- Overview: decoupled stages preserve original gaze rate; AprilTag detection is throttled.
- Install and run: Makefile setup and run commands; CLI flags.
- WebSocket message schema (copy the JSON structure above).
- How to point at a real provider (Pupil Labs) vs mocked tests.
- How to change tag-rate and homography quality thresholds.
- How to replace adapters to support a new vendor.

---

## Quality gates (self-check before each commit)

- No producer blocks on queue operations; always use drop-oldest helper.
- HomographyStore.get_latest(now_ms) enforces TTL, markers, reprojection error.
- GazeMapper.map always returns a GazeEvent (never None).
- Homography seq increments only on meaningful change (tolerant allclose rule).
- No vendor imports in core/ or ports/.
- Public methods have docstrings including units (px, ms).
- Ruff linting, MyPy typecheck, and all tests pass.

---

## Implementation order (follow strictly)

1) Scaffold repo, pyproject.toml, Makefile, basic README.md.
2) Implement core/types.py (models described above).
3) Implement core/geometry.py and core/homography_store.py.
4) Implement core/mapping.py with homography_mode and tolerant seq logic.
5) Define ports/ protocols.
6) Implement adapters/apriltag (layouts loader; tracker with FPSMeter and FrameSkipper).
7) Implement adapters/ws/sink.py.
8) Implement adapters/pupil_labs (gaze and frames) with auto-reconnect run_loop=True.
9) Implement runners/single_process.py using Typer; wire queues and tasks; add CLI flags.
10) Add tests under tests/ using mocks and synthetic data.
11) Finish README and config/default.yaml; ensure “make run” works.

---

## Kickoff prompt (for Cursor)

Implement the project “gaze_pipeline” exactly per AGENT_RULES.md.
Use the specified repo layout, dependencies, frozen Pydantic v2 models, bounded queues with drop-oldest, AprilTag pose at configurable rate (auto = scene FPS), and nested WS JSON including scene, plane, and full homography each sample.
Follow the Implementation order and Quality gates.
Deliver runnable code with passing tests and a working “make run”.