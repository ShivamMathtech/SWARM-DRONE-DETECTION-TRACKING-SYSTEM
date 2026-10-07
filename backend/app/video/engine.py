"""Worker-owned vision state and bounded, frame-synchronized WebSocket publishing."""
import asyncio
import json
import struct
import threading
import time
import uuid
from collections import deque
import cv2
from app.analytics.metrics import Metrics
from app.config import Settings
from app.detection.yolo_detector import YoloDetector
from app.models.schemas import TrackingMessage
from app.tracking.tracker import MultiObjectTracker
from app.video.stream import VideoSource

class Engine:
    def __init__(self, db, settings, loop):
        self.db, self.settings, self.loop=db,settings,loop
        self.lock=threading.RLock()
        self.state='STOPPED'
        self.thread=None
        self.capture=None
        self.stop_event=threading.Event()
        self.pause_event=threading.Event()
        self.events=deque(maxlen=50)
        self.event_sequence=0
        self.subscribers=set()
        self.last_jpeg=b''
        self.last_packet=None
        self.session_id=None
        self.message=self._empty()

    def _empty(self):
        return TrackingMessage(timestamp=time.time(),source_time_s=0,frame_id=0,session_id=None,
            state=self.state,source='none',demo=False,width=1280,height=720,fps=0,
            inference_ms=0,tracker_ms=0,pipeline_ms=0,dropped_frames=0,targets=[],stats={},events=[]).model_dump()

    def snapshot(self):
        with self.lock:
            return {**self.message,'state':self.state,'events':list(self.events)}

    def subscribe(self):
        queue=asyncio.Queue(maxsize=1)
        self.subscribers.add(queue)
        return queue

    def _distribute(self, msg, packet):
        for q in list(self.subscribers):
            if q.full():
                q.get_nowait()
            q.put_nowait((msg,packet))

    def publish(self, msg, jpeg=None):
        with self.lock:
            msg={**msg,'state':self.state,'events':list(self.events)}
            self.message=msg
            if jpeg is not None:
                self.last_jpeg=jpeg
            raw=json.dumps(msg,separators=(',',':'),allow_nan=False).encode()
            packet=struct.pack('!I',len(raw))+raw+self.last_jpeg if self.last_jpeg else None
            self.last_packet=packet
        if not self.loop.is_closed():
            self.loop.call_soon_threadsafe(self._distribute,msg,packet)

    def event(self,level,message):
        with self.lock:
            self.event_sequence+=1
            ev=dict(id=self.event_sequence,timestamp=time.time(),level=level,message=message)
            self.events.append(ev)
        self.db.event(self.session_id,ev)

    def start(self,request):
        with self.lock:
            if self.thread and self.thread.is_alive():
                raise RuntimeError('Stop the current stream before starting another.')
            if self.capture and self.capture.thread.is_alive():
                raise RuntimeError('The camera driver is still closing. Retry shortly or restart the backend.')
            self.state='STARTING'
            self.stop_event.clear()
            self.pause_event.clear()
            self.events.clear()
            self.last_jpeg=b''
            self.last_packet=None
            self.session_id=uuid.uuid4().hex
            self.message={**self._empty(),'session_id':self.session_id,'source':request.source,'demo':request.source=='demo'}
            self.db.start_session(self.session_id,request.source,self.settings)
            self.thread=threading.Thread(target=self._run,args=(request,),name='vision',daemon=True)
            self.thread.start()
            self.publish(self.message)
        return self.snapshot()

    def pause(self):
        with self.lock:
            if self.state!='RUNNING':
                raise RuntimeError('Only a running stream can be paused.')
            self.pause_event.set()
            if self.capture:
                self.capture.paused.set()
            self.state='PAUSED'
        self.event('INFO','Stream paused')
        self.publish(self.snapshot())

    def resume(self):
        with self.lock:
            if self.state!='PAUSED':
                raise RuntimeError('The stream is not paused.')
            if self.capture:
                self.capture.paused.clear()
            self.pause_event.clear()
            self.state='RUNNING'
        self.event('INFO','Stream resumed')
        self.publish(self.snapshot())

    def stop(self):
        with self.lock:
            thread=self.thread
            if thread and thread.is_alive():
                self.state='STOPPING'
                self.stop_event.set()
                self.pause_event.clear()
                if self.capture:
                    self.capture.stop_event.set()
            elif self.state!='ERROR':
                self.state='STOPPED'
        if thread and thread.is_alive():
            thread.join(timeout=6)
        self.publish(self.snapshot())
        return self.snapshot()

    def _run(self,request):
        error=None
        try:
            config=self.settings.model_copy(deep=True)
            demo=request.source=='demo'
            self.event('INFO','DEMO: synthetic frames and detections; real multi-object tracker.' if demo else 'Loading configured YOLO model')
            detector=None if demo else YoloDetector(config)
            names={0:'drone'} if demo else detector.names
            tracker=MultiObjectTracker(config,names)
            if detector and detector.warning:
                self.event('WARN',detector.warning)
            if detector and not any('drone' in name.lower() for name in names.values()):
                self.event('WARN','Model has no drone class. Displaying its actual classes; load custom drone weights.')
            self.capture=VideoSource(request,config)
            self.capture.start()
            metrics=Metrics()
            previous_id=0
            last_inference=0.
            dropped=0
            while not self.stop_event.is_set():
                if self.pause_event.is_set():
                    self.stop_event.wait(.03)
                    continue
                sample=self.capture.snapshot()
                if self.capture.error:
                    raise ValueError(self.capture.error)
                if sample is None or sample.frame_id==previous_id:
                    if self.capture.ended:
                        break
                    self.stop_event.wait(.005)
                    continue
                if sample.frame_id-previous_id<=config.frame_skip or time.monotonic()-last_inference<1/config.target_fps:
                    # Process the final file frame even when it falls in a skip interval.
                    if not self.capture.ended:
                        self.stop_event.wait(.003)
                        continue
                last_inference=time.monotonic()
                if previous_id:
                    dropped+=max(0,sample.frame_id-previous_id-1)
                previous_id=sample.frame_id
                detect_start=time.monotonic()
                detections=sample.demo_detections if demo else detector.detect(sample.image)
                after_detect=time.monotonic()
                targets=tracker.update(detections,sample.image,sample.source_time)
                after_track=time.monotonic()
                for level,text in tracker.new_events:
                    self.event(level,text)
                gray=cv2.cvtColor(sample.image,cv2.COLOR_BGR2GRAY)
                ok,encoded=cv2.imencode('.jpg',gray,[cv2.IMWRITE_JPEG_QUALITY,config.jpeg_quality])
                if not ok:
                    raise ValueError('VIDEO ERROR: JPEG encoding failed.')
                latency=(time.monotonic()-sample.captured_mono)*1000
                high_detections=[d for d in detections if d.confidence>=config.confidence_threshold]
                stats=metrics.update(time.monotonic(),latency,high_detections,targets)
                stats['unique_tracks']=tracker.serial
                stats['reacquisitions']=tracker.total_reacquisitions
                with self.lock:
                    if self.state=='STARTING':
                        self.state='RUNNING'
                msg=TrackingMessage(timestamp=sample.captured_at,source_time_s=sample.source_time,
                    frame_id=sample.frame_id,session_id=self.session_id,state=self.state,source=request.source,
                    demo=demo,width=sample.image.shape[1],height=sample.image.shape[0],fps=stats['fps'],
                    inference_ms=round((after_detect-detect_start)*1000,2),
                    tracker_ms=round((after_track-after_detect)*1000,2),pipeline_ms=round(latency,2),
                    dropped_frames=dropped,targets=targets,stats=stats,events=[],
                    device='CPU' if demo else ('CUDA:0' if detector.device=='0' else 'CPU'),
                    model='SYNTHETIC / NO YOLO' if demo else config.model_path,
                    raw_detections=[dict(bbox=d.bbox,confidence=d.confidence,class_name=d.class_name) for d in detections] if config.debug else []).model_dump()
                self.db.record(msg,high_detections,tracker.associations)
                self.publish(msg,encoded.tobytes())
        except FileNotFoundError as e:
            error=str(e)
        except ValueError as e:
            # Only explicitly constructed application errors are exposed.
            safe=str(e)
            error=safe if safe.startswith(('MODEL UNAVAILABLE','CAMERA ERROR','VIDEO ERROR','VIDEO UNAVAILABLE','INVALID RTSP','The selected class')) else 'PIPELINE ERROR: configuration or model output is incompatible. Check model and input.'
        except ImportError:
            error='DEPENDENCY ERROR: install backend/requirements.txt in your active Python environment.'
        except Exception:
            error='INFERENCE ERROR: check the trusted model, device memory, codec and installed dependency versions.'
        finally:
            if self.capture:
                closed=self.capture.stop()
                if closed:
                    self.capture=None
                else:
                    error='CAMERA ERROR: driver did not close within 5 seconds. Retry shortly or restart the backend.'
            with self.lock:
                self.state='ERROR' if error else 'STOPPED'
                self.message={**self.message,'error':error}
            self.event('ERROR' if error else 'INFO',error or 'Session finished')
            self.db.end_session(self.session_id,self.message.get('stats',{}))
            self.publish(self.snapshot())
