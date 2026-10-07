import asyncio
import csv
import io
import json
import uuid
from pathlib import Path
import cv2
from fastapi import APIRouter, HTTPException, Request, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from app.config import DATA_DIR, MAX_UPLOAD_BYTES, ORIGINS, ROOT, Settings
from app.models.schemas import StartRequest

router=APIRouter()

def engine(request):
    return request.app.state.engine

@router.get('/health')
def health(request: Request):
    e=engine(request)
    return dict(status='ok',stream_state=e.state,model_available=(ROOT/e.settings.model_path).is_file(),version='1.0.0')

@router.get('/config')
def get_config(request: Request):
    return engine(request).settings

@router.post('/config')
def update_config(settings: Settings, request: Request):
    e=engine(request)
    with e.lock:
        if e.thread and e.thread.is_alive():
            raise HTTPException(409,'Stop the stream before saving pipeline settings.')
        e.db.save_config(settings)
        e.settings=settings
    return settings

@router.post('/stream/start')
def start(body: StartRequest, request: Request):
    if body.source=='video' and (not body.video_id or not (DATA_DIR/'uploads'/body.video_id).is_file()):
        raise HTTPException(400,'Upload and select a video first.')
    try:
        return engine(request).start(body)
    except RuntimeError as e:
        raise HTTPException(409,str(e)) from None

@router.post('/stream/stop')
def stop(request: Request):
    return engine(request).stop()

@router.post('/stream/pause')
def pause(request: Request):
    try:
        engine(request).pause()
        return engine(request).snapshot()
    except RuntimeError as e:
        raise HTTPException(409,str(e)) from None

@router.post('/stream/resume')
def resume(request: Request):
    try:
        engine(request).resume()
        return engine(request).snapshot()
    except RuntimeError as e:
        raise HTTPException(409,str(e)) from None

@router.get('/tracks')
def tracks(request: Request):
    return engine(request).snapshot()['targets']

@router.get('/stats')
def stats(request: Request):
    return engine(request).snapshot()

@router.post('/upload-video')
async def upload_video(file: UploadFile=File(...)):
    suffix=Path(file.filename or '').suffix.lower()
    if suffix not in {'.mp4','.avi','.mov','.mkv','.webm'}:
        raise HTTPException(400,'Choose an MP4, AVI, MOV, MKV or WebM video.')
    directory=DATA_DIR/'uploads'
    directory.mkdir(parents=True,exist_ok=True)
    video_id=uuid.uuid4().hex+suffix
    path=directory/video_id
    size=0
    try:
        with path.open('wb') as out:
            while chunk:=await file.read(1024*1024):
                size+=len(chunk)
                if size>MAX_UPLOAD_BYTES:
                    raise HTTPException(413,'Video exceeds the configured upload limit.')
                await asyncio.to_thread(out.write,chunk)
        def inspect():
            cap=cv2.VideoCapture(str(path))
            try:
                ok,frame=cap.read()
                return bool(ok and frame is not None and frame.size>0)
            finally:
                cap.release()
        if not await asyncio.to_thread(inspect):
            raise HTTPException(400,'Video cannot be decoded. Try an H.264 MP4 file.')
        return dict(video_id=video_id,size_bytes=size)
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

@router.get('/sessions')
def sessions(request: Request):
    return engine(request).db.sessions()

@router.get('/sessions/{session_id}/report')
def report(session_id: str,request: Request,format: str='json', kind: str='detections'):
    db=engine(request).db
    report=db.report(session_id)
    if not report:
        raise HTTPException(404,'Session not found.')
    if format=='json':
        content=json.dumps(report,indent=2)
        return StreamingResponse(iter([content]),media_type='application/json',headers={'Content-Disposition':f'attachment; filename="session-{session_id}.json"'})
    if format!='csv':
        raise HTTPException(400,'Format must be json or csv.')
    if kind not in {'detections','tracks'}:
        raise HTTPException(400,'CSV kind must be detections or tracks.')
    def rows():
        buf=io.StringIO()
        writer=csv.DictWriter(buf,fieldnames=['frame_id','source_time','track_id','class_name','x1','y1','x2','y2','confidence'])
        writer.writeheader()
        yield buf.getvalue()
        records=db.observation_rows(session_id) if kind=='tracks' else db.detection_rows(session_id)
        for row in records:
            buf.seek(0); buf.truncate(0)
            writer.writerow(row)
            yield buf.getvalue()
    return StreamingResponse(rows(),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="{kind}-{session_id}.csv"'})

@router.get('/research/results')
def research_results():
    path=DATA_DIR/'reports'/'latest.json'
    if not path.is_file():
        return {'available':False,'note':'Run scripts/evaluate.py against an annotated dataset.'}
    try:
        return {'available':True,'report':json.loads(path.read_text())}
    except (ValueError,OSError):
        raise HTTPException(500,'Evaluation report cannot be read.') from None

async def socket_loop(ws: WebSocket, binary: bool):
    origin=ws.headers.get('origin')
    if origin and origin not in ORIGINS:
        await ws.close(code=1008)
        return
    await ws.accept()
    e=ws.app.state.engine
    queue=e.subscribe()
    async def sender():
        initial=e.snapshot()
        if binary and e.last_packet:
            await ws.send_bytes(e.last_packet)
        else:
            await ws.send_json(initial)
        while True:
            try:
                msg,packet=await asyncio.wait_for(queue.get(),timeout=10)
            except asyncio.TimeoutError:
                msg,packet=e.snapshot(),None
            if binary and packet:
                await asyncio.wait_for(ws.send_bytes(packet),timeout=3)
            else:
                await asyncio.wait_for(ws.send_json(msg),timeout=3)
    async def receiver():
        while True:
            message=await ws.receive()
            if message['type']=='websocket.disconnect':
                return
    tasks=[asyncio.create_task(sender()),asyncio.create_task(receiver())]
    try:
        done,pending=await asyncio.wait(tasks,return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    except (WebSocketDisconnect,asyncio.TimeoutError,RuntimeError):
        pass
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks,return_exceptions=True)
        e.subscribers.discard(queue)
        try:
            await ws.close()
        except RuntimeError:
            pass

@router.websocket('/ws/tracking')
async def tracking_socket(ws: WebSocket):
    await socket_loop(ws,False)

@router.websocket('/ws/frames')
async def frame_socket(ws: WebSocket):
    await socket_loop(ws,True)
