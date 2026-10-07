# Start here — the simple route

**Developed by Shivam Singh · MathTech**

This is a local research console with a working synthetic demo. A trained drone
model is required for detecting drones in your own video. No drone weights or
research accuracy results are included.

## Windows: one-time setup

1. Install **Python 3.11 or 3.12** from https://www.python.org/downloads/ . Enable
   **Add Python to PATH** during setup.
2. Install **Node.js 22 LTS** from https://nodejs.org/ . Reopen your terminal.
3. Extract this ZIP, then open the `swarm-drone-tracker` folder. Click the Explorer
   address bar, type `powershell`, and press Enter.
4. Run these commands one line at a time:

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

If you installed Python 3.12, use `py -3.12` on the first line. The explicit Python
path avoids PowerShell activation/execution-policy problems. The first install
needs internet access and downloads the machine-learning libraries.

## Run it

Double-click **START_BACKEND_WINDOWS.bat**, then **START_FRONTEND_WINDOWS.bat**.
Keep both terminal windows open. Open **http://localhost:5173** in your browser.

1. Leave **SOURCE = DEMO / SYNTHETIC**.
2. Click **START**. The first tracker import can take several seconds.
3. Click a green drone bracket or **DR-01** in the track register.
4. Inspect its actual frame crop; change zoom between 2×, 3× and 4×.
5. Try **PAUSE**, **RESUME**, **STOP**, **SETTINGS**, and **RESEARCH**.

The demo produces three synthetic moving drone shapes and synthetic detections,
then uses the real ByteTrack/BoT-SORT tracker. It intentionally hides one object
briefly to demonstrate LOST and REACQUIRED states. It does not use YOLO or report
model accuracy.

## Use your own video

1. Place your trained YOLO model at `weights/drone_detector.pt`.
2. Stop the stream; check the model path in **SETTINGS** and save it.
3. Choose **VIDEO FILE**, upload an MP4, then click **START**.
4. If a CPU is slow, stop, set inference size to **640**, target FPS to **10**, and
   frame width to **960**. Save and start again.

A generic YOLO model trained on COCO does **not** have a drone class. Train your
own model with the commands in `README.md`; labels in the HUD always reflect the
loaded model's actual class names.

The full architecture, Linux/macOS setup, model training, GPU setup, RTSP,
evaluation, tests and troubleshooting are in **README.md**.
