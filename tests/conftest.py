import os
import sys
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
sys.path.insert(0,str(ROOT/'scripts'))
os.environ['SWARM_DATA_DIR']=tempfile.mkdtemp(prefix='swarm-tests-')
os.environ['YOLO_AUTOINSTALL']='false'
os.environ['YOLO_CONFIG_DIR']=tempfile.mkdtemp(prefix='swarm-yolo-')
