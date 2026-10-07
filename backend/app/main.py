import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.routes import router
from app.config import DATA_DIR, ORIGINS, Settings
from app.utils.database import Database
from app.video.engine import Engine

@asynccontextmanager
async def lifespan(app):
    db=Database(DATA_DIR/'swarm.sqlite3')
    saved=db.load_config()
    settings=Settings(**saved) if saved else Settings.from_environment()
    app.state.engine=Engine(db,settings,asyncio.get_running_loop())
    yield
    await asyncio.to_thread(app.state.engine.stop)

app=FastAPI(title='Swarm Drone Tracker',version='1.0.0',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=ORIGINS,allow_methods=['GET','POST'],allow_headers=['Content-Type'])

@app.middleware('http')
async def local_origin_guard(request: Request,call_next):
    origin=request.headers.get('origin')
    if origin and origin not in ORIGINS:
        return JSONResponse({'detail':'Origin is not allowed.'},status_code=403)
    return await call_next(request)

app.include_router(router)
