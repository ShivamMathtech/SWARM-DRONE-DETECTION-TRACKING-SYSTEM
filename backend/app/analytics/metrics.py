from collections import deque
from statistics import mean

class Metrics:
    def __init__(self):
        self.times=deque(maxlen=90)
        self.latencies=deque(maxlen=90)
        self.frames=0
        self.detections=0
        self.sum_latency=0.
        self.sum_conf=0.
        self.max_tracks=0

    def update(self, now, latency, detections, targets):
        self.times.append(now)
        self.latencies.append(latency)
        self.frames+=1
        self.detections+=len(detections)
        self.sum_conf+=sum(d.confidence for d in detections)
        self.sum_latency+=latency
        visible=[t for t in targets if t.status!='LOST']
        self.max_tracks=max(self.max_tracks,len(visible))
        fps=(len(self.times)-1)/(self.times[-1]-self.times[0]) if len(self.times)>1 and self.times[-1]>self.times[0] else 0.
        return dict(processed_frames=self.frames, detection_count=self.detections,
            visible=len(visible), lost=len(targets)-len(visible), retained_tracks=len(targets),
            tracked_drones=sum(t.class_name.lower()=='drone' for t in targets),
            average_confidence=round(mean(t.confidence for t in visible),4) if visible else None,
            mean_persistence=round(mean(t.persistence for t in targets),4) if targets else None,
            peak_visible=self.max_tracks, fps=round(fps,2),
            mean_latency_ms=round(self.sum_latency/self.frames,2),
            precision=None, recall=None, map50=None, map50_95=None, id_switches=None)
