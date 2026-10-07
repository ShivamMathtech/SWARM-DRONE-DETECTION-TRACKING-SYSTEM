"""Auditable framewise identity diagnostics against CSV ground truth (not HOTA/IDF1)."""
import argparse
import csv
from collections import defaultdict
import numpy as np
from scipy.optimize import linear_sum_assignment
from common import write_reports,utc_now

def read_rows(path,id_field):
    grouped=defaultdict(list)
    seen=set()
    with open(path,newline='') as f:
        for row in csv.DictReader(f):
            if not row.get(id_field):
                # Unconfirmed detections have no persistent identity.
                continue
            frame=int(row['frame_id']);ident=row[id_field]
            if (frame,ident) in seen:
                raise ValueError(f'Duplicate identity {ident} on frame {frame}')
            seen.add((frame,ident))
            box=[float(row[k]) for k in ['x1','y1','x2','y2']]
            if not np.isfinite(box).all() or box[2]<=box[0] or box[3]<=box[1]:
                raise ValueError(f'Invalid box on frame {frame}')
            grouped[frame].append((ident,row.get('class_name','drone'),box))
    return grouped

def iou(a,b):
    intersection=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-intersection
    return intersection/union if union else 0.

def evaluate(gt,pred,threshold=.5,max_gap=30):
    if not gt:
        raise ValueError('Ground truth contains no identities.')
    tp=fp=fn=switches=0
    last={};totals=defaultdict(int);matched_counts=defaultdict(int)
    for frame in sorted(set(gt)|set(pred)):
        ground,observed=gt.get(frame,[]),pred.get(frame,[])
        for gid,cls,_ in ground:
            totals[(cls,gid)]+=1
        pairs=[]
        if ground and observed:
            cost=np.ones((len(ground),len(observed)))*1e6
            for i,(_,gc,gb) in enumerate(ground):
                for j,(_,pc,pb) in enumerate(observed):
                    overlap=iou(gb,pb)
                    if gc==pc and overlap>=threshold:
                        cost[i,j]=1-overlap
            ii,jj=linear_sum_assignment(cost)
            pairs=[(i,j) for i,j in zip(ii,jj) if cost[i,j]<1e6]
        tp+=len(pairs);fn+=len(ground)-len(pairs);fp+=len(observed)-len(pairs)
        for i,j in pairs:
            gid,cls,_=ground[i];pid=observed[j][0];key=(cls,gid)
            if key in last and frame-last[key][1]<=max_gap and pid!=last[key][0]:
                switches+=1
            last[key]=(pid,frame);matched_counts[key]+=1
    gt_count=tp+fn
    return dict(precision=tp/(tp+fp) if tp+fp else 0.,recall=tp/gt_count,
        id_switches=switches,matched_observations=tp,false_positives=fp,misses=fn,
        mean_track_coverage=float(np.mean([matched_counts[k]/v for k,v in totals.items()])),
        iou_threshold=threshold,id_switch_max_gap_frames=max_gap,
        definition='Class-aware Hungarian IoU matching. An ID switch occurs when a matched ground-truth identity changes predicted ID within max_gap frames. Coverage is the fraction of annotated appearances matched, averaged over ground-truth IDs. Not a standardized HOTA/IDF1 benchmark.')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ground-truth',required=True)
    p.add_argument('--predictions',required=True)
    p.add_argument('--iou',type=float,default=.5)
    p.add_argument('--max-gap',type=int,default=30)
    p.add_argument('--output',default='data/reports')
    args=p.parse_args()
    if not 0<args.iou<=1 or args.max_gap<1:
        p.error('IoU must be in (0,1]; max-gap must be positive.')
    result=evaluate(read_rows(args.ground_truth,'gt_id'),read_rows(args.predictions,'track_id'),args.iou,args.max_gap)
    result.update(created_at=utc_now(),ground_truth=args.ground_truth,predictions=args.predictions)
    print(write_reports(result,args.output,'tracking'))

if __name__=='__main__':
    main()
