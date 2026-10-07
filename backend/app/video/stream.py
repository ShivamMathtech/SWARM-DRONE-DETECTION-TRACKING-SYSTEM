"""Single-slot capture: slow inference never creates an ever-growing video queue."""
import os
os.environ.setdefault('OPENCV_FFMPEG_LOGLEVEL', '-8')
import threading
import time
from dataclasses import dataclass
from urllib.parse import urlsplit
import cv2
from app.video.demo import DemoScene
from app.config import DATA_DIR
cv2.setLogLevel(0)

@dataclass
class Frame:
    image: object
    frame_id: int
    source_time: float
    captured_at: float
    captured_mono: float
    demo_detections: object = None

class VideoSource:
    def __init__(self, request, config):
        self.request, self.config = request, config
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.paused = threading.Event()
        self.latest = None
        self.error = None
        self.ended = False
        self.thread = threading.Thread(target=self._capture, name='capture', daemon=True)

    def start(self):
        self.thread.start()

    def snapshot(self):
        with self.lock:
            return self.latest

    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=5)
        return not self.thread.is_alive()

    def _capture(self):
        cap = None
        try:
            kind = self.request.source
            demo = DemoScene(self.config.stream_width, round(self.config.stream_width*9/16)) if kind=='demo' else None
            if not demo:
                if kind == 'webcam':
                    cap = cv2.VideoCapture(self.request.camera_index)
                elif kind == 'video':
                    path = DATA_DIR / 'uploads' / (self.request.video_id or '')
                    if not path.is_file():
                        raise ValueError('VIDEO UNAVAILABLE: upload a video before starting.')
                    cap = cv2.VideoCapture(str(path))
                else:
                    address = os.getenv('RTSP_URL', '')
                    parsed = urlsplit(address)
                    if parsed.scheme not in {'rtsp','rtsps'} or not parsed.hostname:
                        raise ValueError('INVALID RTSP: configure RTSP_URL in the project .env file.')
                    cap = cv2.VideoCapture(address, cv2.CAP_FFMPEG,
                        [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000, cv2.CAP_PROP_READ_TIMEOUT_MSEC, 3000])
                if not cap.isOpened():
                    raise ValueError('CAMERA ERROR: unable to open video source. Check device, file, or RTSP configuration.')
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            fps = self.config.target_fps if demo else float(cap.get(cv2.CAP_PROP_FPS))
            if not 1<=fps<=240:
                fps=30.
            number=0
            deadline=time.monotonic()
            active_start=deadline
            paused_total=0.
            while not self.stop_event.is_set():
                if self.paused.is_set():
                    pause_start=time.monotonic()
                    # Drain live capture while paused, so resuming shows current video.
                    while self.paused.is_set() and not self.stop_event.is_set():
                        if kind in {'rtsp','webcam'}:
                            cap.grab()
                        self.stop_event.wait(.03)
                    paused_total += time.monotonic()-pause_start
                    deadline=time.monotonic()
                    continue
                source_time=number/fps if demo or kind=='video' else time.monotonic()-active_start-paused_total
                if demo:
                    frame,detections=demo.render(source_time)
                    ok=True
                else:
                    ok,frame=cap.read()
                    detections=None
                if not ok or frame is None or frame.size==0:
                    if kind=='video':
                        total=cap.get(cv2.CAP_PROP_FRAME_COUNT)
                        if total>0 and number<total-2:
                            raise ValueError('VIDEO ERROR: decoder stopped before the end of the file. Try re-encoding the video.')
                        break
                    raise ValueError('CAMERA ERROR: stream ended or returned an empty/corrupted frame.')
                if frame.shape[1] > self.config.stream_width:
                    scale=self.config.stream_width/frame.shape[1]
                    frame=cv2.resize(frame,(self.config.stream_width,round(frame.shape[0]*scale)),interpolation=cv2.INTER_AREA)
                number+=1
                sample=Frame(frame,number,source_time,time.time(),time.monotonic(),detections)
                with self.lock:
                    self.latest=sample
                if demo or kind=='video':
                    deadline+=1/fps
                    self.stop_event.wait(max(0,deadline-time.monotonic()))
        except ValueError as e:
            self.error=str(e)
        except Exception:
            # Raw decoder exceptions can contain an authenticated camera URL.
            self.error='VIDEO ERROR: decoding failed. Verify source, codec and connection.'
        finally:
            if cap is not None:
                cap.release()
            self.ended=True
