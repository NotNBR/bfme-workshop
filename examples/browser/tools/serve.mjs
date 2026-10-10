import http from 'node:http';
import {readFile,stat} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFile} from 'node:child_process';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const contentRoot=path.resolve(root,'../..','local/content');
const port=Number(process.env.PORT??8077);
if(!Number.isInteger(port)||port<1||port>65535)throw Error('PORT must be an integer from 1 to 65535');
const types={'.html':'text/html; charset=utf-8','.mjs':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json','.png':'image/png','.svg':'image/svg+xml','.ico':'image/x-icon'};
const allowed=new Set(['index.html','style.css','src','local-content']);
const server=http.createServer(async(req,res)=>{
  if(!['GET','HEAD'].includes(req.method)){res.writeHead(405);res.end();return;}
  try{
    const url=new URL(req.url,'http://localhost');
    if(url.pathname==='/healthz'){res.writeHead(200,{'Content-Type':'application/json'});res.end(JSON.stringify({app:'bmfe-workshop',version:'0.1.0'}));return;}
    const decoded=decodeURIComponent(url.pathname).replaceAll('\\','/');
    const parts=decoded.split('/').filter(Boolean);
    if(parts.some(p=>p==='..'||p.startsWith('.')||p.includes(':'))){res.writeHead(403);res.end('Forbidden');return;}
    if(!parts.length)parts.push('index.html');
    if(!allowed.has(parts[0])){res.writeHead(404);res.end('Not found');return;}
    const base=parts[0]==='local-content'?contentRoot:root;
    const file=path.resolve(base,...(parts[0]==='local-content'?parts.slice(1):parts));
    if(!file.startsWith(base+path.sep)){res.writeHead(403);res.end();return;}
    const info=await stat(file);if(!info.isFile()){res.writeHead(404);res.end();return;}
    const data=await readFile(file);
    res.writeHead(200,{'Content-Type':types[path.extname(file)]??'application/octet-stream','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});res.end(req.method==='HEAD'?undefined:data);
  }catch{res.writeHead(404);res.end('Not found');}
});
server.on('error',async e=>{
  if(e.code==='EADDRINUSE'&&process.argv.includes('--open')){
    try{const response=await fetch(`http://127.0.0.1:${port}/healthz`,{signal:AbortSignal.timeout(1500)});const status=await response.json();if(status.app==='bmfe-workshop'){console.log('Opening the running bmfe-workshop server.');openBrowser();return;}}catch{}
  }
  console.error(`Could not start bmfe-workshop: ${e.message}`);process.exitCode=1;
});
function openBrowser(){
  const url=`http://127.0.0.1:${port}`;
  if(process.platform==='win32')execFile('explorer.exe',[url],()=>{});
  else execFile(process.platform==='darwin'?'open':'xdg-open',[url],()=>{});
}
server.listen(port,'127.0.0.1',()=>{
  console.log(`bmfe-workshop is ready: http://127.0.0.1:${port}\nCtrl+C stops the local server.`);
  if(process.argv.includes('--open'))openBrowser();
});
