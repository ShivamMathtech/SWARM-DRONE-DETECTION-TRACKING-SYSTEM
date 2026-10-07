# Local API and packet contract

All REST paths below are relative to `http://127.0.0.1:8000`. The frontend uses
`/api` through its proxy. The application supports one active source at a time.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | API health, stream state and configured model availability |
| GET | `/config` | Validated pipeline settings; excludes RTSP credentials |
| POST | `/config` | Complete Settings object; returns 409 while active |
| POST | `/stream/start` | Start request shown below; initialization runs in worker |
| POST | `/stream/stop` | Stop; can return STOPPING if slow device/model is still closing |
| POST | `/stream/pause` | Pause a RUNNING session |
| POST | `/stream/resume` | Resume a PAUSED session |
| POST | `/upload-video` | Multipart `file`; returns generated `video_id` |
| GET | `/tracks` | Latest retained ACTIVE/LOST/REACQUIRED tracks |
| GET | `/stats` | Full latest tracking metadata |
| GET | `/sessions` | Most recent 100 local sessions |
| GET | `/sessions/{id}/report?format=json` | Session configuration, metrics, tracks, events |
| GET | `/sessions/{id}/report?format=csv` | Thresholded raw detections |
| GET | `/sessions/{id}/report?format=csv&kind=tracks` | Filtered visible track boxes for identity evaluation |
| GET | `/research/results` | Latest annotated-data detection report, if present |
| WS | `/ws/tracking` | Plain JSON metadata, no image |
| WS | `/ws/frames` | JPEG and matching metadata in one binary packet |

## Start requests

```json
{"source":"demo"}
```

```json
{"source":"webcam","camera_index":0}
```

```json
{"source":"video","video_id":"UUID_RETURNED_BY_UPLOAD.mp4"}
```

```json
{"source":"rtsp"}
```

RTSP uses only the backend environment variable `RTSP_URL`. The API does not
accept or echo the address. The complete config schema is available at `/docs`.
A source initially enters STARTING. Watch stream state/error for asynchronous
initialization failures; a successful start HTTP response alone is not evidence
that a model or camera loaded successfully.

## Metadata example

Illustrative numeric values below show the schema, not measured performance:

```json
{
  "schema_version": 1,
  "timestamp": 1791360000.0,
  "source_time_s": 2.0,
  "frame_id": 61,
  "session_id": "a-session-identifier",
  "state": "RUNNING",
  "source": "video",
  "demo": false,
  "width": 1280,
  "height": 720,
  "fps": 24.0,
  "inference_ms": 30.0,
  "tracker_ms": 2.0,
  "pipeline_ms": 36.0,
  "dropped_frames": 4,
  "targets": [{
    "id": "DR-01",
    "track_id": 1,
    "class_name": "drone",
    "confidence": 0.94,
    "bbox": [400,220,470,280],
    "center": [435,250],
    "status": "ACTIVE",
    "trajectory": [[432,250],[435,250]],
    "age_s": 1.9,
    "last_seen": 2.0,
    "missed_s": 0.0,
    "velocity_px_s": [15.0,0.0],
    "speed_px_s": 15.0,
    "persistence": 0.96,
    "range_m": null,
    "altitude_m": null,
    "speed_m_s": null
  }],
  "stats": {"precision":null,"recall":null,"map50":null,"map50_95":null,"id_switches":null},
  "events": [],
  "error": null,
  "device": "CPU",
  "model": "weights/drone_detector.pt",
  "raw_detections": []
}
```

`class_name` is the canonical class field, and statuses are uppercase enums.
The sample request in the specification is normalized to this versioned schema;
consumers should not assume a lower-case `tracking` state or a `class` key.

`timestamp` is Unix wall time after the capture read. `source_time_s` is nominal
media time for recorded video/demo or elapsed active capture time for live input.
`frame_id` is a 1-based captured frame sequence, not the count of processed frames.
With dropping/skipping it can jump. Coordinates belong to the resized display
frame. Last-seen locations/velocity in LOST entries are stale observations.

## Binary frame packet

For `/ws/frames`, initial or heartbeat/status messages can be JSON text. Image
messages are one binary WebSocket message:

1. Bytes 0–3: unsigned big-endian 32-bit JSON byte length, N.
2. Bytes 4–(4+N-1): UTF-8 JSON metadata.
3. Remaining bytes: grayscale JPEG corresponding to the same frame ID.

Example Python consumer (requires `websockets` installed with backend requirements):

```python
import asyncio, json, struct
import websockets

async def main():
    async with websockets.connect('ws://127.0.0.1:8000/ws/frames', max_size=8_000_000) as ws:
        async for packet in ws:
            if isinstance(packet, str):
                print(json.loads(packet)['state'])
                continue
            n = struct.unpack('!I', packet[:4])[0]
            metadata = json.loads(packet[4:4+n])
            jpeg_bytes = packet[4+n:]
            print(metadata['frame_id'], len(jpeg_bytes))

asyncio.run(main())
```

The latest state repeats every 10 seconds while idle. Client queues keep one
pending update; sends that remain blocked for three seconds are disconnected.
Browser reconnection uses bounded backoff. A dropped connection leaves a labeled
last frame on screen; it is not presented as live video.
