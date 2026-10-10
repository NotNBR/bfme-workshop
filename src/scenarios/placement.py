"""Terrain-checked placement for the authored Eight Kingdoms scenario."""

from common.paths import ROOT
import json
import math
from pathlib import Path
import re
import struct
import sys
import tomllib

import numpy as np

from formats.map import Map
from examples.maps.eight_kingdoms.build import STARTS, WORLD_SHIFT, reference_routes

OUT=ROOT/'local/artifacts/eight-kingdoms/trailer'
PROJECT=ROOT/'examples/scenarios/eight_kingdoms_4v4'
SETTINGS=tomllib.loads((PROJECT/'scenario.toml').read_text())
if SETTINGS['map']!='eight-kingdoms' or SETTINGS['players']!=8:
    raise ValueError('This native scenario adapter requires Eight Kingdoms and eight players')
ARMIES=json.loads((PROJECT/SETTINGS['armies']).read_text())
FACTIONS=ARMIES['factions']
TEMPLATES=ARMIES['templates']
HEAVIES=ARMIES['heavies']
BUILDINGS=json.loads((PROJECT/SETTINGS['buildings']).read_text())
DEPLOYMENTS=json.loads((PROJECT/SETTINGS['deployments']).read_text())
if DEPLOYMENTS['teams']!=[1]*4+[2]*4:
    raise ValueError('This native scenario adapter requires slots 1-4 versus slots 5-8')


def plan(mod, output=None):
    data=(mod/'maps/map mp bfmexbar eight kingdoms/map mp bfmexbar eight kingdoms.map').read_bytes()
    m=Map(data);hm=m.heightmap();z=hm['elevations'].astype(float)/25.6;border=hm['border']
    valid=set(re.findall(r'^\s*(?:Object|ChildObject|ObjectReskin)\s+(\w+)',
        '\n'.join(p.read_text(encoding='cp1252') for p in (mod/'data/ini/object').rglob('*.ini')),re.M))
    for group in [*TEMPLATES,*BUILDINGS.values(),*HEAVIES.values()]:
        for name in group:
            if name not in valid:raise ValueError('Missing native template '+name)
    bases=np.asarray(STARTS)+WORLD_SHIFT
    centers=np.array([bases[f['base']] if 'base' in f else f['position'] for f in DEPLOYMENTS['fronts']])
    front_names=DEPLOYMENTS['front_names']
    axes=DEPLOYMENTS['axes']
    rng=np.random.default_rng(DEPLOYMENTS['seed'])
    roads=np.asarray([p for route in reference_routes() for p in route])+WORLD_SHIFT
    occupied=[];units=[];checks=[]
    obstacles=[(o['x'],o['y']) for o in m.objects()
               if o['template'].startswith(('Osgiliath','DarkRock','DolGoldur'))]
    def placement(desired,center,sign,axis,front,radius=450):
        candidates=[]
        for dy in range(-radius,radius+1,30):
            for dx in range(-radius,radius+1,30):
                x,y=desired+np.array([dx,dy]);ix=round(x/10)+border;iy=round(y/10)+border
                patch=z[iy-5:iy+6,ix-5:ix+6]
                if patch.shape!=(11,11) or patch.min()<100 or np.ptp(patch)>18:continue
                if np.dot(np.array([x,y])-center,axis)*sign<140:continue
                if front in (1,2) and min(np.linalg.norm(bases-[x,y],axis=1))<1250:continue
                # Both formations must have a dry, traversable approach to contact.
                line=np.linspace([x,y],center,35)
                heights=z[np.rint(line[:,1]/10).astype(int)+border,np.rint(line[:,0]/10).astype(int)+border]
                if heights.min()<100 or np.max(np.abs(np.diff(heights)))>22:continue
                if any(math.hypot(x-a,y-b)<205 for a,b in bases):continue
                if any(math.hypot(x-a,y-b)<105 for a,b in occupied):continue
                if any(math.hypot(x-a,y-b)<75 for a,b in obstacles):continue
                candidates.append((dx*dx+dy*dy,x,y,float(np.ptp(patch))))
        if not candidates:raise ValueError(f'No safe army position near {desired}')
        _,x,y,rise=min(candidates);occupied.append((x,y));checks.append(dict(x=x,y=y,relief=rise))
        return [x,y,0.]
    for front,center in enumerate(centers):
        axis=np.array([math.cos(axes[front]),math.sin(axes[front])]);cross=np.array([-axis[1],axis[0]])
        for side,player in enumerate((front,front+4)):
            sign=-1 if side==0 else 1
            for n in range(13):
                hero=n==12
                col=n%3;row=n//3
                desired=center+axis*sign*(215+row*95+rng.uniform(-35,35))+cross*((col-1)*150+rng.uniform(-45,45))
                if hero:desired=center+axis*sign*290+cross*235
                position=placement(desired,center,sign,axis,front)
                role=3 if hero else (0 if n<6 else 1 if n<9 else 2)
                destination=[float(center[0]),float(center[1]),160.]
                # Four staggered fronts; rear ranks march in as reserves.
                release=20+front*38+(45 if n>=9 and not hero else 0)
                units.append(dict(player=player,horde=int(not hero),release=release,
                    position=position,destination=destination,angle=axes[front]+(0. if sign<0 else math.pi),
                    name=TEMPLATES[player][role],front=front))
    # Reinforce each army with real native siege/monster objects. Keep ranged
    # artillery behind the infantry and melee monsters on the forward flanks.
    for front,center in enumerate(centers):
        axis=np.array([math.cos(axes[front]),math.sin(axes[front])]);cross=np.array([-axis[1],axis[0]])
        for side,player in enumerate((front,front+4)):
            sign=-1 if side==0 else 1
            for n,name in enumerate(HEAVIES[FACTIONS[player]]):
                ranged=any(word in name for word in ('Catapult','Trebuchet','Ballista','Giant'))
                desired=center+axis*sign*(560 if ranged else 210)+cross*((-1 if n%2 else 1)*(280+75*(n//2)))
                position=placement(desired,center,sign,axis,front,radius=660)
                units.append(dict(player=player,horde=3,release=10+front*28,
                    position=position,destination=[*map(float,center),160.],angle=axes[front]+(0. if sign<0 else math.pi),
                    name=name,front=front))
    # Give each group its own contact lane instead of stacking every order on
    # the fortress or central rock. Validate the endpoint against actual terrain.
    objectives=[]
    for i,u in enumerate(units):
        front=u['front'];center=centers[front]
        axis=np.array([math.cos(axes[front]),math.sin(axes[front])]);cross=np.array([-axis[1],axis[0]])
        sign=-1 if u['player']<4 else 1
        lane=((i%3)-1)*170+(35 if u['player']%2 else -35)
        desired=center-axis*sign*240+cross*lane
        candidates=[]
        for dy in range(-300,301,30):
            for dx in range(-300,301,30):
                x,y=desired+[dx,dy];ix=round(x/10)+border;iy=round(y/10)+border
                patch=z[iy-4:iy+5,ix-4:ix+5]
                if patch.shape!=(9,9) or patch.min()<100 or np.ptp(patch)>16:continue
                if any(math.hypot(x-a,y-b)<250 for a,b in bases):continue
                if any(math.hypot(x-a,y-b)<110 for a,b in obstacles):continue
                if np.linalg.norm(np.array([x,y])-center)>630:continue
                line=np.linspace(u['position'][:2],[x,y],45)
                heights=z[np.rint(line[:,1]/10).astype(int)+border,np.rint(line[:,0]/10).astype(int)+border]
                if heights.min()<100 or np.max(np.abs(np.diff(heights)))>22:continue
                candidates.append((dx*dx+dy*dy,x,y))
        if not candidates:raise ValueError(f'No clear contact lane for {u["name"]}')
        _,x,y=min(candidates);u['destination']=[float(x),float(y),160.]
        objectives.append(dict(front=front,x=x,y=y))
    structures=[]
    for player,base in enumerate(bases):
        # Each settlement grows beside a different bent lane. Production forms
        # loose clusters; resource buildings spread farther into the outskirts.
        inward=np.array([5700.,6000.])-base;inward/=np.linalg.norm(inward)
        cross=np.array([-inward[1],inward[0]])
        lane_side=-1 if player in (0,2,5) else 1
        district=base+inward*rng.uniform(280,420)+cross*lane_side*rng.uniform(250,440)
        for n,name in enumerate(BUILDINGS[FACTIONS[player]]):
            if n<3:
                angle=rng.uniform(0,math.tau)
                desired=base+np.array([math.cos(angle),math.sin(angle)])*rng.uniform(610,980)
            elif n==7:
                desired=base+inward*rng.uniform(650,850)-cross*lane_side*rng.uniform(100,330)
            else:
                desired=district+inward*rng.uniform(-340,360)+cross*rng.uniform(-230,230)
            candidates=[]
            for dy in range(-720,721,40):
                for dx in range(-720,721,40):
                    x,y=desired+np.array([dx,dy]);ix=round(x/10)+border;iy=round(y/10)+border
                    patch=z[iy-6:iy+7,ix-6:ix+7]
                    if patch.shape!=(13,13) or patch.min()<100 or np.ptp(patch)>12:continue
                    if any(math.hypot(x-a,y-b)<250 for a,b in bases):continue
                    if any(math.hypot(x-a,y-b)<150 for a,b in occupied):continue
                    if any(math.hypot(x-a,y-b)<205 for a,b in structures):continue
                    if any(math.hypot(x-a,y-b)<135 for a,b in obstacles):continue
                    if min(np.linalg.norm(roads-[x,y],axis=1))<95:continue
                    if min(np.linalg.norm(centers[[1,2]]-[x,y],axis=1))<1250:continue
                    candidates.append((dx*dx+dy*dy,x,y,float(np.ptp(patch))))
            if not candidates:raise ValueError(f'No building foundation for {player}: {name}')
            _,x,y,rise=min(candidates);structures.append((x,y))
            checks.append(dict(x=x,y=y,relief=rise,building=name))
            # Face the nearest approach with small individual deviations.
            nearest=roads[np.argmin(np.linalg.norm(roads-[x,y],axis=1))]
            angle=math.atan2(nearest[1]-y,nearest[0]-x)+rng.uniform(-.28,.28)
            units.append(dict(player=player,horde=2,release=0,position=[x,y,0.],destination=[x,y,0.],angle=angle,name=name,front=-1))
    import hashlib
    result=dict(map_sha256=hashlib.sha256(data).hexdigest(),factions=FACTIONS,
        teams=DEPLOYMENTS['teams'],fronts=centers.tolist(),front_names=front_names,field_fronts=DEPLOYMENTS['field_fronts'],
        battalions=96,heroes=8,heavy_units=32,completed_buildings=64,units=units,placement_checks=checks,contact_lanes=objectives)
    output=Path(output or OUT)
    output.mkdir(parents=True,exist_ok=True);(output/'battle-plan.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
