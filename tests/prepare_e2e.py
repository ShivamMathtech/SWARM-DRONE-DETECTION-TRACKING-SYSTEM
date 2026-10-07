"""Create local, UNTRAINED YOLO + synthetic video fixtures for browser transport tests."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
import cv2
import torch
from ultralytics import YOLO
from app.video.demo import DemoScene

def main():
    torch.set_num_threads(2)
    weights=ROOT/'weights'/'smoke-test.pt'
    if weights.exists():
        raise FileExistsError('Refusing to overwrite existing smoke-test.pt')
    YOLO('yolov8n.yaml').save(str(weights))
    output=ROOT/'data'/'smoke.avi'
    output.parent.mkdir(exist_ok=True)
    scene=DemoScene(320,180)
    writer=cv2.VideoWriter(str(output),cv2.VideoWriter_fourcc(*'MJPG'),15,(320,180))
    if not writer.isOpened():
        raise RuntimeError('AVI writer unavailable')
    for n in range(150):
        writer.write(scene.render(n/15)[0])
    writer.release()
    print('Created untrained inference fixture weights/smoke-test.pt and data/smoke.avi. These do not detect drones.')

if __name__=='__main__':
    main()
