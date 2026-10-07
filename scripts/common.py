import json
import csv
from pathlib import Path
from datetime import datetime, timezone
import yaml
ROOT=Path(__file__).resolve().parents[1]
from dotenv import load_dotenv
load_dotenv(ROOT/'.env')

def dataset_path(filename):
    """Resolve relative dataset roots against the YAML file, not Ultralytics' global datasets directory."""
    path=Path(filename).resolve()
    if not path.is_file():
        raise ValueError(f'Dataset YAML not found: {path}')
    payload=yaml.safe_load(path.read_text())
    if not isinstance(payload,dict) or not all(k in payload for k in ['train','val','names']):
        raise ValueError('data.yaml must contain train, val and names.')
    root=(path.parent/str(payload.get('path','.'))).resolve()
    payload['path']=str(root)
    for key in ['train','val','test']:
        if key in payload:
            values=payload[key] if isinstance(payload[key],list) else [payload[key]]
            if any(not (root/str(v)).exists() for v in values):
                raise ValueError(f'Missing dataset {key} path relative to {root}.')
    output=ROOT/'data'/'resolved_datasets'
    output.mkdir(parents=True,exist_ok=True)
    # A hash avoids collisions between different datasets with the same filename.
    import hashlib
    resolved=output/(hashlib.sha256(str(path).encode()).hexdigest()[:12]+'.yaml')
    resolved.write_text(yaml.safe_dump(payload,sort_keys=False))
    return resolved

def write_reports(result,directory,name):
    directory=Path(directory)
    directory.mkdir(parents=True,exist_ok=True)
    path=directory/f'{name}.json'
    path.write_text(json.dumps(result,indent=2,allow_nan=False))
    flat={k:v for k,v in result.items() if not isinstance(v,(dict,list))}
    with (directory/f'{name}.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(flat));writer.writeheader();writer.writerow(flat)
    return path

def utc_now():
    return datetime.now(timezone.utc).isoformat()
