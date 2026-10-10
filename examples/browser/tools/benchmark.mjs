import {Simulation} from '../src/simulation.mjs';
import {readFileSync} from 'node:fs';
let pack=null;try{pack=JSON.parse(readFileSync(new URL('../../../local/content/bfme-content.json',import.meta.url),'utf8'));}catch{}
for(const scale of [800,2400,6000]){
  const sim=new Simulation({scale,pack});
  for(const team of [0,1])sim.issue(sim.squads.filter(s=>s.team===team).map(s=>s.id),'attack',2600,1800,false,team);
  const samples=[];for(let i=0;i<600;i++){const t=performance.now();sim.step();samples.push(performance.now()-t);}
  samples.sort((a,b)=>a-b);
  console.log(JSON.stringify({requestedUnits:scale,remaining:sim.units.filter(u=>u.hp>0).length,simulatedSeconds:sim.time,meanMs:samples.reduce((a,b)=>a+b,0)/samples.length,p95Ms:samples[Math.floor(samples.length*.95)],maxMs:samples.at(-1),budgetMs:50}));
}
