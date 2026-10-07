from types import SimpleNamespace
import numpy as np
from app.detection.yolo_detector import parse_yolo_boxes,xyxy_to_xywh

def test_parse_clip_filter_empty_and_invalid():
    boxes=SimpleNamespace(data=np.array([[-5,20,50,70,.94,0],[60,30,70,50,.1,1],[2,2,1,4,.9,0],[0,0,4,4,float('nan'),0]]))
    ds=parse_yolo_boxes(boxes,{0:'drone',1:'bird'},(100,100),minimum=.4)
    assert len(ds)==1
    assert ds[0].bbox==(0.,20.,50.,70.)
    assert ds[0].class_name=='drone'
    assert parse_yolo_boxes(None,{0:'drone'},(100,100))==[]
    assert parse_yolo_boxes(boxes,{0:'drone',1:'bird'},(100,100),allowed=['aircraft'])==[]

def test_bbox_conversion():
    assert xyxy_to_xywh([400,220,470,280])==(435,250,70,60)
