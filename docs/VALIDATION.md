# Validation of this build

Date: 7 October 2026. Local Linux environment; Python 3.12.14, PyTorch 2.7.1 CPU,
Ultralytics 8.3.156, OpenCV 4.11.0, Node.js 24.19.0, Chromium 136 via Playwright.
The setup guide recommends Python 3.11/3.12 and Node.js 22.

## Executed checks

- **12 backend tests passed.** Actual ByteTrack and BoT-SORT association,
  class isolation, persistence through brief loss, expiry/new identity,
  low-confidence rescue, bbox/output parsing, config validation, origin guard,
  invalid source/upload handling, actual binary/JSON WebSockets, pause/resume,
  SQLite exports and ground-truth identity diagnostics.
- **2 browser workflows passed.** Full demo flow through selection, real crop,
  moving frames, pause/resume, settings and exports; uploaded AVI through
  actual YOLO inference and the frontend Canvas. No trained weights were used.
- **Frontend production build passed.** Strict TypeScript check plus Vite bundle.
- **Training script smoke run passed.** One epoch of YOLOv8n from the bundled YAML
  architecture on a deliberately tiny synthetic fixture, CPU, 320 px, batch 2.
  A real checkpoint was generated, and the run manifest was written.
- **Detection evaluation script smoke run passed.** The generated checkpoint
  was evaluated against the corresponding tiny synthetic test fixture; JSON and
  CSV reports were produced. All accuracy scores were zero, as expected from a
  one-epoch plumbing fixture. These are not drone research results.
- **Visual inspection completed.** A real browser screenshot of the demo is
  included as `console-preview.png`. It is not a generated design mockup.

The Python test suite's JUnit output is included in `test-results.xml`.
A harmless Starlette/AnyIO deprecation warning appeared during the tests.

## Not established by these checks

- Real-world drone accuracy, small-object recall or ID-switch rates on real flights.
- Sustained 30 FPS across hardware, camera resolutions or network conditions.
- CUDA, ONNX, physical webcam/RTSP devices, Docker or Windows/macOS execution.
- Standardized MOT/HOTA/IDF1 benchmark compliance or production internet hosting.

The browser/YOLO fixtures and the synthetic training checkpoint are intentionally
excluded from the source ZIP. Run the included fixture generator/tests to recreate
them. Trained drone weights and a labeled real dataset remain user-supplied.
