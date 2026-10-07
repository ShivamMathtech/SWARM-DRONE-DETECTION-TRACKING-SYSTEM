import {CameraView} from './CameraView';
import {TargetInfo,TargetManager,EventLog} from './TargetManager';
export function HudLayout(){return <><CameraView/><div className="lower-panels"><TargetInfo/><TargetManager/><EventLog/></div></>;}
