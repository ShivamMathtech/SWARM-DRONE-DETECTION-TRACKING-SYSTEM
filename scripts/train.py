"""Train a configurable Ultralytics detection model on a local YOLO dataset."""
import argparse
import json
import shutil
from pathlib import Path
from common import ROOT,dataset_path,utc_now

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data',default='dataset/data.yaml')
    p.add_argument('--model',default='yolov8n.pt')
    p.add_argument('--epochs',type=int,default=100)
    p.add_argument('--imgsz',type=int,default=640)
    p.add_argument('--batch',type=int,default=8)
    p.add_argument('--device',default='cpu')
    p.add_argument('--workers',type=int,default=0,help='0 is robust on Windows; increase for Linux training')
    p.add_argument('--seed',type=int,default=42)
    p.add_argument('--project',default=str(ROOT/'runs'/'train'))
    p.add_argument('--name',default='drone')
    p.add_argument('--install',action='store_true',help='Copy best.pt to weights/drone_detector.pt after training')
    args=p.parse_args()
    if args.epochs<1 or args.imgsz<32 or args.imgsz%32:
        p.error('epochs must be positive; imgsz must be a positive multiple of 32')
    data=dataset_path(args.data)
    from ultralytics import YOLO
    model=YOLO(args.model)
    model.train(data=str(data),epochs=args.epochs,imgsz=args.imgsz,batch=args.batch,
        device=args.device,workers=args.workers,seed=args.seed,deterministic=True,
        project=args.project,name=args.name,exist_ok=False)
    save_dir=Path(model.trainer.save_dir)
    (save_dir/'research_run.json').write_text(json.dumps({'created_at':utc_now(),'arguments':vars(args),'resolved_data':str(data)},indent=2))
    best=Path(model.trainer.best)
    print(f'Best checkpoint: {best}')
    if args.install:
        destination=ROOT/'weights'/'drone_detector.pt'
        if destination.exists():
            raise FileExistsError('Existing weights preserved. Copy the new checkpoint under a different name or back up the old weights first.')
        destination.parent.mkdir(exist_ok=True)
        shutil.copy2(best,destination)
        print(f'Installed: {destination}')

if __name__=='__main__':
    main()
