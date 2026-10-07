"""Thread-local SQLite transactions; all observations use source media time."""
import json
import sqlite3
import time
from contextlib import contextmanager

class Database:
    def __init__(self, path):
        self.path=path
        path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as c:
            c.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS configuration(id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, started_at REAL, ended_at REAL, source TEXT, config TEXT, stats TEXT);
            CREATE TABLE IF NOT EXISTS tracks(session_id TEXT, track_id INTEGER, class_name TEXT, first_seen REAL, last_seen REAL, status TEXT, PRIMARY KEY(session_id, track_id));
            CREATE TABLE IF NOT EXISTS detections(id INTEGER PRIMARY KEY, session_id TEXT, frame_id INTEGER, source_time REAL, track_id INTEGER, class_name TEXT, x1 REAL,y1 REAL,x2 REAL,y2 REAL,confidence REAL);
            CREATE INDEX IF NOT EXISTS detection_session ON detections(session_id, frame_id);
            CREATE TABLE IF NOT EXISTS track_observations(session_id TEXT,frame_id INTEGER,source_time REAL,track_id INTEGER,class_name TEXT,x1 REAL,y1 REAL,x2 REAL,y2 REAL,confidence REAL,PRIMARY KEY(session_id,frame_id,track_id));
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,session_id TEXT,timestamp REAL,level TEXT,message TEXT);
            ''')
            # Recover metadata after an unclean process shutdown.
            c.execute('UPDATE sessions SET ended_at=? WHERE ended_at IS NULL',(time.time(),))

    @contextmanager
    def connect(self):
        c=sqlite3.connect(self.path,timeout=10)
        c.row_factory=sqlite3.Row
        try:
            yield c
            c.commit()
        except Exception:
            c.rollback()
            raise
        finally:
            c.close()

    def load_config(self):
        with self.connect() as c:
            row=c.execute('SELECT payload FROM configuration WHERE id=1').fetchone()
        return json.loads(row[0]) if row else None

    def save_config(self,config):
        with self.connect() as c:
            c.execute('INSERT OR REPLACE INTO configuration VALUES(1,?)',(config.model_dump_json(),))

    def start_session(self,sid,source,config):
        with self.connect() as c:
            c.execute('INSERT INTO sessions VALUES(?,?,NULL,?,?,?)',(sid,time.time(),source,config.model_dump_json(),'{}'))

    def record(self,msg,detections,associations):
        sid=msg['session_id']
        if not sid:
            return
        # Record raw detections above the requested threshold; tracker association
        # is NULL when ByteTrack has not yet confirmed a new detection.
        visible=[t for t in msg['targets'] if t['status']!='LOST']
        with self.connect() as c:
            for t in msg['targets']:
                c.execute('''INSERT INTO tracks VALUES(?,?,?,?,?,?) ON CONFLICT(session_id,track_id)
                    DO UPDATE SET last_seen=excluded.last_seen,status=excluded.status''',
                    (sid,t['track_id'],t['class_name'],max(0,msg['source_time_s']-t['age_s']),t['last_seen'],t['status']))
            for t in visible:
                c.execute('INSERT INTO track_observations VALUES(?,?,?,?,?,?,?,?,?,?)',
                    (sid,msg['frame_id'],msg['source_time_s'],t['track_id'],t['class_name'],*t['bbox'],t['confidence']))
            for d in detections:
                tid=associations.get(id(d))
                c.execute('INSERT INTO detections(session_id,frame_id,source_time,track_id,class_name,x1,y1,x2,y2,confidence) VALUES(?,?,?,?,?,?,?,?,?,?)',
                    (sid,msg['frame_id'],msg['source_time_s'],tid,d.class_name,*d.bbox,d.confidence))
            c.execute('UPDATE sessions SET stats=? WHERE id=?',(json.dumps(msg['stats']),sid))

    def event(self,sid,event):
        with self.connect() as c:
            c.execute('INSERT INTO events(session_id,timestamp,level,message) VALUES(?,?,?,?)',(sid,event['timestamp'],event['level'],event['message']))

    def end_session(self,sid,stats):
        if sid:
            with self.connect() as c:
                c.execute('UPDATE sessions SET ended_at=?,stats=? WHERE id=?',(time.time(),json.dumps(stats),sid))
                c.execute("UPDATE tracks SET status='ENDED' WHERE session_id=?",(sid,))

    def sessions(self):
        with self.connect() as c:
            return [dict(r) for r in c.execute('SELECT id,started_at,ended_at,source,stats FROM sessions ORDER BY started_at DESC LIMIT 100')]

    def report(self,sid):
        with self.connect() as c:
            s=c.execute('SELECT * FROM sessions WHERE id=?',(sid,)).fetchone()
            if not s:
                return None
            data=dict(s)
            data['config']=json.loads(data['config'])
            data['stats']=json.loads(data['stats'])
            data['tracks']=[dict(r) for r in c.execute('SELECT * FROM tracks WHERE session_id=?',(sid,))]
            data['events']=[dict(r) for r in c.execute('SELECT * FROM events WHERE session_id=?',(sid,))]
            data['detection_rows']=c.execute('SELECT COUNT(*) FROM detections WHERE session_id=?',(sid,)).fetchone()[0]
        data['metric_note']='Live precision/recall/mAP/ID-switches are unavailable without annotations. Use scripts/evaluate.py and scripts/evaluate_tracking.py.'
        return data

    def detection_rows(self,sid):
        with self.connect() as c:
            for row in c.execute('SELECT frame_id,source_time,track_id,class_name,x1,y1,x2,y2,confidence FROM detections WHERE session_id=? ORDER BY frame_id,id',(sid,)):
                yield dict(row)

    def observation_rows(self,sid):
        with self.connect() as c:
            for row in c.execute('SELECT frame_id,source_time,track_id,class_name,x1,y1,x2,y2,confidence FROM track_observations WHERE session_id=? ORDER BY frame_id,track_id',(sid,)):
                yield dict(row)
