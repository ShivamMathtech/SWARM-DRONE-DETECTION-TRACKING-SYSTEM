"""Create a clearly synthetic, portable AVI for upload/codec checks (not model validation)."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.video.demo import DemoScene
import cv2

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',default='data/synthetic-drone-demo.avi')
    p.add_argument('--seconds',type=int,default=15)
    args=p.parse_args()
    if not 1<=args.seconds<=600:
        p.error('seconds must be between 1 and 600')
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
    writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*'MJPG'),30,(960,540))
    if not writer.isOpened():
        raise RuntimeError('MJPEG encoder unavailable in this OpenCV build.')
    scene=DemoScene(960,540)
    try:
        for n in range(args.seconds*30):
            frame,_=scene.render(n/30)
            cv2.putText(frame,'SYNTHETIC TEST VIDEO',(20,30),cv2.FONT_HERSHEY_SIMPLEX,.55,(210,210,210),1)
            writer.write(frame)
    finally:
        writer.release()
    print(path.resolve())

if __name__=='__main__':
    main()
