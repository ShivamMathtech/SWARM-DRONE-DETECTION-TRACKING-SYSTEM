# SWARM DRONE DETECTION & TRACKING SYSTEM

**A simple local EO/VIS observation console · MathTech**  
**Developed by Shivam Singh · I HAVE NO LIMITATION**

A connected Python + React research application for drone detection, multi-object
tracking, actual video crops and session analytics. Its interface follows the
supplied grayscale/neon-green reference: full camera view, thin crosshair,
corner brackets, persistent IDs, observed trajectories and a seeker-style zoom.
The interface uses a Canvas HUD and compact React controls.

**New to setup? Start with [START_HERE.md](START_HERE.md).**

The built-in demo runs without weights or a camera. Real input uses Ultralytics
YOLO with ByteTrack or BoT-SORT. A trained drone checkpoint and an annotated
research dataset are **external inputs**, not included in this source package.
There is no fake `.pt` file and no invented accuracy result.

This software performs observation, detection, classification, localization in
image coordinates, tracking and research analytics. It has no vehicle-control,
weapon, engagement, interception or actuation interface.

## What is connected

- Webcam on the backend computer, uploaded video, configured RTSP, and synthetic demo.
- Configurable YOLO weights, class filter, confidence/NMS IoU, image size, CPU/CUDA.
- Real Ultralytics ByteTrack and BoT-SORT with class-separated association pools.
- Session-local `DR-01`, `DR-02`, … IDs; ACTIVE, LOST and REACQUIRED states.
- Dashed observed paths, fading, selected-track details, image velocity in px/s.
- Clickable brackets and track list; 2×/3×/4× crop of the exact displayed frame.
- Start, stop, pause, resume, reconnect, full-screen video and debug boxes.
- SQLite sessions, observations, raw detections, events and saved configuration.
- CSV/JSON session exports; actual labeled-data precision/recall/mAP evaluation.
- Ground-truth identity diagnostics and reproducible training/evaluation scripts.
- Backend tests and browser tests, including an actual YOLO inference path.

## 1. Architecture

```mermaid
flowchart TD
    A[Webcam / video / RTSP] --> B[Latest-frame capture]
    B --> C[YOLO detections]
    C --> D[ByteTrack / BoT-SORT]
    D --> E[Track history and image motion]
    E --> F[Frame and metadata packet]
    E --> G[SQLite observations]
    F --> H[React Canvas HUD]
    H --> I[Selection and actual frame crop]
    G --> J[CSV / JSON research export]
    K[Synthetic demo frames and detections] --> D
```

There are two long-lived worker threads per active session: capture and vision.
Only one source/session runs at a time. FastAPI stays responsive while inference
runs. A single-slot capture buffer favors fresh frames when inference is slower
than input. Each WebSocket subscriber also has a one-packet queue. Slow clients
skip old packets instead of creating an unlimited backlog.

The main browser uses `/ws/frames`: each binary message contains a 4-byte
big-endian JSON length, UTF-8 metadata and a JPEG from the **same processed frame**.
This avoids brackets drifting across unrelated camera frames. There is also a
plain-JSON `/ws/tracking` endpoint for research clients. No base64 video is used.
The browser keeps only the latest pending decode and renders all HUD primitives
with Canvas. No browser-side inference is needed.

Low-score YOLO candidates (down to 0.10) are retained for ByteTrack's second
association pass. Your confidence threshold controls new-track creation and
high-confidence detection exports. An existing track may survive a lower score;
it is shown in amber. This is intentional ByteTrack behavior, not a broken slider.
BoT-SORT uses optical-flow camera-motion compensation, with appearance ReID off.
Tracking is best effort: occlusion, similar objects, sudden movement and low frame
rates can cause new IDs or ID switches. There is no guaranteed identity recovery. The application also caps retained
histories at max(64, 2 × max detections), retiring the oldest lost histories
first if noisy inputs exceed that memory bound.

## 2. Folder structure

```text
swarm-drone-tracker/
  START_HERE.md
  README.md
  START_BACKEND_WINDOWS.bat
  START_FRONTEND_WINDOWS.bat
  .env.example
  .gitignore
  .dockerignore
  LICENSE
  backend/
    requirements.txt
    requirements-dev.txt
    Dockerfile
    app/
      main.py                     FastAPI lifecycle, origin guard
      config.py                   validated pipeline settings and local paths
      api/routes.py               REST, upload, export and WebSocket endpoints
      detection/yolo_detector.py  YOLO adapter and bbox parsing
      tracking/tracker.py         ByteTrack/BoT-SORT, lifecycle, history
      video/stream.py             bounded capture worker
      video/engine.py             vision worker, encoding, publishing
      video/demo.py               deterministic synthetic camera scene
      analytics/metrics.py        measured session metrics
      models/schemas.py          API / target / WebSocket schemas
      utils/database.py          SQLite schema and transactions
  frontend/
    package.json
    package-lock.json
    vite.config.ts
    tsconfig.json
    Dockerfile
    nginx.conf
    playwright.config.cjs
    e2e/console.spec.cjs
    src/
      App.tsx
      main.tsx
      style.css
      components/
        HudLayout.tsx
        CameraView.tsx             camera and actual seeker crop
        ControlPanel.tsx
        TargetManager.tsx          details, register and events
        Settings.tsx
      hud/draw.ts                 reticle, brackets, paths and hit testing
      pages/Research.tsx
      services/api.ts
      services/stream.ts           synchronized packet decoding
      store/useStore.ts
      types/index.ts
  weights/README.md                place trusted drone_detector.pt here
  dataset/
    data.yaml
    images/{train,val,test}/
    labels/{train,val,test}/
  scripts/
    common.py
    train.py
    evaluate.py
    evaluate_tracking.py
    make_sample_video.py
  tests/
    conftest.py
    test_detection.py
    test_tracker.py
    test_api.py
    test_research.py
    test_yolo_integration.py
    prepare_e2e.py
  docs/
    API.md
    VALIDATION.md
    console-preview.png
  docker-compose.yml
  pytest.ini
```

At runtime `data/` stores `swarm.sqlite3`, uploaded files, reports and configuration.
It is created automatically and excluded from source control. The database uses
SQLite WAL and short transactions. No video recording is performed automatically;
uploaded input files are retained locally. Uploaded files are assigned UUID names.

## 3. Installation — Windows PowerShell

Use Python **3.11 or 3.12**, Node.js **22 LTS**, and a recent desktop browser.
A Python virtual environment avoids system package conflicts. The CPU install is
the simplest way to start. Installation requires internet; the demo does not
need internet once dependencies are installed.

Open PowerShell **inside the extracted project folder**:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Copy-Item .env.example .env
cd frontend
npm install
cd ..
```

Use `py -3.12` if that is the Python version you installed. No activation command
is required when using these explicit executable paths.

Run backend in terminal A:

```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open terminal B at the project root, then run:

```powershell
cd frontend
npm run dev
```

Visit **http://localhost:5173**. Select **DEMO / SYNTHETIC** and press **START**.
Both terminals must stay open. Ctrl+C stops each server. The included Windows
`.bat` launchers are convenient after the one-time install; they run the backend
without the development reloader.

With an activated environment, the requested backend command also works:

```powershell
cd backend
python -m uvicorn app.main:app --reload
```

## 4. Installation — Linux / macOS

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
# Linux CPU build:
python -m pip install torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r backend/requirements.txt
cp .env.example .env
cd frontend
npm install
cd ..
```

On macOS install PyTorch from the default index instead of the Linux CPU index:
`python -m pip install torch==2.7.1 torchvision==0.22.1`. This app selects CPU on
macOS; MPS inference is not exposed. On Linux, OpenCV may need `libgl1` and
`libglib2.0-0` from your distribution's package manager.

In separate terminals with the environment activated:

```bash
cd backend
python -m uvicorn app.main:app --reload
```

```bash
cd frontend
npm run dev
```

## 5. Input sources

| Source | Setup | Behavior |
|---|---|---|
| Demo | No camera or weights | Synthetic frames/detections → real tracker → full HUD. Always labeled DEMO. |
| Video file | Upload MP4/AVI/MOV/MKV/WebM; install weights | Runs real YOLO, paces playback by nominal source FPS, stops at EOF. |
| Webcam | Device attached to backend computer, index 0 initially | OpenCV device capture. The browser does not request webcam permissions. |
| RTSP / IP camera | Set `RTSP_URL` in `.env`, restart backend | OpenCV FFmpeg stream adapter, read/open timeouts; credentials stay on backend. |

Pause freezes file/demo capture. For a live camera the capture worker drains
frames during pause so resume does not intentionally replay a queue of old video.
Stop completes a session. Restarting starts a new session and resets public IDs.

For RTSP, edit `.env` locally:

```dotenv
RTSP_URL=rtsp://USERNAME:PASSWORD@CAMERA_HOST:554/STREAM_PATH
```

This is a format example. URL-encode reserved characters in credentials. Do not
paste credentials into frontend fields or screenshots. The backend never returns
the RTSP address through configuration, errors, SQLite session data or WebSockets.
Restart after changing `.env`; use STOP/START to retry a failed connection.

To create a test clip:

```bash
python scripts/make_sample_video.py --output data/synthetic-drone-demo.avi --seconds 15
```

This is a codec/upload fixture with synthetic shapes. A real drone model is not
expected to recognize those shapes reliably. Select built-in Demo to exercise
synthetic tracking without a model.

## 6. Dataset preparation

Place real images and YOLO labels in the corresponding folders. An image
`images/train/frame_001.jpg` needs `labels/train/frame_001.txt`:

```text
0 0.500000 0.400000 0.080000 0.050000
```

Fields are `class_id center_x center_y width height`, normalized to [0,1] relative
to that image. One line per object. Negative images can have an empty label file.
Do not label birds or aircraft as drones to force the desired class output.

The included `dataset/data.yaml` has one class, drone. You can add bird, aircraft,
and helicopter by extending `names` and using consistent class IDs in all labels.
The training/evaluation scripts resolve `path: .` relative to this YAML file.

Split by **flight, camera scene or recording**, not adjacent random frames, to
reduce train/test leakage. Keep the test split untouched while choosing settings.
Record label policy, dataset version, image resolution, class distribution and
occlusion/size conditions. No real images or annotations are bundled.

## 7. Train and install a model

From the project root with the virtual environment active:

```bash
python scripts/train.py --data dataset/data.yaml --model yolov8n.pt --epochs 100 --imgsz 640 --batch 8 --device cpu --seed 42
```

The `--model` argument can be another compatible pretrained detection checkpoint
or a local model/architecture. The first training command may download the named
base weights. Inference in the dashboard never downloads missing models.

For NVIDIA training:

```bash
python scripts/train.py --data dataset/data.yaml --model yolov8n.pt --epochs 100 --imgsz 1280 --batch 4 --device 0 --seed 42
```

The script prints the actual `best.pt` path. Copy it to
`weights/drone_detector.pt`, then stop the stream, set the model path in Settings,
and save. Alternatively append `--install` to the training command; it copies
`best.pt` there only if no model already exists. Save old checkpoints separately.
There is no implied drone accuracy from choosing any particular YOLO model size.

Models are loaded from the project's `weights/` directory. Trusted `.pt` detection
checkpoints are the tested route. The adapter also accepts `.onnx`; install a
compatible `onnxruntime` package separately for ONNX execution. ONNX export/runtime
combinations and CUDA inference were not validated in this environment.

## 8. Configuration and visualization

`.env` supplies initial defaults. After you save Settings, SQLite configuration
is authoritative on later launches. To change an existing setting, use Settings.
`RTSP_URL`, upload limit, allowed origins and data directory remain environment-only.

```dotenv
MODEL_PATH=weights/drone_detector.pt
CONFIDENCE_THRESHOLD=0.40
IOU_THRESHOLD=0.50
IMAGE_SIZE=1280
DEVICE=auto
TRACKER=bytetrack
TRACK_BUFFER=60
LOST_TIMEOUT_S=3.0
MATCH_THRESHOLD=0.80
MAX_TRAJECTORY_POINTS=50
TARGET_FPS=30
FRAME_SKIP=0
STREAM_WIDTH=1280
JPEG_QUALITY=80
MAX_DETECTIONS=100
DEBUG=false
CLASSES=
```

Stop before changing pipeline settings. Input dimensions are scaled down to
`STREAM_WIDTH` if needed; box positions, image speed and exported coordinates
refer to this processed/displayed frame, **not necessarily the original resolution**.
`IMAGE_SIZE` controls the YOLO inference tensor and must be a multiple of 32.
Class filtering is by model class name; leave it empty to display every model class.
The HUD never relabels arbitrary model classes as drone.

`TRACK_BUFFER` counts tracker updates, not camera frames. `LOST_TIMEOUT_S` is
measured on the source timeline. A retained public track expires when either
limit is exceeded. A return after expiry receives a new public ID. Successful
association within the limits may retain the old ID. BoT-SORT's appearance ReID is
intentionally disabled to keep setup simple.

Visual switches apply immediately in the current browser and persist in local
storage: brackets, IDs/classes, detection confidence, paths, fading, crosshair,
scanlines, zoom crop and path thickness. The seeker zoom means source-pixel
magnification into its 320-pixel canvas; 3× uses a roughly 107-pixel-wide crop.
Selected objects have larger brackets.
Green means a tracked observation, amber means low detection confidence, and red
means temporarily lost. A lost bracket is the **last observed location**, not a
new measurement or predicted location. Its crop is blank until reacquisition.

### Measured values and unavailable values

| Display | Definition |
|---|---|
| Detection confidence | YOLO detection score, or an explicitly synthetic score in Demo. Not a calibrated probability of identity correctness. |
| Image speed | Exponential smoothing of center displacement / source elapsed time, in px/s. Includes camera motion and is resolution-dependent. |
| Range, altitude, physical speed | `N/A` / JSON `null`; no sensors or calibration supplied. |
| Persistence | Matched tracker updates / updates since that public ID first appeared. Not tracking accuracy. |
| FPS | Recent processed/published inference frames per second; not the source camera's nominal FPS. |
| YOLO / SIM GEN | Detection stage wall time; Demo bypasses YOLO. |
| Tracker | Multi-object association + lifecycle/history wall time. |
| Pipeline | After capture returns to after grayscale/JPEG encoding. Excludes database write, network and browser. |
| Render | Local Canvas drawing time, sampled once per second. |
| APP E2E | After backend capture returns to browser JPEG decode completion. Requires synchronized host clocks; best interpreted for local use. Excludes camera exposure/driver buffering. |
| Dropped | Captured frames skipped between processed frames, including intentional skips. |

Thirty FPS is a hardware-dependent target, not a guarantee. For CPU start at
640 inference size, 960 frame width, 10 FPS and ByteTrack. If inference is slower,
frames are dropped; the UI never substitutes fake detections. No batched live
inference is used because it would add latency. Offline YOLO evaluation supports
batching. Grayscale is applied for display after inference on the original color
frame. Neither grayscale nor the seeker-style UI implies a thermal sensor.

## 9. GPU setup

The default install is CPU. For a supported NVIDIA GPU and driver, replace the
CPU wheels with the matching pinned CUDA build. Example for the CUDA 12.6 wheels:

```bash
python -m pip install --force-reinstall torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cu126
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"
```

Choose AUTO or CUDA:0 in Settings. The app falls back to CPU, with an event, if
CUDA is unavailable. Reduce image size when GPU memory is insufficient. Consult
[PyTorch's version-specific installation matrix](https://pytorch.org/get-started/previous-versions/)
for the pinned versions and your platform/driver. This package was tested on CPU.

## 10. Research and evaluation

### Detection metrics

```bash
python scripts/evaluate.py --data dataset/data.yaml --model weights/drone_detector.pt --split test --imgsz 1280 --device cpu
```

This calls actual Ultralytics validation against annotations. It produces:

- `data/reports/latest.json` and `latest.csv`: precision, recall, mAP50,
  mAP50–95, validation timings, model SHA-256, model/version and run parameters.
- Validation outputs under `data/reports/validation/`.
- The Research panel displays the latest detection evaluation with its model,
  dataset/split provenance. It is not necessarily the current stream's model.

No annotation means no precision, recall, mAP or ID-switch score in a live session.
The synthetic demo is never used as evidence of real-world detector accuracy.
Evaluate each trained checkpoint before interpreting its live confidence scores.

### Tracking identity diagnostics

Open RESEARCH and download **CSV TRACKS** for a completed session. Annotate the
same source using ground-truth IDs with this header:

```csv
frame_id,gt_id,class_name,x1,y1,x2,y2
1,object_a,drone,100,100,150,130
2,object_a,drone,102,100,152,130
```

Use the **same processed frame dimensions and original 1-based source frame IDs**.
If capture dropped frames, either evaluate the union to measure complete
observation coverage (missing predictions count as misses) or explicitly restrict
both files to the processed frame set and report that protocol. Do not compare
resized predictions with native-size labels.

```bash
python scripts/evaluate_tracking.py --ground-truth annotations.csv --predictions tracks-SESSION.csv --iou 0.5 --max-gap 30
```

This computes class-aware Hungarian IoU matches, precision, recall, misses, false
positives, ID switches and mean ground-truth track coverage. An ID switch is a
change of matched predicted ID within the configured frame gap. Definitions are
stored in `tracking.json`/`tracking.csv`. This diagnostic is **not HOTA or IDF1**;
use an established MOT benchmark implementation for a publication requiring those
standardized metrics. The Research panel's live ID-switch field remains N/A.

**CSV DETECTIONS** contains thresholded raw YOLO observations, with exact assigned
track IDs when available and empty IDs for unconfirmed observations. **CSV TRACKS**
contains the visible filtered track boxes, including low-score rescued tracks.
JSON contains session configuration, summary metrics, tracks and events. Exports
never claim to contain unavailable physical telemetry.

For a paper, include data split policy, label quality checks, hardware, model
hash, settings, seeds, class-wise detection metrics, small-object/occlusion
subsets, identity diagnostic definitions, measured throughput and failure cases.
Compare trackers on the same frozen detector and source frame set. Repeat runs
and report variability rather than selecting only the best outcome.

## 11. API and protocol

Interactive REST documentation: **http://127.0.0.1:8000/docs**.
See [docs/API.md](docs/API.md) for endpoint details and WebSocket examples.
The FastAPI API is at the server root. Vite/Nginx expose it as `/api/*` to the
browser; they proxy `/ws/*` for sockets.

## 12. Tests

Activate your environment and run from the project root:

```bash
python -m pip install -r backend/requirements-dev.txt
python -m pytest
```

Tests cover parsing/clipping, invalid values, bbox conversion, real tracker
association, low-score recovery, class separation, timeout expiry, bounded
trajectory history, config validation, health, source validation, uploads,
WebSockets, pause/resume, persistence/exports and identity metrics.

The real YOLO integration test constructs **untrained weights** from the bundled
architecture without a model download. It creates a synthetic AVI, uploads it,
runs actual YOLO, then validates tracker/WebSocket output. It tests software
plumbing only and removes its temporary model.

For the browser tests, start backend and frontend as described above, and create
the disposable fixtures once:

```bash
python tests/prepare_e2e.py
cd frontend
npx playwright install chromium
npm run test:e2e
npm run build
```

The first browser test checks Demo → HUD → selection/crop → pause/resume → settings
→ exports. The second uploads the fixture video and checks actual YOLO inference
reaches the browser canvas. It restores the prior configuration. You can delete
`weights/smoke-test.pt` and `data/smoke.avi` afterward. They are not drone models or
benchmark data. Tests run serially because the console owns one stream.

See [docs/VALIDATION.md](docs/VALIDATION.md) for checks run on this delivered build
and hardware-dependent paths not exercised here.

## 13. Optional Docker route

```bash
docker compose up --build
```

Open **http://localhost:8080**. Docker runs the CPU backend and a built frontend
through Nginx, with persistent SQLite/uploads in the `swarm-data` volume and
read-only model weights mounted from `weights/`. It is optional; the local
Windows route is simpler for a USB webcam. Host webcams require explicit Linux
container device mapping and are not automatically available in Docker Desktop.
GPU passthrough requires a separate NVIDIA runtime configuration. The provided
Compose path has not been run in this environment.

## 14. Security and operating scope

This is a **single-user local research application**. It has no authentication or
multi-user role system. Default development servers and Compose ports bind to
loopback. Do not expose it publicly without an authenticated TLS reverse proxy
and a deployment review. An Origin allowlist protects browser entry points; it
is not a substitute for authentication.

- Credentials remain in `.env`, which is ignored by Git. No credential input in UI.
- Uploads use generated names, a configurable size limit and a decode check.
- Model paths stay inside `weights/`; load only trusted checkpoints.
- Config fields have validation and limits; changes are rejected while running.
- The UI displays model classes faithfully and makes synthetic data explicit.
- Local observations contain image boxes and timestamps, not personal profiles.
- Stop the app before manually archiving/deleting the local `data/` directory.
  Deleting it removes sessions, uploads and saved configuration.

## 15. Troubleshooting

| Problem | Action |
|---|---|
| `py` / Python not found | Reinstall Python with Add to PATH; reopen terminal. Try `py -3.12` if applicable. |
| PowerShell blocks activation | Use `.venv\Scripts\python.exe` directly, as shown in START_HERE. |
| `npm` not found | Install Node.js and reopen the terminal. |
| UI says CONNECTING | Start backend on port 8000 and frontend on port 5173. Check `/health`. |
| Port already in use | Stop the other process. If changing backend port, also update Vite's proxy. |
| Model unavailable | Place trained weights under `weights/`, stop the stream and update Settings. Demo needs no model. |
| No drones detected | Check the loaded class names, labeled training data, model quality, object size and threshold. A COCO model lacks a drone class. |
| Camera error | Close other camera apps, check OS permissions and try index 0/1. Camera belongs to backend host. If a native driver remains blocked during stop, restart the backend. |
| RTSP fails | Check `.env`, network reachability, credentials, supported codec and stream path; restart backend. |
| Upload fails | Use a valid supported video under the limit; try H.264 MP4 or MJPEG AVI. |
| Video stops early | Decoder may have encountered corruption; re-encode the source and retry. |
| Slow or choppy output | Use smaller model/image size, lower target FPS and frame width; select ByteTrack or enable working CUDA. |
| IDs change after occlusion | Expected association limitation; increase retention cautiously and evaluate with identities. |
| Settings appear unchanged after editing `.env` | Saved SQLite settings take priority. Change them in the panel. |
| CUDA unavailable | Verify the PyTorch wheel and driver; AUTO falls back to CPU with an event. |
| Precision / mAP / ID switches say N/A | Supply annotations and run the evaluation scripts. No live guesses are made. |
| Evaluation dataset not found | Verify paths in data.yaml and that each split contains real images and labels. |
| Docker webcam unavailable | Use the local backend for simplest device access. |

## 16. Research extensions

Useful next steps include stronger small-object training data, sliced inference,
formal MOT/HOTA evaluation, calibrated cameras, measured sensor adapters,
uncertainty calibration and controlled multi-camera experiments. Keep sensors and
units explicit; do not infer physical distance from an uncalibrated bbox.

## References and license

The adapter is built against the **pinned** Ultralytics 8.3.156 API. Official
current documentation may describe newer versions; upgrade through tests.

- [Ultralytics tracking](https://docs.ultralytics.com/modes/track/)
- [ByteTracker API](https://docs.ultralytics.com/reference/trackers/byte_tracker/)
- [BoT-SORT API](https://docs.ultralytics.com/reference/trackers/bot_sort/)
- [Ultralytics detection training/validation](https://docs.ultralytics.com/tasks/detect/)
- [PyTorch version matrix](https://pytorch.org/get-started/previous-versions/)

Project source is released under **AGPL-3.0**, with the full text in `LICENSE`.
Dependencies retain their own licenses; Ultralytics is offered under AGPL-3.0 or
its commercial license. This source package contains no pretrained model weights,
third-party dataset images or bundled dependency binaries.
