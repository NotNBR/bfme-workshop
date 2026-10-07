// Original prototype defaults. Local retail fields override only supported values.
export const TYPES = {
  soldier: {name:'Gondor soldiers', glyph:'◆', faction:0, count:15, health:200, damage:32, range:24, cooldown:1, speed:68, cost:200, buildTime:12, role:'infantry'},
  archer: {name:'Gondor archers', glyph:'⌁', faction:0, count:15, health:100, damage:24, range:260, cooldown:1.8, speed:62, cost:300, buildTime:15, role:'archer'},
  cavalry: {name:'Gondor knights', glyph:'♞', faction:0, count:10, health:600, damage:48, range:30, cooldown:1.3, speed:132, cost:700, buildTime:24, role:'cavalry'},
  ranger: {name:'Ithilien rangers', glyph:'⌁', faction:0, count:10, health:200, damage:42, range:350, cooldown:1.5, speed:76, cost:600, buildTime:20, role:'archer'},
  hero: {name:'Aragorn', glyph:'✦', faction:0, count:1, health:3500, damage:250, range:40, cooldown:.75, speed:95, cost:3000, buildTime:40, role:'hero'},
  orc: {name:'Mordor warriors', glyph:'◆', faction:1, count:20, health:125, damage:16, range:24, cooldown:1.4, speed:70, cost:50, buildTime:9, role:'infantry'},
  orcarcher: {name:'Orc archers', glyph:'⌁', faction:1, count:20, health:150, damage:22, range:240, cooldown:1.8, speed:62, cost:300, buildTime:15, role:'archer'},
  troll: {name:'Attack trolls', glyph:'⬟', faction:1, count:1, health:3000, damage:400, range:38, cooldown:1.4, speed:88, cost:1100, buildTime:30, role:'monster'},
  siege: {name:'Mordor catapult', glyph:'✣', faction:1, count:1, health:2000, damage:200, range:480, cooldown:6, speed:40, cost:400, buildTime:25, role:'siege'},
};
export function makeCatalog(pack) {
  const types = structuredClone(TYPES);
  if (pack?.schemaVersion !== 1) return types;
  for (const [key, data] of Object.entries(pack.units ?? {})) {
    if (!types[key]) continue;
    for (const prop of ['health','damage','range','cost','buildTime','count']) {
      const val = data[prop];
      if (Number.isFinite(val) && val > 0 && val < 100000) types[key][prop] = val;
    }
    types[key].count = Math.min(40, Math.max(1, Math.round(types[key].count)));
    if (Number.isFinite(data.attackDelayMs) && data.attackDelayMs > 0) types[key].cooldown = Math.max(.25, data.attackDelayMs / 1000);
    types[key].source = data.object;
    if (typeof data.portrait === 'string' && /^\/local-content\/portraits\/[a-z]+\.png$/.test(data.portrait)) types[key].portrait = data.portrait;
  }
  return types;
}
export const WORLD = {width:5200, height:3600};
export const POSTS = [
  {x:1150,y:1050,name:'North watch'}, {x:2600,y:800,name:'The high pass'},
  {x:2600,y:1800,name:'Osgiliath crossing'}, {x:2600,y:2850,name:'South ford'},
  {x:4050,y:2550,name:'Ashen outpost'},
];
