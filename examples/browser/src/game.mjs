import {Simulation, STEP} from './simulation.mjs';
import {Renderer} from './renderer.mjs';
import {WORLD} from './content.mjs';
const $=id=>document.getElementById(id);
const canvas=$('battle'),renderer=new Renderer(canvas,$('minimap'));
let pack=null;
try {const res=await fetch('/local-content/bfme-content.json');if(res.ok)pack=await res.json();} catch { /* Standalone fallback remains playable. */ }
let sim=new Simulation({scale:800,pack}), selected=new Set(),groups=new Map(),started=false,paused=true,speed=1,mode='select',drag=null,mouse={x:0,y:0},keys=new Set(),lastCamera=null;
let last=performance.now(),accumulator=0,uiTime=0,frames=0,fps=60,frameTime=0,simMs=0,toastUntil=0;
const startScreen=$('start-screen');startScreen.close();startScreen.showModal();
if(pack){$('content-status').textContent='LOCAL BFME2 DATA';$('pack-note').textContent=`${Object.keys(pack.units).length} BFME2 definitions imported locally · Schematic visuals · Single player`;}
function toast(text){$('toast').textContent=text;$('toast').style.opacity=1;toastUntil=performance.now()+4200;}
function selectedSquads(){return sim.squads.filter(s=>selected.has(s.id)&&s.members.length&&s.team===0);}
function setMode(next){mode=next;canvas.style.cursor=next==='select'?'default':'crosshair';document.querySelectorAll('[data-order]').forEach(b=>b.classList.toggle('active',b.dataset.order===next));}
function selectArmy(){selected=new Set(sim.squads.filter(s=>s.team===0&&s.members.length).map(s=>s.id));toast(`Selected ${selected.size} battalions`);}
function command(kind,x,y,append){if(!selected.size){toast('Select battalions first.');setMode('select');return;}sim.issue([...selected],kind,x,y,append);toast(`${kind==='attack'?'Attack move':kind==='move'?'Move':kind==='hold'?'Hold ground':'Stop'}${append?' queued':''} · ${selected.size} battalions`);}
function focus(){const ss=selectedSquads();if(!ss.length)return;renderer.camera.x=ss.reduce((n,s)=>n+s.x,0)/ss.length;renderer.camera.y=ss.reduce((n,s)=>n+s.y,0)/ss.length;}
function overview(){if(lastCamera){renderer.camera=lastCamera;lastCamera=null;}else{lastCamera={...renderer.camera};renderer.fit();}}
function pause(){if(!started||startScreen.open||$('help-screen').open)return;paused=!paused;$('pause').textContent=paused?'▶':'Ⅱ';toast(paused?'Battle paused. Orders can still be issued.':'Battle resumed.');}
function openMenu(){paused=true;keys.clear();startScreen.showModal();$('resume').hidden=!started;$('save').hidden=!started;}
function roster(){
  $('roster').replaceChildren();
  for(const type of ['soldier','archer','cavalry','ranger','hero']){const d=sim.catalog[type],b=document.createElement('button');b.className='unit-card';b.dataset.type=type;b.title=`${d.name}: ${d.count} soldiers · ${d.buildTime}s · ${d.health} health per soldier`;
    b.innerHTML=`<b>${d.portrait?`<img src="${d.portrait}" alt="${d.name}">`:d.glyph}</b>${{soldier:'Soldiers',archer:'Archers',cavalry:'Knights',ranger:'Rangers',hero:'Aragorn'}[type]}<span>${d.cost}</span>`;
    b.onclick=()=>{if(sim.recruit(type))toast(`${d.name} added to production`);else toast('Cannot recruit: check resources, queue, or existing hero.');};$('roster').append(b);}
}
function start(){sim=new Simulation({scale:Number($('scale').value),pack});selected.clear();groups.clear();started=true;paused=false;speed=1;accumulator=0;lastCamera=null;setMode('select');renderer.fit();startScreen.close();$('result').hidden=true;$('pause').textContent='Ⅱ';$('speed').textContent='1×';roster();toast('Gondor awaits your orders. Capture the crossings and destroy Mordor’s fortress.');}
$('start').onclick=start;$('menu').onclick=openMenu;$('new-battle').onclick=()=>{$('result').hidden=true;openMenu();};
$('resume').onclick=()=>{startScreen.close();paused=false;$('pause').textContent='Ⅱ';};
$('pause').onclick=pause;$('speed').onclick=()=>{speed=speed===1?2:speed===2?.5:1;$('speed').textContent=speed+'×';};
$('overview').onclick=overview;$('all-army').onclick=selectArmy;
$('save').onclick=()=>{try{localStorage.setItem('bfmexbar-save',sim.save());toast('Battle saved on this browser.');}catch{toast('Could not save: browser storage is full or unavailable.');}};
$('load').onclick=()=>{try{const save=localStorage.getItem('bfmexbar-save');if(!save){toast('No saved battle in this browser.');return;}sim=Simulation.restore(save);started=true;paused=false;selected.clear();groups.clear();accumulator=0;startScreen.close();$('result').hidden=true;roster();renderer.fit();toast('Saved battle loaded.');}catch{toast('Saved battle could not be loaded.');}};
let beforeHelp=false;$('help').onclick=()=>{beforeHelp=paused;paused=true;$('help-screen').showModal();};
$('close-help').onclick=()=>$('help-screen').close();$('help-screen').addEventListener('close',()=>{paused=beforeHelp;});
startScreen.addEventListener('cancel',e=>{if(!started)e.preventDefault();else{paused=false;$('pause').textContent='Ⅱ';}});
$('heal').onclick=()=>{setMode('heal');toast('Click an area to heal your soldiers · 30 power');};
$('rally').onclick=()=>{setMode('rally');toast('Click to set the reinforcement rally point');};
document.querySelectorAll('[data-order]').forEach(b=>b.onclick=()=>{const kind=b.dataset.order;if(kind==='stop'||kind==='hold')command(kind,0,0,false);else{setMode(kind);toast(`Click a destination for ${kind==='attack'?'attack move':'move'}. Shift queues orders.`);}});
document.querySelectorAll('[data-formation]').forEach(b=>b.onclick=()=>{sim.setFormation([...selected],b.dataset.formation);document.querySelectorAll('[data-formation]').forEach(x=>x.classList.toggle('active',x===b));toast(`${b.textContent} formation applied`);});
canvas.addEventListener('contextmenu',e=>e.preventDefault());
canvas.addEventListener('wheel',e=>{e.preventDefault();renderer.zoom(e.deltaY,e.clientX,e.clientY);lastCamera=null;},{passive:false});
canvas.addEventListener('pointerdown',e=>{if(!started)return;mouse={x:e.clientX,y:e.clientY};drag={x:e.clientX,y:e.clientY,button:e.button,moved:false,cam:{...renderer.camera}};canvas.setPointerCapture(e.pointerId);});
canvas.addEventListener('pointermove',e=>{mouse={x:e.clientX,y:e.clientY};if(!drag)return;if(Math.hypot(mouse.x-drag.x,mouse.y-drag.y)>5)drag.moved=true;if(drag.button===1){renderer.camera.x=drag.cam.x-(mouse.x-drag.x)/renderer.camera.zoom;renderer.camera.y=drag.cam.y-(mouse.y-drag.y)/renderer.camera.zoom;renderer.clampCamera();}});
canvas.addEventListener('pointerup',e=>{
  if(!drag)return;const p=renderer.world(e.clientX,e.clientY),d=drag;drag=null;
  if(d.button===1)return;
  if(d.button===2){const enemy=sim.grid.nearest(p.x,p.y,0,35/renderer.camera.zoom);command(mode==='attack'||enemy?'attack':'move',p.x,p.y,e.shiftKey);if(!e.shiftKey)setMode('select');return;}
  if(d.button!==0)return;
  if(mode==='rally'){sim.rally[0]={x:Math.max(0,Math.min(WORLD.width,p.x)),y:Math.max(0,Math.min(WORLD.height,p.y))};setMode('select');toast('Rally point set');return;}
  if(mode==='heal'){toast(sim.heal(p.x,p.y)?'The light of the West restores your army.':'Heal needs 30 power and a ready cooldown.');setMode('select');return;}
  if(mode==='move'||mode==='attack'){command(mode,p.x,p.y,e.shiftKey);if(!e.shiftKey)setMode('select');return;}
  if(!e.shiftKey)selected.clear();
  if(d.moved){const a=renderer.world(d.x,d.y),left=Math.min(a.x,p.x),right=Math.max(a.x,p.x),top=Math.min(a.y,p.y),bottom=Math.max(a.y,p.y);for(const u of sim.units)if(u.team===0&&u.hp>0&&u.x>=left&&u.x<=right&&u.y>=top&&u.y<=bottom)selected.add(u.squad);}
  else{let nearest=null,best=28/renderer.camera.zoom;for(const u of sim.units)if(u.team===0&&u.hp>0){const dist=Math.hypot(u.x-p.x,u.y-p.y);if(dist<best){best=dist;nearest=u;}}if(nearest){if(e.shiftKey&&selected.has(nearest.squad))selected.delete(nearest.squad);else selected.add(nearest.squad);}}
});
canvas.addEventListener('pointercancel',()=>{drag=null;});
canvas.addEventListener('dblclick',()=>{const ss=selectedSquads();if(!ss.length)return;const type=ss[0].type;for(const s of sim.squads){const p=renderer.screen(s.x,s.y);if(s.team===0&&s.type===type&&p.x>0&&p.x<renderer.width&&p.y>83&&p.y<renderer.height-240)selected.add(s.id);}});
$('minimap').addEventListener('pointerdown',e=>{const r=$('minimap').getBoundingClientRect();renderer.camera.x=(e.clientX-r.left)/r.width*WORLD.width;renderer.camera.y=(e.clientY-r.top)/r.height*WORLD.height;});
addEventListener('keydown',e=>{
  if(e.target.matches('select,input')||startScreen.open||$('help-screen').open)return;
  if(['Space','Tab','F2','ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(e.code)||(/Digit[1-9]/.test(e.code)&&e.ctrlKey))e.preventDefault();
  keys.add(e.code);if(e.repeat)return;
  if(e.code==='Space')pause();if(e.code==='Tab')overview();if(e.code==='F2')selectArmy();if(e.code==='KeyF')focus();if(e.code==='Escape'){setMode('select');selected.clear();}
  if(e.code==='KeyA')setMode('attack');if(e.code==='KeyM')setMode('move');if(e.code==='KeyH')command('hold',0,0,false);if(e.code==='KeyS')command('stop',0,0,false);if(e.code==='KeyQ')$('heal').click();
  if(/^Digit[1-9]$/.test(e.code)){const n=e.code.slice(-1);if(e.ctrlKey){groups.set(n,[...selected]);toast(`Control group ${n} assigned`);}else{selected=new Set((groups.get(n)??[]).filter(id=>sim.squads.some(s=>s.id===id&&s.members.length)));toast(`Control group ${n} · ${selected.size} battalions`);}}
});
addEventListener('keyup',e=>keys.delete(e.code));addEventListener('blur',()=>{keys.clear();drag=null;if(started){paused=true;$('pause').textContent='▶';}});
function updateUI(){
  const alive=sim.units.filter(u=>u.hp>0),ss=selectedSquads();selected=new Set(ss.map(s=>s.id));
  $('pause').textContent=paused?'▶':'Ⅱ';$('speed').textContent=speed+'×';
  document.querySelectorAll('[data-formation]').forEach(b=>b.classList.toggle('active',ss.length>0&&ss.every(s=>s.formation===b.dataset.formation)));
  $('money').textContent=Math.floor(sim.resources[0]).toLocaleString();$('income').textContent=`+${sim.income[0]} / s`;$('army').textContent=alive.filter(u=>u.team===0).length.toLocaleString();$('power').textContent=`${Math.floor(sim.power)} / 100`;
  $('time').textContent=`${String(Math.floor(sim.time/60)).padStart(2,'0')}:${String(Math.floor(sim.time%60)).padStart(2,'0')}`;
  $('view-mode').textContent=renderer.camera.zoom<.2?'STRATEGIC VIEW':'TACTICAL VIEW';$('perf').textContent=`${fps} FPS · ${simMs.toFixed(1)} ms sim · ${alive.length.toLocaleString()} units`;
  $('selection').textContent=ss.length===1?sim.catalog[ss[0].type].name:ss.length?`${ss.length} battalions selected`:'No battalions selected';
  $('selection-detail').textContent=ss.length?`${ss.reduce((n,s)=>n+s.members.length,0)} soldiers · ${ss.reduce((n,s)=>n+s.orders.length,0)} orders`:'Drag a box across your army';
  $('base-health').value=sim.bases[0].hp;
  $('posts').innerHTML=sim.posts.map(p=>`<div class="post"><i class="${p.owner===0?'good':p.owner===1?'evil':''}"></i><span>${p.name}</span><span>${p.progress>0?Math.round(p.progress*100)+'%':p.owner===0?'+10 / s':p.owner===1?'Mordor':'Neutral'}</span></div>`).join('');
  $('queue').replaceChildren();sim.production[0].forEach((p,i)=>{const b=document.createElement('button');b.title=`${sim.catalog[p.type].name} · ${Math.ceil(p.remaining)}s · click to cancel (75% refund)`;b.innerHTML=`${sim.catalog[p.type].glyph}<i style="width:${100*(1-p.remaining/p.total)}%"></i>`;b.onclick=()=>sim.cancelProduction(i);$('queue').append(b);});
  for(const b of document.querySelectorAll('[data-type]')){const def=sim.catalog[b.dataset.type];b.disabled=sim.resources[0]<def.cost||sim.production[0].length>=12||(b.dataset.type==='hero'&&(alive.some(u=>u.type==='hero')||sim.production[0].some(p=>p.type==='hero')));}
  $('heal').title=sim.powerCooldown>0?`Ready in ${Math.ceil(sim.powerCooldown)}s`:'Heal half health in a 250m area';
  if(sim.winner!==null){$('result').hidden=false;$('result-title').textContent=sim.winner===0?'The West endures.':'The shadow prevails.';$('result-detail').textContent=`${sim.kills[0]} enemies defeated · ${Math.floor(sim.time/60)}m ${Math.floor(sim.time%60)}s`;}
}
function frame(now){
  const elapsed=Math.min(.15,(now-last)/1000);last=now;
  const pan=750*elapsed/renderer.camera.zoom;
  if(keys.has('ArrowLeft'))renderer.camera.x-=pan;if(keys.has('ArrowRight'))renderer.camera.x+=pan;if(keys.has('ArrowUp'))renderer.camera.y-=pan;if(keys.has('ArrowDown'))renderer.camera.y+=pan;renderer.clampCamera();
  if(!paused){accumulator+=elapsed*speed;let steps=0;const t=performance.now();while(accumulator>=STEP&&steps<6){sim.step();accumulator-=STEP;steps++;}if(steps)simMs=(performance.now()-t)/steps;if(steps===6)accumulator=Math.min(accumulator,STEP);}
  renderer.draw(sim,selected,drag,mouse,mode);
  frames++;frameTime+=elapsed;if(frameTime>=1){fps=Math.round(frames/frameTime);frames=0;frameTime=0;}
  uiTime+=elapsed;if(uiTime>.2){updateUI();uiTime=0;}
  if(now>toastUntil)$('toast').style.opacity=.0;
  requestAnimationFrame(frame);
}
roster();updateUI();requestAnimationFrame(frame);
// Read-only diagnostics for automated smoke checks and performance inspection.
Object.defineProperty(window,'workshop',{value:{get status(){return {started,paused,units:sim.units.filter(u=>u.hp>0).length,selected:selected.size,tick:sim.tick,winner:sim.winner,imported:!!pack};}},writable:false});
