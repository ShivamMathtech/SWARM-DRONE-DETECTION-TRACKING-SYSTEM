import type {Target,TrackingMessage,Visual} from '../types';
const GREEN='#00ff40', AMBER='#edc65d', RED='#ff6a65';
export function brackets(c:CanvasRenderingContext2D,b:number[],selected=false){
 const [x1,y1,x2,y2]=b,p=selected?6:0,l=Math.min(15,(x2-x1)/3,(y2-y1)/3);c.beginPath();
 for(const [x,y,dx,dy] of [[x1-p,y1-p,1,1],[x2+p,y1-p,-1,1],[x1-p,y2+p,1,-1],[x2+p,y2+p,-1,-1]]){c.moveTo(x+dx*l,y);c.lineTo(x,y);c.lineTo(x,y+dy*l);}c.stroke();
}
export function drawHud(c:CanvasRenderingContext2D,m:TrackingMessage,selected:string|null,v:Visual,threshold:number,now:number){
 const w=m.width,h=m.height,cx=w/2,cy=h/2,scale=w/1280;
 c.save();c.strokeStyle=GREEN;c.fillStyle=GREEN;c.lineWidth=1*scale;c.font=`${12*scale}px ui-monospace, monospace`;
 if(v.crosshair){
  c.globalAlpha=.45;c.beginPath();c.moveTo(0,cy);c.lineTo(cx-34*scale,cy);c.moveTo(cx+34*scale,cy);c.lineTo(w,cy);c.moveTo(cx,40*scale);c.lineTo(cx,cy-34*scale);c.moveTo(cx,cy+34*scale);c.lineTo(cx,h-22*scale);c.stroke();c.globalAlpha=.9;
  c.beginPath();c.moveTo(cx-10*scale,cy);c.lineTo(cx+10*scale,cy);c.moveTo(cx,cy-10*scale);c.lineTo(cx,cy+10*scale);c.stroke();
  brackets(c,[cx-47*scale,cy-44*scale,cx+47*scale,cy+44*scale]);
  c.globalAlpha=.12;c.beginPath();c.arc(cx,cy,82*scale,now*.00013,now*.00013+.33);c.stroke();c.globalAlpha=1;
 }
 for(const t of m.targets){
  const color=t.status==='LOST'?RED:t.confidence<threshold+.12?AMBER:GREEN;
  c.strokeStyle=color;c.fillStyle=color;c.lineWidth=(t.id===selected?1.8:1)*scale;
  if(v.trajectory&&t.trajectory.length>1){c.setLineDash([5*scale,6*scale]);c.lineWidth=v.thickness*scale;for(let i=1;i<t.trajectory.length;i++){c.globalAlpha=v.fade?(.15+.65*i/t.trajectory.length):.65;c.beginPath();c.moveTo(...t.trajectory[i-1] as [number,number]);c.lineTo(...t.trajectory[i] as [number,number]);c.stroke();}c.setLineDash([]);c.globalAlpha=1;}
  c.lineWidth=(t.id===selected?1.8:1.1)*scale;
  if(v.boxes)brackets(c,t.bbox,t.id===selected);
  c.beginPath();c.arc(t.center[0],t.center[1],1.4*scale,0,Math.PI*2);c.fill();
  const tx=Math.min(w-124*scale,t.bbox[2]+11*scale),ty=Math.max(27*scale,t.bbox[1]-3*scale);
  const lines:string[]=[];
  if(v.ids)lines.push(`${t.id}${t.id===selected?' ◁':''} / ${t.class_name.toUpperCase()}`);
  if(v.confidence)lines.push(`CONF ${(t.confidence*100).toFixed(0)}%`);
  if(t.status==='LOST')lines.push(`LOST ${t.missed_s.toFixed(1)}s`);
  else if(t.id===selected)lines.push(`RNG N/A · ALT N/A`,`V ${t.speed_px_s.toFixed(1)} px/s`);
  c.shadowColor='#000';c.shadowBlur=3;
  lines.forEach((line,i)=>c.fillText(line,tx,ty+i*16*scale));c.shadowBlur=0;
 }
 if(m.raw_detections.length){c.strokeStyle=AMBER;c.globalAlpha=.7;c.setLineDash([2,4]);for(const d of m.raw_detections){const b=d.bbox;c.strokeRect(b[0],b[1],b[2]-b[0],b[3]-b[1]);}c.setLineDash([]);c.globalAlpha=1;}
 c.strokeStyle=GREEN;c.fillStyle=GREEN;c.globalAlpha=.65;
 c.fillText(`FRAME ${String(m.frame_id).padStart(6,'0')}    ${m.width} × ${m.height}    T+${m.source_time_s.toFixed(2)} s`,22*scale,h-21*scale);
 c.textAlign='right';c.fillText(`EO / VIS    ${m.device}`,w-22*scale,h-21*scale);
 c.restore();
}
export function hitTarget(targets:Target[],x:number,y:number){
 return [...targets].sort((a,b)=>(a.bbox[2]-a.bbox[0])*(a.bbox[3]-a.bbox[1])-(b.bbox[2]-b.bbox[0])*(b.bbox[3]-b.bbox[1])).find(t=>x>=t.bbox[0]-10&&x<=t.bbox[2]+10&&y>=t.bbox[1]-10&&y<=t.bbox[3]+10);
}
