import {useEffect,useRef,useState} from 'react';
import {getFrame,onFrame} from '../services/stream';
import {useStore} from '../store/useStore';
import {drawHud,hitTarget,brackets} from '../hud/draw';

export function SeekerView(){
 const canvas=useRef<HTMLCanvasElement>(null);const selected=useStore(s=>s.selected),visual=useStore(s=>s.visual),setVisual=useStore(s=>s.setVisual);
 useEffect(()=>{
  const draw=()=>{const c=canvas.current?.getContext('2d');if(!c)return;c.clearRect(0,0,320,182);c.fillStyle='#101611';c.fillRect(0,0,320,182);
   const f=getFrame(),t=f?.metadata.targets.find(t=>t.id===useStore.getState().selected),zoom=useStore.getState().visual.zoom;
   if(f&&t&&t.status!=='LOST'){
    // Digital source-pixel magnification, centered at the selected observation.
    const sw=Math.min(f.image.width,320/zoom,f.image.height*320/182),sh=sw*182/320,sx=Math.max(0,Math.min(f.image.width-sw,t.center[0]-sw/2)),sy=Math.max(0,Math.min(f.image.height-sh,t.center[1]-sh/2));
    c.imageSmoothingEnabled=true;c.drawImage(f.image,sx,sy,sw,sh,0,0,320,182);
    c.strokeStyle='#00ff40';c.lineWidth=1;const b=t.bbox;brackets(c,[(b[0]-sx)/sw*320,(b[1]-sy)/sh*182,(b[2]-sx)/sw*320,(b[3]-sy)/sh*182]);
   }else{c.fillStyle='#799580';c.font='11px monospace';c.textAlign='center';c.fillText(t?'OBSERVATION LOST':'SELECT A TRACK',160,96);c.textAlign='left';}
  };draw();const unsubscribe=onFrame(draw);const unsubStore=useStore.subscribe(draw);return()=>{unsubscribe();unsubStore();};
 },[]);
 if(!visual.seeker)return null;
 return <section className="seeker" aria-label="Selected track zoom"><header><span>SEEKER VIEW</span><span>{selected||'NO SELECTION'}</span></header><canvas ref={canvas} width={320} height={182}/><footer><span>ACTUAL FRAME CROP</span><select aria-label="Seeker zoom" value={visual.zoom} onChange={e=>setVisual({zoom:Number(e.target.value)})}>{[2,3,4].map(z=><option key={z} value={z}>{z}.0×</option>)}</select></footer></section>;
}
export function CameraView(){
 const canvas=useRef<HTMLCanvasElement>(null),viewport=useRef<HTMLDivElement>(null);const message=useStore(s=>s.message),connected=useStore(s=>s.connected),visual=useStore(s=>s.visual);const [renderMs,setRenderMs]=useState(0);const [endToEnd,setEndToEnd]=useState(0);
 useEffect(()=>{let raf=0,lastMetric=0;
  const paint=(now:number)=>{const c=canvas.current?.getContext('2d'),f=getFrame();if(c&&f){const start=performance.now();if(c.canvas.width!==f.image.width||c.canvas.height!==f.image.height){c.canvas.width=f.image.width;c.canvas.height=f.image.height;}c.drawImage(f.image,0,0);const s=useStore.getState();drawHud(c,f.metadata,s.selected,s.visual,s.config?.confidence_threshold??.4,now);if(now-lastMetric>1000){setRenderMs(performance.now()-start);setEndToEnd(f.latencyMs);lastMetric=now;}}raf=requestAnimationFrame(paint);};
  raf=requestAnimationFrame(paint);return()=>cancelAnimationFrame(raf);
 },[]);
 const visible=message?.targets.filter(t=>t.status!=='LOST')||[],lost=message?.targets.filter(t=>t.status==='LOST')||[];
 return <div className={`camera ${visual.scanlines?'scanlines':''}`} ref={viewport} style={{aspectRatio:message?`${message.width}/${message.height}`:'16/9'}}>
  <canvas ref={canvas} width={1280} height={720} aria-label="Live camera HUD. Select a track using its bracket or the track list below." onClick={e=>{const f=getFrame();if(!f)return;const r=e.currentTarget.getBoundingClientRect();const t=hitTarget(f.metadata.targets,(e.clientX-r.left)/r.width*f.metadata.width,(e.clientY-r.top)/r.height*f.metadata.height);useStore.getState().select(t?.id||null);}}/>
  {!message?.frame_id&&<div className="standby"><div className="standby-reticle">＋</div><h2>SENSOR STANDBY</h2><p>Choose a source. Start observation.</p><small>Demo works without a camera or model weights.</small></div>}
  <div className="top-telemetry left"><b>{message?.demo?'DEMO MODE · SYNTHETIC':'EO / VIS · OBSERVATION'}</b><span>DETECTION {message?.demo?'SIMULATED':'YOLO'}</span><span>TRACKING <strong>{message?.state||'STANDBY'}</strong></span><span>IN VIEW {String(visible.length).padStart(2,'0')} <i>/</i> FPS {message?.fps.toFixed(1)||'0.0'}</span></div>
  <div className="top-telemetry right"><b><i className={`dot ${connected?'online':''}`}/>{connected?'SENSOR LINK ONLINE':'SENSOR LINK OFFLINE'}</b><span>MODEL {message?.demo?'SYNTHETIC':message?.model.split('/').pop()||'N/A'}</span><span>{message?.demo?'SIM GEN':'YOLO'} {message?.inference_ms.toFixed(1)||'0.0'} ms</span><span>TRACKER {message?.tracker_ms.toFixed(1)||'0.0'} ms</span><span>RENDER {renderMs.toFixed(1)} ms</span><span>APP E2E {message?.state==='RUNNING'?endToEnd.toFixed(0)+' ms':'N/A'}</span></div>
  <div className="swarm-summary"><span>RETAINED TRACKS <b>{String(message?.targets.length||0).padStart(2,'0')}</b></span><span>VISIBLE <b>{String(visible.length).padStart(2,'0')}</b></span><span>LOST <b>{String(lost.length).padStart(2,'0')}</b></span><span>MEAN DET CONF <b>{visible.length?(visible.reduce((n,t)=>n+t.confidence,0)/visible.length*100).toFixed(0)+'%':'N/A'}</b></span><span className="physical">RNG N/A · ALT N/A · SPD N/A</span></div>
  <SeekerView/>
  {message?.frame_id!==0&&message?.state==='PAUSED'&&<div className="state-badge">PAUSED · LAST FRAME</div>}
  {message?.frame_id!==0&&['STOPPED','ERROR','STOPPING'].includes(message?.state||'')&&<div className="state-badge">{message?.state} · LAST FRAME</div>}
  {!connected&&message?.frame_id!==0&&<div className="state-badge">LINK LOST · LAST FRAME</div>}
  <button className="fullscreen" aria-label="Expand camera" onClick={()=>{if(document.fullscreenElement)void document.exitFullscreen();else void viewport.current?.requestFullscreen();}}>⛶</button>
 </div>;
}
