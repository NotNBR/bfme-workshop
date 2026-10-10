"""Sheltered woods, varied edges, slope-toe geology and small outpost scenes.

Uses native optimized tree assets and preserves broad navigable corridors.
Placement is deterministic and checked against terrain and model footprints.
"""
from collections import Counter
import heapq
import json
import math

import numpy as np
from PIL import Image, ImageDraw


def corridors(k,t,sites):
    walk=(~t['blocked'])|t['decks']
    stride=4;coarse=walk[::stride,::stride]
    z=t['z'][::stride,::stride];slope=t['slope'][::stride,::stride]
    cost=1+slope*4+np.maximum(z-250,0)/35
    h,w=coarse.shape
    def node(p):
        yy,xx=k.cell(p);a,b=round(yy/stride),round(xx/stride)
        candidates=[(math.hypot(c-a,d-b),c,d) for c in range(max(0,a-6),min(h,a+7))
                    for d in range(max(0,b-6),min(w,b+7)) if coarse[c,d]]
        if not candidates:raise ValueError('No route endpoint near '+str(p))
        _,a,b=min(candidates);return a,b
    def path(a,b):
        start,goal=node(a),node(b)
        queue=[(0,0,start)];distances={start:0};previous={}
        while queue:
            _,score,current=heapq.heappop(queue)
            if score!=distances.get(current):continue
            if current==goal:
                nodes=[current]
                while current!=start:current=previous[current];nodes.append(current)
                return [(d*stride,c*stride) for c,d in reversed(nodes)]
            c,d=current
            for e,f in ((c-1,d),(c+1,d),(c,d-1),(c,d+1)):
                if not (0<=e<h and 0<=f<w and coarse[e,f]):continue
                # A sampled node pair may straddle a narrow water/sloped barrier.
                segment=walk[min(c,e)*stride:max(c,e)*stride+1,min(d,f)*stride:max(d,f)*stride+1]
                if not segment.all():continue
                candidate=score+.5*(cost[c,d]+cost[e,f])
                if candidate<distances.get((e,f),math.inf):
                    distances[e,f]=candidate;previous[e,f]=current
                    heapq.heappush(queue,(candidate+abs(e-goal[0])+abs(f-goal[1]),candidate,(e,f)))
        raise ValueError('No protected terrain route between '+str((a,b)))
    pairs=[(p,k.STARTS[(i+1)%6]) for i,p in enumerate(k.STARTS)]
    pairs += [(k.STARTS[s['player']-1],s['position']) for s in sites]
    pairs += [(b['ends'][0],b['ends'][1]) for b in t['bridges']]
    mask=Image.new('L',(walk.shape[1],walk.shape[0]));draw=ImageDraw.Draw(mask)
    routes=[]
    for a,b in pairs:
        points=path(a,b);draw.line(points,fill=255,width=36)
        routes.append(dict(source=a,destination=b,length=sum(math.dist(p,q)*10 for p,q in zip(points,points[1:]))))
    return np.array(mask)>0,routes


def populate(k,m,t,put,rng,sites):
    dy,dx=np.gradient(t['z'],10);t['slope']=np.hypot(dx,dy)
    t['blocked']=(t['z']<k.WATER+8)|(t['slope']>.82)
    routes,route_report=corridors(k,t,sites)
    t['scenery_solids']=np.zeros(t['z'].shape,bool)
    counts=Counter();checks=[]
    def place(template,x,y,layer,gap=50,footprint=8,max_rise=7,solid=0,angle=None,offset=0,site=False):
        if not (100<x<k.WIDTH*10-100 and 100<y<k.HEIGHT*10-100):return False
        iy,ix=k.cell((x,y));r=max(1,math.ceil(footprint/10))
        selection=np.s_[iy-r:iy+r+1,ix-r:ix+r+1]
        patch=t['z'][selection]
        if patch.min()<k.WATER+18 or t['blocked'][selection].any() or routes[selection].any():return False
        if t['protected'][selection].any() and not site:return False
        if site:
            if any(math.dist((x,y),p)<760+footprint for p in k.STARTS):return False
            for b in t['bridges']:
                vx,vy=b['axis'];px,py=b['center']
                if abs((x-px)*vx+(y-py)*vy)<760+footprint and abs(-(x-px)*vy+(y-py)*vx)<210+footprint:return False
        relief=float(np.ptp(patch))
        if relief>max_rise:return False
        if not put(template,x,y,layer,gap=gap,z=offset,angle=angle):return False
        counts[layer]+=1
        checks.append(dict(template=template,position=(x,y),layer=layer,footprint=footprint,
                           relief=relief,max_relief=max_rise,solid_radius=solid))
        if solid:
            radius=math.ceil(solid/10)+1
            yy,xx=np.indices((radius*2+1,radius*2+1))
            disk=((xx-radius)*10)**2+((yy-radius)*10)**2<=(solid+7)**2
            t['scenery_solids'][iy-radius:iy+radius+1,ix-radius:ix+radius+1]|=disk
        return True
    eligible=(t['z']>k.WATER+48)&(t['z']<280)&(t['slope']<.27)&(~t['protected'])&(~routes)
    centers=[]
    desired=[]
    for i,p in enumerate(k.STARTS):
        heading=math.atan2(k.HEIGHT*5-p[1],k.WIDTH*5-p[0])+.70*(-1 if i%2 else 1)
        desired.append((p[0]+math.cos(heading)*1230,p[1]+math.sin(heading)*1230))
    desired += [(u*k.WIDTH*10,v*k.HEIGHT*10) for u,v in
                [(.29,.79),(.48,.63),(.71,.78),(.81,.60),(.32,.27),(.51,.18),(.78,.24),(.56,.46)]]
    for i,(px,py) in enumerate(desired):
        candidates=[]
        for oy in range(-800,801,80):
            for ox in range(-800,801,80):
                x,y=px+ox,py+oy
                if not (350<x<k.WIDTH*10-350 and 350<y<k.HEIGHT*10-350):continue
                iy,ix=k.cell((x,y))
                if not eligible[iy,ix] or any(math.dist((x,y),a['center'])<650 for a in centers):continue
                candidates.append((math.hypot(ox,oy)+t['slope'][iy,ix]*300,x,y))
        if not candidates:raise ValueError('No sheltered woodland near '+str((px,py)))
        _,x,y=min(candidates)
        centers.append(dict(center=(x,y),radii=(rng.uniform(480,790),rng.uniform(340,590)),
                            rotation=rng.random()*math.tau,strength=.83 if i<6 else 1.08,trees=0))
    grove=np.zeros(t['z'].shape)
    for c in centers:
        px,py=c['center'];a=c['rotation'];rx,ry=c['radii']
        u=(t['x']-px)*math.cos(a)+(t['y']-py)*math.sin(a)
        v=-(t['x']-px)*math.sin(a)+(t['y']-py)*math.cos(a)
        grove=np.maximum(grove,c['strength']*np.exp(-.5*((u/rx)**2+(v/ry)**2)))
    from mapkit.earth import fbm
    grove*=np.clip(.93+.55*fbm(t['x'],t['y'],scale=350,seed=k.SEED+331,octaves=3),.45,1.35)
    t['labels'][(grove>.45)&(t['slope']<.25)&(t['z']>k.WATER+40)&(~t['protected'])]=1
    # Reserve small outpost scenes before woodland fills their surroundings.
    settlements=[]
    for s in sites:
        if s['template']!='Outpost':continue
        px,py=s['position'];placed=0
        for _ in range(200):
            if placed>=2:break
            a=rng.random()*math.tau;r=rng.uniform(300,550);x,y=px+math.cos(a)*r,py+math.sin(a)*r
            if place(rng.choice(['OsgiliathRuin01','OsgiliathRuin02','OsgiliathRuin21b']),x,y,
                     'OldOutpostRuins',gap=130,footprint=60,max_rise=14,solid=75,angle=a,site=True):
                placed+=1
                for _ in range(8):
                    b=rng.random()*math.tau;rr=rng.uniform(105,170)
                    place(rng.choice(['CartWheel','Crate01','Barrel','MoriaRubble01']),x+math.cos(b)*rr,y+math.sin(b)*rr,
                          'OutpostDebris',gap=28,footprint=15,max_rise=6,solid=18,site=True)
        settlements.append(dict(player=s['player'],position=s['position'],ruins=placed))
    deciduous=['Tree01_L','Tree03a_L','Tree03a','Tree03aL_L']
    evergreen=['TreeEvergreen03','TreeEvergreen03b','TreeEvergreen03c']
    tree_count=0
    for density,low,high,target,gap in [('Dense',.60,2,1050,43),('Open',.30,.60,500,72),('Fringe',.10,.30,250,120)]:
        placed=0
        for _ in range(50000):
            if placed>=target:break
            index=rng.randrange(len(centers));c=centers[index]
            px,py=c['center'];rx,ry=c['radii'];a=c['rotation']
            u,v=rng.gauss(0,rx*.9),rng.gauss(0,ry*.9)
            x,y=px+u*math.cos(a)-v*math.sin(a),py+u*math.sin(a)+v*math.cos(a)
            if not (100<x<k.WIDTH*10-100 and 100<y<k.HEIGHT*10-100):continue
            iy,ix=k.cell((x,y));g=grove[iy,ix]
            if not low<=g<high or t['z'][iy,ix]>300 or t['slope'][iy,ix]>.38:continue
            probability=float(np.clip((t['z'][iy,ix]-210)/80,.12,.85))
            conifer=rng.random()<probability
            if place(rng.choice(evergreen if conifer else deciduous),x,y,
                     ('Foothill' if conifer else 'Valley')+'Woodland'+density,gap=gap,footprint=6,max_rise=8,solid=8):
                c['trees']+=1;placed+=1;tree_count+=1
                if rng.random()<.11:
                    b=rng.random()*math.tau;r=rng.uniform(35,68)
                    place(rng.choice(['Fern01','OptBush01','OptBush03']),x+math.cos(b)*r,y+math.sin(b)*r,
                          'ForestUnderstory',gap=22,footprint=6,max_rise=5)
    # Boulder anchors and downhill fragments at the toes of actual rocky terrain.
    rock_groups=[]
    candidates=np.column_stack(np.nonzero((t['slope']>.15)&(t['slope']<.48)&(t['z']>205)&(~routes)&(~t['protected'])))
    candidates=candidates[np.random.default_rng(k.SEED+71).permutation(len(candidates))]
    for iy,ix in candidates:
        if len(rock_groups)>=130:break
        x,y=t['x'][iy,ix],t['y'][iy,ix]
        if any(math.dist((x,y),p)<185 for p in rock_groups):continue
        if place(rng.choice(['DarkRockGrey03','DarkRockGrey04','DarkRockGrey05']),x,y,'BoulderGroups',
                 gap=75,footprint=55,max_rise=27,solid=60,offset=-2):
            rock_groups.append((x,y))
            heading=math.atan2(-dy[iy,ix],-dx[iy,ix])
            for _ in range(rng.randint(3,6)):
                a=heading+rng.uniform(-1.15,1.15);r=rng.uniform(75,190)
                place(rng.choice(['DarkRockGrey02','DarkRockGrey07','DarkRockGrey17','DarkRockGrey18']),
                      x+math.cos(a)*r,y+math.sin(a)*r,'ScreeFragments',gap=30,footprint=14,max_rise=10,offset=-1)
    # Small river stones collect on dry terraces rather than uniform map scatter.
    shore=k.gaussian(t['water'].astype(float),8)
    candidates=np.column_stack(np.nonzero((shore>.008)&(t['z']>k.WATER+20)&(t['slope']<.3)))
    candidates=candidates[np.random.default_rng(k.SEED+217).permutation(len(candidates))]
    for iy,ix in candidates:
        if counts['RiverTerraceStones']>=190:break
        place(rng.choice(['DarkRockGrey02','DarkRockGrey07','DarkRockGrey17','DarkRockGrey18']),
              t['x'][iy,ix],t['y'][iy,ix],'RiverTerraceStones',gap=65,footprint=12,max_rise=9,offset=-1)
    for _ in range(25000):
        if counts['MeadowDetail']>=300 and counts['WoodlandDeadwood']>=70:break
        x,y=rng.uniform(100,k.WIDTH*10-100),rng.uniform(100,k.HEIGHT*10-100)
        iy,ix=k.cell((x,y));g=grove[iy,ix]
        if .18<g<.70 and counts['WoodlandDeadwood']<70:
            place(rng.choice(['PTStump01','TreeLog','TreeSpruceStump']),x,y,'WoodlandDeadwood',
                  gap=65,footprint=15,max_rise=6,offset=-.5)
        elif counts['MeadowDetail']<300 and g<.3 and t['slope'][iy,ix]<.18:
            place(rng.choice(['OptGrass08','OptGrass09','OptBush01']),x,y,'MeadowDetail',gap=85,footprint=7,max_rise=4)
    if tree_count<1600:raise ValueError('Insufficient varied woodland: '+str(tree_count))
    (k.OUT/'detail-placement.json').write_text(json.dumps(dict(placements=checks),indent=2)+'\n')
    return dict(layers=dict(counts),trees=tree_count,woodland_centers=centers,rock_groups=len(rock_groups),
                outpost_scenes=settlements,protected_routes=route_report,corridor_width_world=360,
                solid_footprints_checked=True,tree_rendering='native W3DTreeDraw / optimized-tree templates')
