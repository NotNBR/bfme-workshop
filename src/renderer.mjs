import {WORLD} from './content.mjs';
export class Renderer {
  constructor(canvas, mini) {
    this.canvas=canvas;this.ctx=canvas.getContext('2d',{alpha:false});this.mini=mini;this.mc=mini.getContext('2d');
    this.camera={x:1800,y:1700,zoom:.42};this.width=innerWidth;this.height=innerHeight;
    this.terrain=this.makeTerrain();this.resize();
    addEventListener('resize',()=>this.resize());
  }
  resize(){this.width=innerWidth;this.height=innerHeight;this.dpr=Math.min(devicePixelRatio,2);this.canvas.width=this.width*this.dpr;this.canvas.height=this.height*this.dpr;}
  center(){return {x:this.width/2,y:(this.height-150)/2};}
  screen(x,y){const c=this.center();return {x:(x-this.camera.x)*this.camera.zoom+c.x,y:(y-this.camera.y)*this.camera.zoom+c.y};}
  world(x,y){const c=this.center();return {x:(x-c.x)/this.camera.zoom+this.camera.x,y:(y-c.y)/this.camera.zoom+this.camera.y};}
  fit(){this.camera={x:WORLD.width/2,y:WORLD.height/2,zoom:Math.min((this.width-110)/WORLD.width,(this.height-350)/WORLD.height)};}
  zoom(delta,x,y){const before=this.world(x,y);this.camera.zoom=Math.max(.07,Math.min(2.8,this.camera.zoom*Math.exp(-delta*.0015)));const after=this.world(x,y);this.camera.x+=before.x-after.x;this.camera.y+=before.y-after.y;this.clampCamera();}
  clampCamera(){this.camera.x=Math.max(0,Math.min(WORLD.width,this.camera.x));this.camera.y=Math.max(0,Math.min(WORLD.height,this.camera.y));}
  makeTerrain(){
    const canvas=document.createElement('canvas');canvas.width=1560;canvas.height=1080;
    const c=canvas.getContext('2d');c.scale(.3,.3);
    const g=c.createLinearGradient(0,0,5200,2000);g.addColorStop(0,'#485238');g.addColorStop(.42,'#626344');g.addColorStop(.62,'#494d38');g.addColorStop(1,'#3c4235');c.fillStyle=g;c.fillRect(0,0,5200,3600);
    let seed=117;const rand=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};
    for(let i=0;i<10000;i++){const x=rand()*5200,y=rand()*3600;c.fillStyle=i%2?'#a49c5510':'#152c1920';c.beginPath();c.ellipse(x,y,10+rand()*90,5+rand()*35,rand()*3,0,Math.PI*2);c.fill();}
    // River Anduin; the prototype terrain is decorative, with no blocked cells.
    const river=()=>{c.beginPath();c.moveTo(2830,-100);c.bezierCurveTo(2200,750,3100,1100,2660,1800);c.bezierCurveTo(2230,2450,2830,2850,2360,3700);};
    river();c.strokeStyle='#98927466';c.lineWidth=180;c.stroke();river();c.strokeStyle='#294944';c.lineWidth=132;c.stroke();river();c.strokeStyle='#46706688';c.lineWidth=55;c.stroke();
    for(let y of [800,1800,2850]){c.beginPath();c.moveTo(200,y+(y-1800)*.2);c.bezierCurveTo(1200,y-90,1900,y+90,2600,y);c.bezierCurveTo(3200,y-100,3800,y+100,5050,y-(y-1800)*.2);c.strokeStyle='#ada07850';c.lineWidth=36;c.stroke();c.strokeStyle='#c4b58c30';c.lineWidth=7;c.stroke();}
    for(let [x,y] of [[2570,800],[2660,1800],[2570,2850]]){c.save();c.translate(x,y);c.rotate(.15);c.fillStyle='#252d24';c.fillRect(-134,-52,270,114);c.fillStyle='#9b997d';c.fillRect(-135,-48,270,90);c.strokeStyle='#6b6f57';c.lineWidth=5;for(let i=-125;i<135;i+=22){c.beginPath();c.moveTo(i,-48);c.lineTo(i,42);c.stroke();}c.fillStyle='#beb493';c.fillRect(-135,-51,270,9);c.fillRect(-135,40,270,9);c.restore();}
    // Woodland clusters frame the playable lanes.
    for(let i=0;i<2600;i++){const x=rand()*5200,y=rand()*3600;const lane=Math.min(Math.abs(y-800),Math.abs(y-1800),Math.abs(y-2850));if(lane<180||Math.abs(x-2600)<220||x<700||x>4500)continue;if(Math.sin(x*.006)+Math.cos(y*.009)<.4)continue;
      c.fillStyle='#16271b55';c.beginPath();c.ellipse(x+9,y+16,21,13,0,0,7);c.fill();c.fillStyle=['#243c27','#2e462c','#364c2e'][i%3];c.beginPath();c.arc(x,y,14+rand()*16,0,7);c.fill();c.fillStyle='#5e6a342c';c.beginPath();c.arc(x-5,y-6,10,0,7);c.fill();}
    for(let i=0;i<45;i++){const x=2350+rand()*570,y=1510+rand()*570;if(Math.abs(x-2660)<105)continue;c.save();c.translate(x,y);c.rotate(rand()*.6-.3);c.fillStyle='#252c2444';c.fillRect(8,8,32,45);c.fillStyle='#96947b';c.fillRect(0,0,32,42);c.fillStyle='#515842';c.fillRect(6,6,20,28);c.restore();}
    c.fillStyle='#dcd5af80';c.font='35px Georgia';c.textAlign='center';for(let [text,x,y] of [['G O N D O R',900,300],['O S G I L I A T H',2600,1430],['M O R D O R',4300,300]])c.fillText(text,x,y);
    c.font='italic 27px Georgia';c.fillStyle='#baccc077';c.save();c.translate(2820,2350);c.rotate(-1.3);c.fillText('The Anduin',0,0);c.restore();return canvas;
  }
  fortress(c,b){
    c.save();c.translate(b.x,b.y);const good=b.team===0;
    c.fillStyle='#0004';c.beginPath();c.ellipse(15,30,125,95,0,0,7);c.fill();
    c.fillStyle=good?'#b8b7a1':'#666451';c.strokeStyle=good?'#e1debe':'#939074';c.lineWidth=5;c.fillRect(-84,-70,168,140);c.strokeRect(-84,-70,168,140);c.fillStyle=good?'#606d54':'#313b2c';c.fillRect(-63,-50,126,100);
    for(let x of [-88,60])for(let y of [-75,48]){c.fillStyle=good?'#b8bca2':'#77755f';c.fillRect(x,y,33,34);c.fillStyle=good?'#59706a':'#813b30';c.beginPath();c.moveTo(x-5,y);c.lineTo(x+16,y-30);c.lineTo(x+38,y);c.fill();}
    c.fillStyle=good?'#e2e0bf':'#9c987d';c.fillRect(-23,-65,46,92);c.fillStyle=good?'#81c7b2':'#d5765f';c.fillRect(1,-97,32,19);c.strokeStyle='#d9c690';c.lineWidth=3;c.beginPath();c.moveTo(0,-55);c.lineTo(0,-101);c.stroke();
    c.fillStyle='#121d14';c.fillRect(-80,107,160,8);c.fillStyle=good?'#85ccb5':'#d1816c';c.fillRect(-80,107,160*Math.max(0,b.hp/b.maxHp),8);c.fillStyle='#eee5c9';c.font='20px Georgia';c.textAlign='center';c.fillText(good?'Gondor fortress':'Mordor fortress',0,148);c.restore();
  }
  draw(sim,selected,drag,mouse,mode){
    const c=this.ctx,z=this.camera.zoom,ctr=this.center();c.setTransform(this.dpr,0,0,this.dpr,0,0);c.fillStyle='#111c16';c.fillRect(0,0,this.width,this.height);
    c.save();c.translate(ctr.x,ctr.y);c.scale(z,z);c.translate(-this.camera.x,-this.camera.y);c.drawImage(this.terrain,0,0,WORLD.width,WORLD.height);
    c.strokeStyle='#e3d69a25';c.lineWidth=2/z;c.strokeRect(0,0,WORLD.width,WORLD.height);
    for(const p of sim.posts){c.save();c.translate(p.x,p.y);c.strokeStyle=p.owner===0?'#83cdb4':p.owner===1?'#d7826b':'#d1c295';c.lineWidth=2/z;c.beginPath();c.arc(0,0,95,0,7);c.stroke();if(p.progress>0){c.lineWidth=6/z;c.beginPath();c.arc(0,0,95,-Math.PI/2,-Math.PI/2+p.progress*Math.PI*2);c.stroke();}c.fillStyle='#252e23';c.fillRect(-22,-24,44,48);c.fillStyle=p.owner===0?'#81c7b2':p.owner===1?'#d5765f':'#c7b787';c.beginPath();c.moveTo(-28,-25);c.lineTo(0,-52);c.lineTo(28,-25);c.fill();c.fillRect(1,-74,25,16);c.fillStyle='#e5dfc5';c.font=`${Math.max(16,10/z)}px Georgia`;c.textAlign='center';c.fillText(p.name,0,135);c.restore();}
    for(const base of sim.bases)this.fortress(c,base);
    for(const s of sim.squads)if(selected.has(s.id)&&s.members.length){
      c.strokeStyle='#a6d5bb55';c.lineWidth=1/z;c.beginPath();c.ellipse(s.x,s.y,65,50,0,0,7);c.stroke();
      if(s.orders.length){c.beginPath();c.moveTo(s.x,s.y);for(const p of s.orders)c.lineTo(p.x,p.y);c.setLineDash([8/z,6/z]);c.strokeStyle=s.orders[0].kind==='attack'?'#edb97599':'#a9e5c999';c.stroke();c.setLineDash([]);for(const [i,p] of s.orders.entries()){c.fillStyle='#c9dfa9';c.beginPath();c.arc(p.x,p.y,4/z,0,7);c.fill();if(selected.size<5){c.font=`${10/z}px Segoe UI`;c.fillText(i+1,p.x+8/z,p.y);}}}
    }
    const tl=this.world(-20,-20),br=this.world(this.width+20,this.height+20);
    if(z<.20){
      for(const s of sim.squads){if(!s.members.length)continue;c.fillStyle=s.team===0?'#94d9c5':'#eb997c';c.strokeStyle=selected.has(s.id)?'#f5e6ad':'#142319';c.lineWidth=1.2/z;const size=s.type==='hero'?7/z:4/z;c.beginPath();c.moveTo(s.x,s.y-size);c.lineTo(s.x+size,s.y);c.lineTo(s.x,s.y+size);c.lineTo(s.x-size,s.y);c.closePath();c.fill();c.stroke();}
    }else{
      for(const u of sim.units){if(u.hp<=0||u.x<tl.x||u.x>br.x||u.y<tl.y||u.y>br.y)continue;const def=sim.catalog[u.type],sel=selected.has(u.squad),big=['monster','hero','siege','cavalry'].includes(def.role);const size=def.role==='monster'?10:def.role==='hero'?8:big?7:4.5;
        c.fillStyle=sel?'#b3e4c9':u.team===0?'#92b9b3':'#bf8160';
        if(z<.48){c.fillRect(u.x-size/2,u.y-size/2,Math.max(size,2/z),Math.max(size,2/z));continue;}
        c.save();c.translate(u.x,u.y);c.rotate(u.angle);c.fillStyle='#08140966';c.beginPath();c.ellipse(2,4,size*1.2,size*.7,0,0,7);c.fill();
        if(sel){c.strokeStyle='#bfe6ba';c.lineWidth=1/z;c.beginPath();c.ellipse(0,0,size+3,size+2,0,0,7);c.stroke();}
        c.fillStyle=u.team===0?'#769c9a':'#975e45';c.fillRect(-size,-size*.65,size*1.7,size*1.3);
        c.fillStyle=u.team===0?'#d0d2bd':'#c5af7b';c.beginPath();c.arc(size*.35,0,size*.5,0,7);c.fill();
        c.strokeStyle=def.role==='archer'?'#bca06b':'#d2d2b6';c.lineWidth=1.6;c.beginPath();c.moveTo(2,-size-1);c.lineTo(def.role==='archer'?5:size+10,-size-1);c.stroke();
        if(def.role==='hero'){c.strokeStyle='#f4d88d';c.lineWidth=2;c.beginPath();c.arc(0,0,14,0,7);c.stroke();}c.restore();
        if(sel&&u.hp<u.maxHp){c.fillStyle='#223020';c.fillRect(u.x-8,u.y-13,16,2);c.fillStyle='#acd694';c.fillRect(u.x-8,u.y-13,16*u.hp/u.maxHp,2);}
      }
    }
    for(const e of sim.effects){c.strokeStyle=e.kind==='heal'?'#a7e4b7aa':e.kind==='siege'?'#ffb75d':'#dfd6a866';c.lineWidth=e.kind==='siege'?3:1/z;c.beginPath();if(e.kind==='heal')c.arc(e.x,e.y,250*(1-e.life/2),0,7);else{c.moveTo(e.x,e.y);c.lineTo(e.x2,e.y2);}c.stroke();}
    const rally=sim.rally[0];c.strokeStyle='#a9d4c588';c.lineWidth=1/z;c.beginPath();c.moveTo(rally.x,rally.y+18);c.lineTo(rally.x,rally.y-20);c.lineTo(rally.x+22,rally.y-10);c.lineTo(rally.x,rally.y);c.stroke();
    if(mode==='heal'){const p=this.world(mouse.x,mouse.y);c.strokeStyle='#c6e3b8';c.lineWidth=1/z;c.beginPath();c.arc(p.x,p.y,250,0,7);c.stroke();}
    c.restore();
    if(drag?.button===0&&drag.moved){c.fillStyle='#a9d9bd18';c.strokeStyle='#b1d5b1';c.lineWidth=1;c.fillRect(drag.x,drag.y,mouse.x-drag.x,mouse.y-drag.y);c.strokeRect(drag.x,drag.y,mouse.x-drag.x,mouse.y-drag.y);}
    this.drawMini(sim);
  }
  drawMini(sim){const c=this.mc,w=this.mini.width,h=this.mini.height;c.drawImage(this.terrain,0,0,w,h);const sx=w/WORLD.width,sy=h/WORLD.height;
    for(const p of sim.posts){c.fillStyle=p.owner===0?'#a4ebca':p.owner===1?'#fca17c':'#f1dfb3';c.fillRect(p.x*sx-2,p.y*sy-2,4,4);}
    for(const s of sim.squads){if(!s.members.length)continue;c.fillStyle=s.team===0?'#91e2d0':'#ef9679';c.fillRect(s.x*sx-1,s.y*sy-1,2,2);}
    for(const b of sim.bases){c.fillStyle=b.team===0?'#cdfbe6':'#e9ad7b';c.fillRect(b.x*sx-3,b.y*sy-3,6,6);}
    const tl=this.world(0,83),br=this.world(this.width,this.height-250);c.strokeStyle='#fff5c4';c.lineWidth=1;c.strokeRect(tl.x*sx,tl.y*sy,(br.x-tl.x)*sx,(br.y-tl.y)*sy);
  }
}
