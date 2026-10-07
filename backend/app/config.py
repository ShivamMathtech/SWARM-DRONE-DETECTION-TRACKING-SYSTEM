"""Validated local-console configuration. Camera credentials never enter this model."""
import os
from pathlib import Path
from typing import Literal
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, field_validator

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / '.env')
DATA_DIR = Path(os.getenv('SWARM_DATA_DIR', str(ROOT / 'data'))).resolve()
os.environ.setdefault('YOLO_AUTOINSTALL', 'false')
YOLO_CONFIG = DATA_DIR / 'ultralytics'
YOLO_CONFIG.mkdir(parents=True, exist_ok=True)
os.environ.setdefault('YOLO_CONFIG_DIR', str(YOLO_CONFIG))
ORIGINS = [s.strip() for s in os.getenv('ALLOWED_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080,http://127.0.0.1:8080').split(',') if s.strip()]
MAX_UPLOAD_BYTES = int(os.getenv('MAX_UPLOAD_MB', '250')) * 1024 * 1024

class Settings(BaseModel):
    model_config = ConfigDict(extra='forbid', validate_assignment=True)
    model_path: str = 'weights/drone_detector.pt'
    confidence_threshold: float = Field(0.40, ge=0.10, le=0.95)
    iou_threshold: float = Field(0.50, ge=0.1, le=0.95)
    image_size: int = Field(1280, ge=320, le=1920)
    device: Literal['auto', 'cpu', 'cuda:0'] = 'auto'
    classes: list[str] = Field(default_factory=list, max_length=32)
    tracker: Literal['bytetrack', 'botsort'] = 'bytetrack'
    track_buffer: int = Field(60, ge=5, le=300)
    lost_timeout_s: float = Field(3.0, ge=0.2, le=30)
    match_threshold: float = Field(0.80, ge=0.1, le=0.99)
    max_trajectory_points: int = Field(50, ge=5, le=200)
    target_fps: int = Field(30, ge=1, le=60)
    frame_skip: int = Field(0, ge=0, le=10)
    stream_width: int = Field(1280, ge=320, le=1920)
    jpeg_quality: int = Field(80, ge=40, le=95)
    max_detections: int = Field(100, ge=1, le=300)
    debug: bool = False

    @field_validator('image_size')
    @classmethod
    def stride(cls, value):
        if value % 32:
            raise ValueError('Image size must be a multiple of 32.')
        return value

    @field_validator('model_path')
    @classmethod
    def safe_model(cls, value):
        path = (ROOT / value).resolve()
        if not path.is_relative_to((ROOT / 'weights').resolve()) or path.suffix.lower() not in {'.pt', '.onnx'}:
            raise ValueError('Use a trusted .pt or .onnx model inside weights/.')
        return str(path.relative_to(ROOT))

    @field_validator('classes')
    @classmethod
    def normalize_classes(cls, values):
        return list(dict.fromkeys(v.strip().lower() for v in values if v.strip()))

    @classmethod
    def from_environment(cls):
        values = {}
        for key in cls.model_fields:
            if key.upper() in os.environ:
                values[key] = os.environ[key.upper()]
        if 'classes' in values:
            values['classes'] = values['classes'].split(',')
        return cls(**values)
