import {create} from 'zustand';
import type {Config,TrackingMessage,Visual} from '../types';
const defaultVisual:Visual={boxes:true,ids:true,confidence:true,trajectory:true,crosshair:true,seeker:true,fade:true,thickness:1,zoom:3,scanlines:true};
let stored:Partial<Visual>={};
try {stored=JSON.parse(localStorage.getItem('swarm.visual')||'{}');} catch { /* Recover malformed preferences with defaults. */ }
interface State {message:TrackingMessage|null;selected:string|null;connected:boolean;config:Config|null;visual:Visual;setMessage:(m:TrackingMessage)=>void;select:(id:string|null)=>void;setConnected:(v:boolean)=>void;setConfig:(v:Config)=>void;setVisual:(v:Partial<Visual>)=>void}
export const useStore=create<State>((set,get)=>({message:null,selected:null,connected:false,config:null,visual:{...defaultVisual,...stored},
 setMessage:m=>{let selected=get().selected; if(m.session_id!==get().message?.session_id) selected=null; if(selected&&!m.targets.some(t=>t.id===selected)) selected=null; set({message:m,selected});},
 select:id=>set({selected:id}),setConnected:connected=>set({connected}),setConfig:config=>set({config}),
 setVisual:patch=>{const visual={...get().visual,...patch};try{localStorage.setItem('swarm.visual',JSON.stringify(visual));}catch{/* Storage may be disabled. */}set({visual});}
}));
