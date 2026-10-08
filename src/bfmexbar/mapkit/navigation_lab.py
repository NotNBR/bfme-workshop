"""Original flat corridors for read-only native pathability observations.

Measures UNIT_CAN_PATH_TO_WAYPOINT and optional scripted traversal across
terrain flags, standing-water depths and height-only ridges. Formation clearance,
manual orders, build placement and bridges remain separate experiments.
"""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from bfmexbar.paths import ROOT
from bfmexbar.formats.map import Map, sha
from bfmexbar.mapkit.blank import create, starts, add_object, set_materials, set_heights
from bfmexbar.mapkit.script_writer import Writer, arg


NAME = 'map mp bfmexbar navigation lab'
UNITS = ('GondorFighter', 'GondorCavalry', 'MordorCatapult', 'MordorAttackTroll')
CASES = ('open', 'impassable', 'players', 'extra_override')


def build(catalog, *, movement=False, human_owned=False, surface='flags', water_depths=(0,1,20), slope_rises=(5,10,20)):
    if surface not in ('flags','water','slopes'): raise ValueError('Unknown navigation surface experiment')
    if len(water_depths)!=3 or len(set(water_depths))!=3 or any(not isinstance(d,int) or d<0 or d>1000 for d in water_depths):
        raise ValueError('Use three distinct integer water depths in the lab range 0..1000')
    if len(slope_rises)!=3 or len(set(slope_rises))!=3 or any(not isinstance(d,int) or not 1<=d<=400 for d in slope_rises):
        raise ValueError('Use three distinct integer rises per sample in the lab range 1..400')
    cases_names = (CASES if surface=='flags' else ('flat',)+tuple(f'rise_{d}' for d in slope_rises) if surface=='slopes'
                   else ('dry',)+tuple('water_at_ground' if d==0 else f'water_{d}' for d in water_depths))
    border, size = 8, 256
    m = create(size, size, border, title='BFME Workshop Navigation Lab')
    starts(m, [(180, 160), (2320, 2380)])
    shape = (size + 2*border,)*2
    blocked = np.zeros(shape, dtype='u1')
    players = np.zeros(shape, dtype='u1')
    extra = np.zeros(shape, dtype='u1')
    labels = np.zeros(shape, dtype='u2')
    # Full-width dividers prevent a route around each corridor's test barrier.
    for y in (0,64,128,192,252):
        blocked[border+y:border+y+4,:] = 1
        labels[border+y:border+y+4,:] = 1
    for case in range(1,4):
        region = np.s_[border+64*case:border+64*(case+1),border+120:border+130]
        labels[region] = 1
        if surface=='flags':
            if case in (1,3): blocked[region] = 1
            if case == 2: players[region] = 1
            if case == 3: extra[region] = 1
    set_materials(m, ['DirtMordor04','RockMordor01'], labels, blocked, blend_edges=False)
    b = m.blend()
    payload = bytearray(m.chunk('BlendTileData').data)
    for name, plane in (('impassable_players',players),('extra_passable',extra)):
        raw = np.packbits(plane,axis=1,bitorder='little').tobytes()
        start = b['offsets'][name]
        payload[start:start+len(raw)] = raw
    m.chunk('BlendTileData').data = bytes(payload)
    if surface=='slopes':
        heights=np.full(shape,100.)
        for row,rise in enumerate(slope_rises,1):
            for sample in range(11):
                heights[border+row*64:border+(row+1)*64,border+120+sample]=100+min(sample,10-sample)*rise
        set_heights(m,heights)
    if surface=='water':
        from bfmexbar.formats.water import standing_water
        areas=[]
        for row,depth in enumerate(water_depths,1):
            areas.append(dict(id=row,name=cases_names[row],layer='Water',uv_speed=.06,additive=0,
                bump_texture='WaterRippleBump.tga',sky_texture='SkyEnv.tga',
                points=[(1200,row*640),(1300,row*640),(1300,(row+1)*640),(1200,(row+1)*640)],
                water_height=100+depth,shader='Wtr_Gondor.W3D',depth_colors=''))
        m.chunk('StandingWaterAreas').data=standing_water(areas)
    add_object(m,'GondorFighter',100,100,extra=[('objectName',3,'LAB_Control')])
    w = Writer(m,catalog)
    scripts, alternatives, cases = [], [], []
    text = lambda kind,value: arg(kind,text=value)
    for corridor, case in enumerate(cases_names):
        for row, template in enumerate(UNITS):
            label = f'{case}_{template}'
            y = (corridor*64+16+row*12)*10
            unit, waypoint = 'LAB_Unit_'+label, 'Target_'+label
            owner = 'Player_1' if human_owned else 'PlyrCivilian'
            add_object(m,template,1050 if movement else 400,y,extra=[('objectName',3,unit),
                ('originalOwner',3,owner+'/team'+owner)])
            for suffix,x in (('Target',1550 if movement else 2100),('Result',200)):
                name = suffix+'_'+label
                add_object(m,'*Waypoints/Waypoint',x,y,extra=[('waypointName',3,name),
                    ('waypointID',1,100+corridor*8+row*2+(suffix=='Result')),
                    ('originalOwner',3,'/team')])
            names = ['LAB_Reachable_'+label,'LAB_Blocked_'+label]
            alternatives.append(names)
            condition = w.operation('condition','UNIT_CAN_PATH_TO_WAYPOINT',[text(14,unit),text(7,waypoint)])
            def marker(name,kind):
                return w.operation(kind,'CREATE_NAMED_ON_TEAM_AT_WAYPOINT',[
                    text(14,name),text(15,'GondorFighter'),text(3,'teamPlyrCivilian'),text(7,'Result_'+label)])
            actions = [marker(names[0],'action')]
            false = [marker(names[1],'false_action')]
            if movement:
                actions.append(w.operation('action','MOVE_NAMED_UNIT_TO',[text(14,unit),text(7,waypoint)]))
                false.append(w.operation('false_action','MOVE_NAMED_UNIT_TO',[text(14,unit),text(7,waypoint)]))
            false.append(w.operation('false_action','DISABLE_SCRIPT',[text(2,label)]))
            scripts.append(w.script(label,[[condition]],actions,false))
            ownership = w.operation('condition','NAMED_OWNED_BY_PLAYER',[text(14,unit),text(11,owner)])
            scripts.append(w.script('Owner_'+label,[[ownership]],[marker('LAB_Owner_'+label,'action')]))
            cases.append(dict(case=case,template=template,unit=unit,target=waypoint,
                              reachable_marker=names[0],blocked_marker=names[1]))
    w.install(scripts,side_index=2)
    data=m.encode()
    Map(data).report()
    proof=dict(schema=1,map=NAME,map_sha256=sha(data),minimum_frame=150,
               expected=['LAB_Control']+[prefix+case+'_'+unit for prefix in ('LAB_Unit_','LAB_Owner_') for case in cases_names for unit in UNITS],
               forbidden=[],one_of=alternatives,timer_reference='LAB_Control',timer_checks=[],
               navigation_cases=cases,
               owner=owner,surface=surface,water_depths=water_depths if surface=='water' else None,
               slope_rises=slope_rises if surface=='slopes' else None,
               scope='Path-query truth values and optional scripted traversal; not placement or formation clearance')
    if movement:
        proof.update(duration_seconds=40, minimum_frame=150,
                     movement_cases=[dict(**case,near_bank_x=1200,far_bank_x=1300) for case in cases])
    return m,proof


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--catalog',type=Path,help='Override the bundled BFME2 1.06 signatures')
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--install',action='store_true')
    p.add_argument('--movement',action='store_true',help='Issue move orders and compare actual barrier crossing with path queries')
    p.add_argument('--human-owned',action='store_true',help='Assign units to Player_1 and verify that ownership with native scripts')
    p.add_argument('--surface',choices=('flags','water','slopes'),default='flags')
    p.add_argument('--water-depths',nargs=3,type=int,default=(0,1,20),metavar=('A','B','C'))
    p.add_argument('--slope-rises',nargs=3,type=int,default=(5,10,20),metavar=('A','B','C'))
    args=p.parse_args()
    if args.out.exists() and any(args.out.iterdir()): p.error('Use a new or empty output directory')
    from bfmexbar.mapkit.script_catalog import load_catalog
    m,proof=build(load_catalog(args.catalog),movement=args.movement,human_owned=args.human_owned,surface=args.surface,
                  water_depths=args.water_depths,slope_rises=args.slope_rises)
    args.out.mkdir(parents=True,exist_ok=True)
    data=m.encode();(args.out/(NAME+'.map')).write_bytes(data)
    (args.out/'proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    if args.install:
        config=json.loads((ROOT/'runtime/bfme-host/manifest.json').read_text())
        target=Path(config['mod'])/'maps'/NAME;target.mkdir(parents=True,exist_ok=True)
        path=target/(NAME+'.map');path.write_bytes(data)
        for suffix in ('_art.tga','_pic.tga'):
            Image.new('RGB',(256,256),(90,75,58)).save(target/(NAME+suffix))
        from bfmexbar.mapkit.cache import cache_entry
        cache_entry(path,m,NAME,'BFME Workshop Navigation Lab','Original pathability experiments.')
    print(json.dumps(proof))


if __name__=='__main__':main()
