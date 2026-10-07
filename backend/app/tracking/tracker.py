"""Real ByteTrack/BoT-SORT association + application track lifecycle and history."""
from collections import deque
from types import SimpleNamespace
import math
import numpy as np
from app.models.schemas import Target

class MultiObjectTracker:
    def __init__(self, config, names):
        from ultralytics.engine.results import Boxes
        from ultralytics.trackers.byte_tracker import BYTETracker
        from ultralytics.trackers.bot_sort import BOTSORT
        self.Boxes = Boxes
        self.config = config
        self.names = names
        args = SimpleNamespace(track_high_thresh=config.confidence_threshold,
            track_low_thresh=0.1, new_track_thresh=config.confidence_threshold,
            track_buffer=config.track_buffer, match_thresh=config.match_threshold,
            fuse_score=True, gmc_method='sparseOptFlow', proximity_thresh=0.5,
            appearance_thresh=0.25, with_reid=False, model='auto')
        tracker_cls = BOTSORT if config.tracker == 'botsort' else BYTETracker
        # All instances are initialized before the first update. Each class has its
        # own association pool, so a bird cannot take a drone's ID.
        self.engines = {cid: tracker_cls(args, frame_rate=30) for cid in names}
        self.records = {}
        self.serial = 0
        self.tick = 0
        self.new_events = []
        self.total_reacquisitions = 0

    def update(self, detections, frame, source_time):
        self.tick += 1
        self.new_events = []
        self.associations = {}
        # Expire before association: a return after the wall/media timeout gets
        # a new public ID even if the underlying tracker still remembers it.
        for key in list(self.records):
            r = self.records[key]
            if source_time-r['last'] > self.config.lost_timeout_s or self.tick-r['last_tick'] > self.config.track_buffer:
                self.new_events.append(('INFO', f'DR-{r["number"]:02d} expired'))
                del self.records[key]
        seen = set()
        for cid, engine in self.engines.items():
            class_detections = [d for d in detections if d.class_id == cid]
            rows = [(*d.bbox, d.confidence, d.class_id) for d in class_detections]
            boxes = self.Boxes(np.array(rows, dtype=np.float32).reshape(-1, 6), frame.shape[:2])
            outputs = engine.update(boxes, frame)
            for row in outputs:
                # x1, y1, x2, y2, tracker ID, score, class, detection index
                key = (cid, int(row[4]))
                h, w = frame.shape[:2]
                b = [float(np.clip(row[i], 0, w if i % 2 == 0 else h)) for i in range(4)]
                if b[2] <= b[0] or b[3] <= b[1]:
                    continue
                center = [(b[0]+b[2])/2, (b[1]+b[3])/2]
                seen.add(key)
                if key not in self.records:
                    self.serial += 1
                    self.records[key] = dict(number=self.serial, first=source_time, last=source_time,
                        first_tick=self.tick, last_tick=self.tick, observations=0, confidence=float(row[5]),
                        center=center, velocity=[0., 0.], history=deque(maxlen=self.config.max_trajectory_points), status='ACTIVE')
                    self.new_events.append(('INFO', f'Detected DR-{self.serial:02d} · {self.names[cid]}'))
                r = self.records[key]
                status = 'REACQUIRED' if r['status'] == 'LOST' else 'ACTIVE'
                if status == 'REACQUIRED':
                    self.total_reacquisitions += 1
                    self.new_events.append(('INFO', f'DR-{r["number"]:02d} reacquired'))
                dt = source_time - r['last']
                velocity = r['velocity']
                if dt > 1e-6:
                    measured = [(center[i]-r['center'][i])/dt for i in range(2)]
                    velocity = [0.35*measured[i]+0.65*velocity[i] for i in range(2)]
                if abs(float(row[5])-r['confidence']) > 0.15:
                    self.new_events.append(('INFO', f'DR-{r["number"]:02d} detection confidence changed'))
                r.update(bbox=b, confidence=float(row[5]), center=center, last=source_time,
                    last_tick=self.tick, velocity=velocity, status=status, observations=r['observations']+1)
                r['history'].append([round(v, 2) for v in center])
                detection_index = int(row[7])
                if 0 <= detection_index < len(class_detections):
                    self.associations[id(class_detections[detection_index])] = r['number']
        for key in list(self.records):
            r = self.records[key]
            if key not in seen:
                if r['status'] != 'LOST':
                    r['status'] = 'LOST'
                    self.new_events.append(('WARN', f'DR-{r["number"]:02d} temporarily lost'))
                if source_time-r['last'] > self.config.lost_timeout_s or self.tick-r['last_tick'] > self.config.track_buffer:
                    self.new_events.append(('INFO', f'DR-{r["number"]:02d} expired'))
                    del self.records[key]
        # Bound retained application history under very noisy detections. Visible
        # tracks take priority; oldest lost histories are retired first.
        limit = max(64, 2*self.config.max_detections)
        if len(self.records) > limit:
            lost = sorted((k for k in self.records if self.records[k]['status']=='LOST'), key=lambda k:self.records[k]['last'])
            for key in lost[:max(0,len(self.records)-limit)]:
                del self.records[key]
        targets = []
        for (cid, _), r in self.records.items():
            targets.append(Target(id=f'DR-{r["number"]:02d}', track_id=r['number'],
                class_name=self.names[cid], confidence=round(r['confidence'], 4), bbox=r['bbox'],
                center=r['center'], status=r['status'], trajectory=list(r['history']),
                age_s=round(source_time-r['first'], 3), last_seen=round(r['last'], 3),
                missed_s=round(source_time-r['last'], 3), velocity_px_s=[round(v,2) for v in r['velocity']],
                speed_px_s=round(math.hypot(*r['velocity']),2),
                persistence=round(r['observations']/(self.tick-r['first_tick']+1),4)))
        return sorted(targets, key=lambda t: t.track_id)
