"""YOLO adapter; imports the ML stack only when a real source starts."""
from dataclasses import dataclass
import numpy as np
from app.config import ROOT, Settings

@dataclass(frozen=True)
class Detection:
    bbox: tuple[float, float, float, float]
    confidence: float
    class_id: int
    class_name: str


def xyxy_to_xywh(box):
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2, (y1 + y2) / 2, x2 - x1, y2 - y1)


def parse_yolo_boxes(boxes, names, shape, minimum=0.1, allowed=None):
    """Parse real Ultralytics Boxes or an equivalent test object, rejecting NaN/degenerate rows."""
    if boxes is None:
        return []
    rows = boxes.data
    if hasattr(rows, 'detach'):
        rows = rows.detach().cpu().numpy()
    h, w = shape[:2]
    detections = []
    for row in np.asarray(rows).reshape(-1, 6):
        if not np.isfinite(row).all() or not minimum <= row[4] <= 1 or row[5] < 0:
            continue
        cid = int(row[5])
        name = str(names.get(cid, str(cid)))
        if allowed and name.lower() not in allowed:
            continue
        x1, y1, x2, y2 = row[:4]
        box = (float(np.clip(x1, 0, w)), float(np.clip(y1, 0, h)), float(np.clip(x2, 0, w)), float(np.clip(y2, 0, h)))
        if box[2] <= box[0] or box[3] <= box[1]:
            continue
        detections.append(Detection(box, float(row[4]), cid, name))
    return detections

class YoloDetector:
    def __init__(self, config: Settings):
        self.config = config
        path = ROOT / config.model_path
        if not path.is_file():
            raise FileNotFoundError('MODEL UNAVAILABLE: place trained weights at ' + config.model_path + ' or select Demo.')
        import torch
        from ultralytics import YOLO
        torch.set_num_threads(max(1, min(4, torch.get_num_threads())))
        self.warning = None
        self.device = '0' if config.device != 'cpu' and torch.cuda.is_available() else 'cpu'
        if config.device == 'cuda:0' and self.device == 'cpu':
            self.warning = 'CUDA unavailable; running inference on CPU.'
        self.model = YOLO(str(path), task='detect')
        self.names = {int(k): str(v) for k, v in self.model.names.items()}
        if config.classes and not any(n.lower() in config.classes for n in self.names.values()):
            raise ValueError('The selected class filter does not match any class in this model.')

    def detect(self, frame):
        # ByteTrack needs low-score candidates for its second association pass.
        # Only scores >= confidence_threshold may initialize a new visible track.
        result = self.model.predict(frame, conf=min(0.1, self.config.confidence_threshold),
            iou=self.config.iou_threshold, imgsz=self.config.image_size,
            device=self.device, max_det=self.config.max_detections, verbose=False)[0]
        return parse_yolo_boxes(result.boxes, self.names, frame.shape, 0.1, self.config.classes)
