import type {TrackingMessage} from '../types';
import {useStore} from '../store/useStore';
export type SensorFrame={image:ImageBitmap;metadata:TrackingMessage;receivedAt:number;latencyMs:number};
let current:SensorFrame|null=null;
const listeners=new Set<()=>void>();
export const getFrame=()=>current;
export function onFrame(fn:()=>void){listeners.add(fn);return()=>{listeners.delete(fn);};}
export function connectStream(){
 let socket:WebSocket|null=null,closed=false,timer:ReturnType<typeof setTimeout>|undefined,pending:ArrayBuffer|null=null,decoding=false,attempt=0,lastUi=0;
 async function decode(){
  if(decoding)return;decoding=true;
  try{while(pending&&!closed){const packet=pending;pending=null;if(packet.byteLength<4)continue;const length=new DataView(packet).getUint32(0);if(length>packet.byteLength-4||length>4000000)continue;
   const metadata=JSON.parse(new TextDecoder().decode(packet.slice(4,4+length))) as TrackingMessage;
   const image=await createImageBitmap(new Blob([packet.slice(4+length)],{type:'image/jpeg'}));
   if(closed){image.close();break;}
   const old=current;current={image,metadata,receivedAt:performance.now(),latencyMs:Math.max(0,Date.now()-metadata.timestamp*1000)};
   for(const fn of listeners)fn();
   old?.image.close();
   if(performance.now()-lastUi>100||metadata.state!=='RUNNING'){useStore.getState().setMessage(metadata);lastUi=performance.now();}
  }}catch {useStore.getState().setConnected(false);}finally{decoding=false;}
 }
 function open(){
  if(closed)return;
  socket=new WebSocket(`${location.protocol==='https:'?'wss':'ws'}://${location.host}/ws/frames`);socket.binaryType='arraybuffer';
  socket.onopen=()=>{attempt=0;useStore.getState().setConnected(true);};
  socket.onmessage=event=>{if(typeof event.data==='string'){try{useStore.getState().setMessage(JSON.parse(event.data));}catch{/* Ignore malformed status packets. */}}else{pending=event.data;void decode();}};
  socket.onclose=()=>{useStore.getState().setConnected(false);if(!closed)timer=setTimeout(open,Math.min(1000*2**attempt++,10000));};
  socket.onerror=()=>socket?.close();
 }
 open();
 return()=>{closed=true;if(timer)clearTimeout(timer);socket?.close();current?.image.close();current=null;};
}
