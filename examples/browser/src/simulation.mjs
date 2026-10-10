import {makeCatalog, WORLD, POSTS} from './content.mjs';
export const STEP = 1 / 20;
const clamp = (v,a,b) => Math.max(a,Math.min(b,v));
const distance = (a,b) => Math.hypot(a.x-b.x,a.y-b.y);

export class SpatialGrid {
  constructor(size=128) { this.size=size; this.cells=new Map(); }
  rebuild(units) {
    this.cells.clear();
    for (const u of units) if(u.hp>0) {
      const key=Math.floor(u.x/this.size)+Math.floor(u.y/this.size)*128;
      const cell=this.cells.get(key);
      if(cell) cell.push(u); else this.cells.set(key,[u]);
    }
  }
  nearest(x,y,team,radius) {
    let best=null, d2=radius*radius;
    const s=this.size;
    for(let cy=Math.floor((y-radius)/s);cy<=Math.floor((y+radius)/s);cy++)
      for(let cx=Math.floor((x-radius)/s);cx<=Math.floor((x+radius)/s);cx++) {
        const cell=this.cells.get(cx+cy*128); if(!cell) continue;
        for(const u of cell) {
          if(u.team===team || u.hp<=0) continue;
          const d=(u.x-x)**2+(u.y-y)**2;
          if(d<d2) {d2=d; best=u;}
        }
      }
    return best;
  }
}

export class Simulation {
  constructor({scale=1600, seed=77, pack=null, empty=false}={}) {
    this.catalog=makeCatalog(pack); this.seed=seed>>>0; this.time=0; this.tick=0;
    this.units=[]; this.squads=[]; this.nextId=1; this.nextSquad=1;
    this.grid=new SpatialGrid(); this.byId=new Map(); this.effects=[];
    this.resources=[1400,1400]; this.income=[16,16]; this.kills=[0,0];
    this.power=0; this.powerCooldown=0; this.production=[[],[]];
    this.rally=[{x:1150,y:1800},{x:4050,y:1800}]; this.cap=8000;
    this.posts=POSTS.map(p=>({...p,owner:-1,progress:0,capturing:-1}));
    this.bases=[{id:-1,team:0,x:500,y:1800,hp:28000,maxHp:28000,base:true},
      {id:-2,team:1,x:4700,y:1800,hp:28000,maxHp:28000,base:true}];
    this.winner=null; this.commandLog=[];
    if(!empty) this.populate(scale);
  }
  random() { this.seed=(Math.imul(this.seed,1664525)+1013904223)>>>0; return this.seed/4294967296; }
  populate(scale) {
    for(let team=0;team<2;team++) {
      let count=0, n=0;
      const kinds=team?['orc','orc','orcarcher','orc','orcarcher','troll','siege']:['soldier','soldier','archer','cavalry','ranger'];
      const mean=kinds.reduce((total,key)=>total+this.catalog[key].count,0)/kinds.length;
      const rows=Math.ceil(scale/2/mean/6);
      while(count<scale/2) {
        const type=kinds[n%kinds.length], col=n%6, row=Math.floor(n/6);
        const x=team?4200-col*115:1000+col*115;
        const y=450+row*Math.min(115,2700/Math.max(1,rows-1));
        this.spawn(type,team,x,y); count+=this.catalog[type].count; n++;
      }
    }
    this.spawn('hero',0,820,1800);
    this.rebuild();
  }
  rebuild() {this.byId=new Map([...this.units,...this.bases].map(u=>[u.id,u]));this.grid.rebuild(this.units);}
  spawn(type,team,x,y) {
    const def=this.catalog[type]; if(!def) return null;
    const squad={id:this.nextSquad++,type,team,x,y,orders:[],formation:'line',stance:'guard',members:[],angle:0};
    for(let i=0;i<def.count;i++) {
      const offset=this.offset(i,def.count,'line',0);
      const u={id:this.nextId++,squad:squad.id,type,team,x:clamp(x+offset.x,20,WORLD.width-20),y:clamp(y+offset.y,20,WORLD.height-20),
        hp:def.health,maxHp:def.health,cooldown:this.random()*def.cooldown,target:0,angle:team?Math.PI:0,slot:i};
      squad.members.push(u.id); this.units.push(u); this.byId.set(u.id,u);
    }
    this.squads.push(squad); return squad;
  }
  offset(i,count,formation,angle) {
    const cols=formation==='column'?3:formation==='wedge'?Math.ceil(Math.sqrt(count)):Math.min(count,5);
    const spacing=formation==='spread'?27:15;
    let x=(Math.floor(i/cols)-Math.floor((count-1)/cols)/2)*spacing;
    let y=(i%cols-(cols-1)/2)*spacing;
    if(formation==='wedge') x=-Math.abs(y);
    return {x:x*Math.cos(angle)-y*Math.sin(angle),y:x*Math.sin(angle)+y*Math.cos(angle)};
  }
  issue(ids,kind,x,y,append=false,team=0) {
    if(!['move','attack','stop','hold'].includes(kind)) return false;
    if(!Number.isFinite(x)||!Number.isFinite(y)) return false;
    const chosen=this.squads.filter(s=>ids.includes(s.id)&&s.team===team&&s.members.length);
    const cols=Math.max(1,Math.ceil(Math.sqrt(chosen.length)));
    chosen.forEach((s,i)=>{
      if(!append || kind==='stop' || kind==='hold') s.orders=[];
      s.stance=kind==='hold'?'hold':'guard';
      if(kind==='move'||kind==='attack') {
        const spacing=100;
        s.orders.push({kind,x:clamp(x+(Math.floor(i/cols)-(Math.ceil(chosen.length/cols)-1)/2)*spacing,60,WORLD.width-60),
          y:clamp(y+(i%cols-(cols-1)/2)*spacing,60,WORLD.height-60)});
      }
      if(kind==='stop'||kind==='hold') {
        for(const id of s.members) {const u=this.byId.get(id);if(u)u.target=0;}
      }
    });
    if(team===0) this.commandLog.push({tick:this.tick,ids:[...ids],kind,x,y,append});
    return !!chosen.length;
  }
  setFormation(ids,formation) {
    if(!['line','column','wedge','spread'].includes(formation)) return;
    for(const s of this.squads) if(s.team===0&&ids.includes(s.id)) s.formation=formation;
  }
  recruit(type,team=0) {
    const def=this.catalog[type];
    if(this.winner!==null||!def||def.faction!==team||this.resources[team]<def.cost||this.production[team].length>=12) return false;
    if(this.units.filter(u=>u.hp>0&&u.team===team).length+this.production[team].reduce((n,p)=>n+this.catalog[p.type].count,0)+def.count>this.cap) return false;
    if(type==='hero'&&(this.units.some(u=>u.type==='hero'&&u.hp>0)||this.production[team].some(p=>p.type==='hero'))) return false;
    this.resources[team]-=def.cost;
    this.production[team].push({type,remaining:def.buildTime,total:def.buildTime}); return true;
  }
  cancelProduction(index,team=0) {
    const [item]=this.production[team].splice(index,1);
    if(item) this.resources[team]+=this.catalog[item.type].cost*.75;
  }
  heal(x,y) {
    if(this.power<30||this.powerCooldown>0||this.winner!==null) return false;
    this.power-=30; this.powerCooldown=35;
    for(const u of this.units) if(u.team===0&&u.hp>0&&Math.hypot(u.x-x,u.y-y)<250) u.hp=Math.min(u.maxHp,u.hp+u.maxHp*.5);
    this.effects.push({x,y,x2:x,y2:y,kind:'heal',life:1.8}); return true;
  }
  ai() {
    const foes=this.squads.filter(s=>s.team===1&&s.members.length);
    const targets=this.posts.filter(p=>p.owner!==1);
    for(const s of foes) {
      if(s.orders.length) continue;
      const target=targets.length?targets[Math.floor(this.random()*targets.length)]:this.bases[0];
      this.issue([s.id],'attack',target.x+(this.random()-.5)*100,target.y+(this.random()-.5)*100,false,1);
    }
    const choices=['orc','orc','orcarcher','troll','siege'];
    if(this.production[1].length<3) this.recruit(choices[Math.floor(this.random()*choices.length)],1);
  }
  step(dt=STEP) {
    if(this.winner!==null) return;
    this.time+=dt; this.tick++;
    this.powerCooldown=Math.max(0,this.powerCooldown-dt);
    this.effects=this.effects.filter(e=>(e.life-=dt)>0);
    this.grid.rebuild(this.units);
    if(this.tick%80===1) this.ai();
    for(let team=0;team<2;team++) {
      this.income[team]=16+this.posts.filter(p=>p.owner===team).length*10;
      this.resources[team]+=this.income[team]*dt;
      const q=this.production[team], job=q[0];
      if(job && (job.remaining-=dt)<=0) {
        const base=this.bases[team];
        const s=this.spawn(job.type,team,base.x+(team?-140:140),base.y+(this.random()-.5)*180);
        const r=this.rally[team];this.issue([s.id],'attack',r.x,r.y,false,team);q.shift();
      }
    }
    for(const s of this.squads) {
      const alive=s.members.map(id=>this.byId.get(id)).filter(u=>u&&u.hp>0);
      s.members=alive.map(u=>u.id);if(!alive.length)continue;
      s.x=alive.reduce((n,u)=>n+u.x,0)/alive.length;s.y=alive.reduce((n,u)=>n+u.y,0)/alive.length;
      let order=s.orders[0];
      if(order&&distance(s,order)<40) {s.orders.shift();order=s.orders[0];}
      if(order)s.angle=Math.atan2(order.y-s.y,order.x-s.x);
      const def=this.catalog[s.type];
      for(let i=0;i<alive.length;i++) {
        const u=alive[i];u.cooldown=Math.max(0,u.cooldown-dt);
        const scan=order?.kind==='move'?def.range:Math.max(def.range+40,190);
        let target=this.byId.get(u.target);
        if(!target||target.hp<=0||distance(u,target)>scan+100)target=null;
        if((this.tick+u.id)%8===0 || (!target&&this.tick%8===0)) {
          target=this.grid.nearest(u.x,u.y,u.team,scan);
          const base=this.bases[1-u.team];
          if(!target&&base.hp>0&&distance(u,base)<scan+65)target=base;
        }
        u.target=target?.id??0;
        const reach=def.range+(target?.base?65:0);
        const d=target?distance(u,target):Infinity;
        if(target&&d<=reach&&u.cooldown<=0) {
          let damage=def.damage;
          if(s.type==='cavalry'&&order) damage*=1.3;
          this.damage(target,damage,u.team);
          u.cooldown=def.cooldown;
          if((def.role==='archer'||def.role==='siege')&&this.effects.length<450)
            this.effects.push({x:u.x,y:u.y,x2:target.x,y2:target.y,kind:def.role,life:.22});
          if(def.role==='monster'||def.role==='siege') {
            // Bounded splash query; same spatial index as acquisition.
            const splash=this.grid.nearest(target.x+7,target.y+7,u.team,45);
            if(splash&&splash!==target)this.damage(splash,damage*.35,u.team);
          }
        }
        let goal=null;
        if(target&&d>reach&&order?.kind!=='move'&&s.stance!=='hold') goal=target;
        else if(order && !(target&&d<=reach&&order.kind==='attack')) {
          const off=this.offset(i,alive.length,s.formation,s.angle);goal={x:order.x+off.x,y:order.y+off.y};
        }
        if(goal) {
          const dx=goal.x-u.x,dy=goal.y-u.y,dist=Math.hypot(dx,dy);
          const amount=Math.min(def.speed*dt,Math.max(0,dist-(goal===target?reach*.85:2)));
          if(dist>0&&amount>0) {u.x=clamp(u.x+dx/dist*amount,15,WORLD.width-15);u.y=clamp(u.y+dy/dist*amount,15,WORLD.height-15);u.angle=Math.atan2(dy,dx);}
        }
      }
    }
    if(this.tick%10===0) this.capture(dt*10);
    if(this.tick%100===0){this.units=this.units.filter(u=>u.hp>0);this.squads=this.squads.filter(s=>s.members.length);this.rebuild();}
    for(const b of this.bases)if(b.hp<=0)this.winner=1-b.team;
  }
  damage(target,amount,team) {
    if(target.hp<=0)return;
    target.hp=Math.max(0,target.hp-amount);
    if(target.hp===0&&!target.base){this.kills[team]++;if(team===0)this.power=Math.min(100,this.power+1.5);}
  }
  capture(dt) {
    for(const p of this.posts) {
      let counts=[0,0];
      for(const s of this.squads)if(s.members.length&&distance(s,p)<180)counts[s.team]+=s.members.length;
      const team=counts[0]&&!counts[1]?0:counts[1]&&!counts[0]?1:-1;
      if(team<0||team===p.owner){p.progress=Math.max(0,p.progress-dt*.1);continue;}
      if(p.capturing!==team){p.capturing=team;p.progress=0;}
      p.progress+=dt/8;
      if(p.progress>=1){p.owner=team;p.progress=0;}
    }
  }
  save() {
    const {grid,byId,...data}=this;
    return JSON.stringify({version:1,data});
  }
  static restore(json) {
    const snapshot=JSON.parse(json);
    if(snapshot.version!==1||!Array.isArray(snapshot.data?.units)||!Array.isArray(snapshot.data?.squads))throw Error('Unsupported save');
    const sim=new Simulation({empty:true});Object.assign(sim,snapshot.data);sim.rebuild();return sim;
  }
}
