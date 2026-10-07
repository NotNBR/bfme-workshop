import test from 'node:test';
import assert from 'node:assert/strict';
import {Simulation, SpatialGrid, STEP} from '../src/simulation.mjs';
import {makeCatalog} from '../src/content.mjs';
const advance=(s,n)=>{for(let i=0;i<n;i++)s.step();};
test('fixed seed and commands reproduce exactly',()=>{
  const a=new Simulation({scale:120}),b=new Simulation({scale:120});
  for(const s of [a,b]){s.issue([1],'attack',2500,1800);advance(s,160);}
  assert.equal(a.save(),b.save());
});
test('shift queue retains order; replace and stop clear it',()=>{
  const s=new Simulation({empty:true}),u=s.spawn('soldier',0,500,500);
  s.issue([u.id],'move',800,700);s.issue([u.id],'attack',900,900,true);
  assert.equal(u.orders.length,2);assert.equal(u.orders[1].kind,'attack');
  s.issue([u.id],'move',600,600);assert.equal(u.orders.length,1);
  s.issue([u.id],'stop',0,0);assert.equal(u.orders.length,0);
});
test('orders reject enemy selection and non-finite destinations',()=>{
  const s=new Simulation({empty:true}),enemy=s.spawn('orc',1,500,500);
  assert.equal(s.issue([enemy.id],'move',100,100),false);
  assert.equal(s.issue([enemy.id],'move',NaN,100,false,1),false);
  assert.equal(enemy.orders.length,0);
});
test('movement arrives and queued order advances',()=>{
  const s=new Simulation({empty:true}),a=s.spawn('hero',0,500,500);
  s.issue([a.id],'move',600,500);s.issue([a.id],'move',800,500,true);advance(s,130);
  assert.ok(a.x>750);assert.equal(a.orders.length,0);
});
test('spatial search returns closest living opponent across cell boundaries',()=>{
  const grid=new SpatialGrid(128);grid.rebuild([{id:1,x:127,y:10,team:0,hp:10},{id:2,x:131,y:10,team:1,hp:10},{id:3,x:128,y:10,team:1,hp:0}]);
  assert.equal(grid.nearest(126,10,0,30).id,2);assert.equal(grid.nearest(0,0,0,20),null);
});
test('hold prevents chasing but still attacks in range',()=>{
  const s=new Simulation({empty:true}),a=s.spawn('hero',0,500,500),b=s.spawn('troll',1,510,500);
  s.issue([a.id],'hold',0,0);s.issue([b.id],'hold',0,0,false,1);
  const x=s.units[0].x;advance(s,40);
  assert.equal(s.units[0].x,x);assert.ok(s.units[1].hp<s.units[1].maxHp);
});
test('recruitment charges once, spawns on completion, and assigns rally order',()=>{
  const s=new Simulation({empty:true});s.catalog.soldier.buildTime=.1;
  assert.equal(s.recruit('soldier'),true);assert.equal(s.resources[0],1200);
  advance(s,2);assert.equal(s.production[0].length,0);assert.equal(s.units.filter(u=>u.team===0).length,15);
  assert.equal(s.squads.find(x=>x.team===0).orders[0].kind,'attack');
});
test('queue cancellation refunds 75 percent and unique hero is enforced',()=>{
  const s=new Simulation({empty:true});s.resources[0]=10000;s.recruit('hero');
  assert.equal(s.recruit('hero'),false);s.cancelProduction(0);assert.equal(s.resources[0],9250);
});
test('uncontested outposts capture and generate extra income',()=>{
  const s=new Simulation({empty:true}),p=s.posts[0];s.spawn('soldier',0,p.x,p.y);
  advance(s,180);assert.equal(p.owner,0);assert.equal(s.income[0],26);
});
test('contested outposts do not capture',()=>{
  const s=new Simulation({empty:true}),p=s.posts[0];s.spawn('soldier',0,p.x,p.y);s.spawn('orc',1,p.x+100,p.y);
  s.capture(10);assert.equal(p.owner,-1);
});
test('healing checks power, affects friendly living units and enforces cooldown',()=>{
  const s=new Simulation({empty:true});s.spawn('hero',0,500,500);const u=s.units[0];u.hp=100;
  assert.equal(s.heal(500,500),false);s.power=60;assert.equal(s.heal(500,500),true);assert.equal(u.hp,1850);assert.equal(s.heal(500,500),false);
});
test('destroyed fortress ends battle',()=>{
  const s=new Simulation({empty:true});s.bases[1].hp=0;s.step();assert.equal(s.winner,0);const t=s.time;s.step();assert.equal(s.time,t);
});
test('an attacking unit can destroy the enemy fortress through normal combat',()=>{
  const s=new Simulation({empty:true});s.bases[1].hp=400;
  const hero=s.spawn('hero',0,4620,1800);s.issue([hero.id],'attack',4700,1800);advance(s,100);
  assert.equal(s.winner,0);assert.equal(s.bases[1].hp,0);
});
test('save and restore continue deterministic simulation',()=>{
  const s=new Simulation({scale:160});advance(s,100);const restored=Simulation.restore(s.save());advance(s,100);advance(restored,100);assert.equal(s.save(),restored.save());
});
test('retail pack applies supported stats while limiting battalion size',()=>{
  const c=makeCatalog({schemaVersion:1,units:{soldier:{health:321,count:999,attackDelayMs:2000},missing:{health:1}}});
  assert.equal(c.soldier.health,321);assert.equal(c.soldier.count,40);assert.equal(c.soldier.cooldown,2);assert.equal(c.missing,undefined);
});
test('6000-unit scenario spawns across the battlefield without invalid positions',()=>{
  const s=new Simulation({scale:6000});assert.ok(s.units.length>=6000);assert.ok(s.units.every(u=>Number.isFinite(u.x)&&u.y>0&&u.y<3600));
});
