"""Actual video -> actual YOLO -> tracker -> WebSocket. Random weights test plumbing only."""
import time
import uuid
import cv2
import numpy as np
from fastapi.testclient import TestClient
from app.config import ROOT
from app.main import app
from app.models.schemas import TrackingMessage

def test_real_yolo_video_pipeline(tmp_path):
    from ultralytics import YOLO
    import torch
    torch.set_num_threads(2)
    # No network/download. Bundled architecture + untrained weights means zero
    # meaningful accuracy claims; real drone accuracy needs a labeled dataset.
    model_path=ROOT/'weights'/f'test-{uuid.uuid4().hex}.pt'
    YOLO('yolov8n.yaml').save(str(model_path))
    video=tmp_path/'synthetic.avi'
    writer=cv2.VideoWriter(str(video),cv2.VideoWriter_fourcc(*'MJPG'),10,(320,192))
    assert writer.isOpened()
    for i in range(50):
        f=np.full((192,320,3),100,np.uint8)
        cv2.rectangle(f,(20+i,40),(40+i,60),(20,20,20),-1)
        writer.write(f)
    writer.release()
    try:
        with TestClient(app) as c:
            config=c.get('/config').json()
            config.update(model_path=str(model_path.relative_to(ROOT)),image_size=320,device='cpu',target_fps=10)
            assert c.post('/config',json=config).status_code==200
            with video.open('rb') as f:
                response=c.post('/upload-video',files={'file':('synthetic.avi',f,'video/x-msvideo')})
            assert response.status_code==200
            with c.websocket_connect('/ws/tracking') as ws:
                ws.receive_json()
                assert c.post('/stream/start',json={'source':'video','video_id':response.json()['video_id']}).status_code==200
                seen=False
                deadline=time.monotonic()+60
                while time.monotonic()<deadline:
                    msg=ws.receive_json()
                    TrackingMessage.model_validate(msg)
                    assert msg['state']!='ERROR',msg['error']
                    if msg['frame_id']>0:
                        assert not msg['demo'] and msg['source']=='video'
                        assert msg['inference_ms']>0
                        seen=True
                        break
                assert seen
                assert c.post('/stream/stop').status_code==200
    finally:
        model_path.unlink(missing_ok=True)
