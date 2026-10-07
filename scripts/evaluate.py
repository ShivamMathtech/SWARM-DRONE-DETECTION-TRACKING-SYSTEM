"""Real annotated detection evaluation; never evaluates demo trajectories as YOLO accuracy."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from common import ROOT,dataset_path,utc_now,write_reports

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data',default='dataset/data.yaml')
    p.add_argument('--model',default='weights/drone_detector.pt')
    p.add_argument('--split',choices=['val','test'],default='test')
    p.add_argument('--imgsz',type=int,default=1280)
    p.add_argument('--batch',type=int,default=1)
    p.add_argument('--device',default='cpu')
    p.add_argument('--output',default=str(Path(os.getenv('SWARM_DATA_DIR',str(ROOT/'data')))/'reports'))
    args=p.parse_args()
    path=Path(args.model)
    if not path.is_file():
        p.error('Supply a trained local model with --model.')
    from ultralytics import YOLO,__version__
    model=YOLO(str(path))
    metrics=model.val(data=str(dataset_path(args.data)),split=args.split,imgsz=args.imgsz,
        batch=args.batch,device=args.device,workers=0,plots=True,project=str(Path(args.output)/'validation'),name=args.split)
    result=dict(created_at=utc_now(),model=str(path.resolve()),model_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        dataset=str(Path(args.data).resolve()),split=args.split,imgsz=args.imgsz,device=args.device,
        precision=float(metrics.box.mp),recall=float(metrics.box.mr),map50=float(metrics.box.map50),map50_95=float(metrics.box.map),
        latency_ms=metrics.speed,inference_fps=1000/metrics.speed['inference'] if metrics.speed.get('inference',0)>0 else None,
        ultralytics_version=__version__,classes=model.names,
        note='Dataset validation results. Inference FPS excludes camera, tracking, encoding, network and browser. Precision/recall are Ultralytics validation operating-point aggregates.')
    saved=write_reports(result,args.output,'latest')
    print(json.dumps(result,indent=2))
    print(f'Report saved: {saved}')

if __name__=='__main__':
    main()
