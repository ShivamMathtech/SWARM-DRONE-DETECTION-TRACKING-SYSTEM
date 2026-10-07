"""Deterministic synthetic sensor frames; no model accuracy is implied."""
import math
import cv2
import numpy as np
from app.detection.yolo_detector import Detection

class DemoScene:
    def __init__(self, width=1280, height=720):
        self.width, self.height = width, height
        rng = np.random.default_rng(42)
        sky = np.linspace(88, 124, height)[:, None] + rng.normal(0, 1.8, (height, width))
        self.background = cv2.cvtColor(np.uint8(np.clip(sky, 0, 255)), cv2.COLOR_GRAY2BGR)
        horizon = np.array([[0,height], [0,int(height*.90)]] + [[x, int(height*(.86+rng.random()*.08))] for x in range(0,width+30,30)] + [[width,height]],np.int32)
        cv2.fillPoly(self.background,[horizon],(31,33,32))
        for x in range(40,width,140):
            cv2.rectangle(self.background,(x,int(height*.89)),(x+45,int(height*.96)),(38,40,39),-1)

    def render(self, t):
        frame = self.background.copy()
        w,h = self.width,self.height
        positions = [(w*(.22+.09*math.sin(t*.17)), h*(.30+.045*math.sin(t*.27))),
                     (w*(.69+.08*math.cos(t*.16)), h*(.34+.04*math.sin(t*.21))),
                     (w*(.44+.09*math.sin(t*.13)), h*(.62+.045*math.cos(t*.19)))]
        detections = []
        for i,(x,y) in enumerate(positions):
            # Briefly occlude DR-02 to exercise LOST -> REACQUIRED.
            if i==1 and 8.0 < t%18 < 8.8:
                continue
            x,y=int(x),int(y)
            ink=(13,16,14)
            cv2.line(frame,(x-19,y-5),(x+19,y+5),ink,3)
            cv2.line(frame,(x+19,y-5),(x-19,y+5),ink,3)
            for dx in [-21,21]:
                for dy in [-7,7]:
                    cv2.ellipse(frame,(x+dx,y+dy),(10,2),0,0,360,ink,1)
            cv2.ellipse(frame,(x,y+3),(7,6),0,0,360,ink,-1)
            cv2.line(frame,(x-4,y+7),(x-8,y+12),ink,1)
            cv2.line(frame,(x+4,y+7),(x+8,y+12),ink,1)
            detections.append(Detection((x-33,y-17,x+33,y+20), .94-i*.025, 0, 'drone'))
        return frame, detections
