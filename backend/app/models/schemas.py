from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class StartRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    source: Literal['demo', 'webcam', 'video', 'rtsp'] = 'demo'
    camera_index: int = Field(0, ge=0, le=10)
    video_id: str | None = Field(None, pattern=r'^[a-f0-9]{32}\.(mp4|avi|mov|mkv|webm)$')

class Target(BaseModel):
    id: str
    track_id: int
    class_name: str
    confidence: float
    bbox: list[float]
    center: list[float]
    status: Literal['ACTIVE', 'LOST', 'REACQUIRED']
    trajectory: list[list[float]]
    age_s: float
    last_seen: float
    missed_s: float
    velocity_px_s: list[float]
    speed_px_s: float
    persistence: float
    range_m: None = None
    altitude_m: None = None
    speed_m_s: None = None

class TrackingMessage(BaseModel):
    schema_version: int = 1
    timestamp: float
    source_time_s: float
    frame_id: int
    session_id: str | None
    state: str
    source: str
    demo: bool
    width: int
    height: int
    fps: float
    inference_ms: float
    tracker_ms: float
    pipeline_ms: float
    dropped_frames: int
    targets: list[Target]
    stats: dict
    events: list[dict]
    error: str | None = None
    device: str = 'N/A'
    model: str = 'N/A'
    raw_detections: list[dict] = Field(default_factory=list)
