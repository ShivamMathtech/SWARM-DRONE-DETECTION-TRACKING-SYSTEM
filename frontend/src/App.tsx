import {useEffect,useState} from 'react';
import {connectStream} from './services/stream';
import {api} from './services/api';
import {useStore} from './store/useStore';
import {ControlPanel} from './components/ControlPanel';
import {HudLayout} from './components/HudLayout';
import {Settings} from './components/Settings';
import {Research} from './pages/Research';
import type {Config} from './types';
export default function App(){const [panel,setPanel]=useState<'settings'|'research'|null>(null),[error,setError]=useState('');const connected=useStore(s=>s.connected),m=useStore(s=>s.message);
 useEffect(()=>connectStream(),[]);
 useEffect(()=>{if(connected)api<Config>('/config').then(config=>{useStore.getState().setConfig(config);setError('');}).catch(e=>setError(e.message));},[connected]);
 useEffect(()=>{const key=(e:KeyboardEvent)=>{if(e.key==='Escape')setPanel(null);};window.addEventListener('keydown',key);return()=>window.removeEventListener('keydown',key);},[]);
 return <main><header className="masthead"><div className="brand"><span className="brand-mark">M∕T</span><div><b>MATHTECH</b><small>VISION SYSTEMS / 01</small></div></div><div className="title"><h1>SWARM DRONE TRACKING</h1><span>EO / VIS OBSERVATION CONSOLE</span></div><div className="connection"><span><i className={`dot ${connected?'online':''}`}/>{connected?'SYSTEM ONLINE':'CONNECTING…'}</span><small>LOCAL / RESEARCH v1.0</small></div></header><ControlPanel settings={()=>setPanel('settings')} research={()=>setPanel('research')}/>{error&&<p className="error-banner">{error}</p>}<HudLayout/><footer className="system-footer"><span>OBSERVATION ONLY <i>/</i> DEVELOPED BY SHIVAM SINGH</span><span>PIPELINE {m?.pipeline_ms.toFixed(1)||'0.0'} ms <i>/</i> DROPPED {m?.dropped_frames||0} <i>/</i> NO PHYSICAL TELEMETRY</span></footer>{panel==='settings'&&<Settings close={()=>setPanel(null)}/>} {panel==='research'&&<Research close={()=>setPanel(null)}/>}</main>;
}
