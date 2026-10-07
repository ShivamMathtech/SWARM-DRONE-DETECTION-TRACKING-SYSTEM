export async function api<T>(path:string,body?:unknown):Promise<T>{
 const response=await fetch('/api'+path,body===undefined?undefined:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 if(!response.ok){let message=`HTTP ${response.status}`;try{const data=await response.json();message=typeof data.detail==='string'?data.detail:JSON.stringify(data.detail);}catch{/* A proxy error may not be JSON. */}throw new Error(message);}
 return response.json();
}
export async function upload(file:File){const data=new FormData();data.append('file',file);const response=await fetch('/api/upload-video',{method:'POST',body:data});const result=await response.json();if(!response.ok)throw new Error(result.detail||'Upload failed');return result as {video_id:string;size_bytes:number};}
