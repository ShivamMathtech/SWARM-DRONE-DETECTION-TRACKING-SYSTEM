import numpy as np
import pytest
from app.config import Settings
from app.detection.yolo_detector import Detection
from app.tracking.tracker import MultiObjectTracker

@pytest.mark.parametrize('method',['bytetrack','botsort'])
def test_persistent_ids_lost_reacquired_and_history(method):
    tracker=MultiObjectTracker(Settings(tracker=method,max_trajectory_points=5),{0:'drone'})
    frame=np.zeros((200,400,3),np.uint8)
    for i in range(9):
        targets=tracker.update([Detection((20+i,30,60+i,60),.9,0,'drone'),Detection((200-i,100,240-i,130),.85,0,'drone')],frame,i*.1)
    ids=[t.id for t in targets]
    assert ids==['DR-01','DR-02']
    assert all(len(t.trajectory)==5 for t in targets)
    assert all(t.speed_px_s>0 for t in targets)
    lost=tracker.update([],frame,.9)
    assert all(t.status=='LOST' for t in lost)
    again=tracker.update([Detection((30,30,70,60),.9,0,'drone'),Detection((190,100,230,130),.85,0,'drone')],frame,1.)
    assert [t.id for t in again]==ids
    assert all(t.status=='REACQUIRED' for t in again)
    assert all(t.range_m is None and t.speed_m_s is None for t in again)
    assert tracker.update([],frame,5)==[]

def test_classes_do_not_swap_ids():
    t=MultiObjectTracker(Settings(),{0:'drone',1:'bird'})
    frame=np.zeros((200,400,3),np.uint8)
    for i in range(5):
        result=t.update([Detection((20+i,20,60+i,60),.9,0,'drone'),Detection((20+i,20,60+i,60),.9,1,'bird')],frame,i*.1)
    assert len(result)==2
    assert len({r.id for r in result})==2
    assert {r.class_name for r in result}=={'drone','bird'}

def test_low_confidence_rescues_existing_track_but_cannot_start():
    t=MultiObjectTracker(Settings(),{0:'drone'})
    f=np.zeros((200,400,3),np.uint8)
    assert not t.update([Detection((20,20,60,60),.2,0,'drone')],f,0)
    for i in range(1,4):
        result=t.update([Detection((20+i,20,60+i,60),.9,0,'drone')],f,i*.1)
    tid=result[0].id
    result=t.update([Detection((24,20,64,60),.25,0,'drone')],f,.4)
    assert result[0].id==tid and result[0].status=='ACTIVE'

def test_return_after_timeout_gets_new_public_identity():
    t=MultiObjectTracker(Settings(lost_timeout_s=.2),{0:'drone'})
    f=np.zeros((200,400,3),np.uint8)
    ds=[Detection((20,20,60,60),.9,0,'drone')]
    first=t.update(ds,f,0)[0].id
    returned=t.update(ds,f,1)[0]
    assert returned.id!=first
    assert t.associations[id(ds[0])]==returned.track_id
