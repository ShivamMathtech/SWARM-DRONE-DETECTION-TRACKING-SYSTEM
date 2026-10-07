import json
import struct
import time
from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import TrackingMessage
from app.config import Settings
import pytest

def test_configuration_bounds_and_model_path():
    for kwargs in [{'image_size':650},{'confidence_threshold':1.1},{'model_path':'../secret.pt'},{'model_path':'weights/../../secret.pt'},{'track_buffer':0}]:
        with pytest.raises(ValueError):
            Settings(**kwargs)

def test_health_settings_upload_validation_and_origin():
    with TestClient(app) as c:
        assert c.get('/health').json()['status']=='ok'
        assert c.get('/health',headers={'Origin':'https://untrusted.example'}).status_code==403
        config=c.get('/config').json()
        assert c.post('/config',json={**config,'image_size':641}).status_code==422
        assert c.post('/config',json={**config,'image_size':640}).status_code==200
        assert c.post('/stream/start',json={'source':'video','video_id':'../../secret'}).status_code==422
        assert c.post('/stream/start',json={'source':'video'}).status_code==400
        assert c.post('/upload-video',files={'file':('broken.mp4',b'not a video','video/mp4')}).status_code==400
        assert c.post('/upload-video',files={'file':('a.txt',b'hello','text/plain')}).status_code==400

def test_demo_websocket_lifecycle_and_exports():
    with TestClient(app) as c:
        with c.websocket_connect('/ws/frames') as ws:
            initial=ws.receive_json()
            assert initial['schema_version']==1
            assert c.post('/stream/start',json={'source':'demo'}).status_code==200
            deadline=time.monotonic()+45
            while time.monotonic()<deadline:
                packet=ws.receive()
                if packet.get('bytes'):
                    raw=packet['bytes'];n=struct.unpack('!I',raw[:4])[0]
                    msg=TrackingMessage.model_validate_json(raw[4:4+n])
                    assert raw[4+n:4+n+2]==b'\xff\xd8'
                    if msg.targets:
                        break
            else:
                pytest.fail('No demo targets arrived')
            assert msg.demo and msg.source=='demo'
            assert len(msg.targets)==3
            assert msg.stats['precision'] is None
            assert c.post('/config',json=c.get('/config').json()).status_code==409
            assert c.post('/stream/pause').json()['state']=='PAUSED'
            time.sleep(.15)
            paused=c.get('/stats').json()['frame_id']
            time.sleep(.15)
            assert c.get('/stats').json()['frame_id']==paused
            assert c.post('/stream/resume').json()['state']=='RUNNING'
            sid=msg.session_id
            assert c.post('/stream/stop').json()['state']=='STOPPED'
            report=c.get(f'/sessions/{sid}/report').json()
            assert report['source']=='demo' and report['detection_rows']>0
            assert 'frame_id' in c.get(f'/sessions/{sid}/report?format=csv').text
            assert c.get('/sessions').json()
            assert c.get('/sessions/missing/report').status_code==404
        with c.websocket_connect('/ws/tracking') as metadata:
            snapshot=metadata.receive_json()
            assert snapshot['session_id']==sid
            TrackingMessage.model_validate(snapshot)
