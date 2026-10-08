"""Paint The Ashen March in reproducible passes, starting with a new document.

Run python -m tools.worldbuilder.ashen --phase terrain|materials|detail|polish.
There is no source-map parameter and no donor landscape is loaded.
"""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import random
import re

import numpy as np
from PIL import Image, ImageDraw

from .blank import create, starts, set_heights, set_materials, add_object
from .format import Map, sha
from .ithilien import cache_entry

ROOT=Path(__file__).resolve().parents[2]
NAME='map mp bfmexbar ashen march'
OUT=ROOT/'artifacts/ashen-march'
CHECK=ROOT/'runtime/worldbuilder/ashen-march/checkpoints'
STARTS=[(1650,1700),(6750,7800)]
ROUTES=[[(1650,1700),(2800,2800),(3550,4050),(4450,5300),(5400,6650),(6750,7800)],
        [(1650,1700),(1950,3400),(1950,5150),(3100,6800),(4800,7800),(6750,7800)],
        [(1650,1700),(3550,2100),(5650,3300),(6600,5050),(6950,6500),(6750,7800)]]
PALETTE=['DirtMordor03','DirtMordor16','DirtMordor17','RockMordor02',
         'CliffMordor01','RockMordor06','DirtMordor09','DirtMordor11','RockMordor07']


def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1)
    return t*t*(3-2*t)


def noise(shape, spacing, seed):
    rng=np.random.default_rng(seed)
    h,w=shape
    im=Image.fromarray(rng.uniform(-1,1,(max(3,h//spacing+2),max(3,w//spacing+2))).astype('float32'))
    return np.asarray(im.resize((w,h),Image.Resampling.BICUBIC)).copy()


def route_field(x,y,points,levels=None):
    # Catmull-Rom interpolation follows the composed control points without
    # mechanical elbows. Elevation targets share the same interpolation.
    values=[(*p,levels[i] if levels is not None else 0) for i,p in enumerate(points)]
    values=np.array([values[0],*values,values[-1]],dtype=float)
    curve=[]
    for i in range(1,len(values)-2):
        a,b,c,d=values[i-1:i+3]
        for t in np.linspace(0,1,5,endpoint=False):
            curve.append(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
    curve.append(values[-1]);points=[v[:2] for v in curve]
    if levels is not None:levels=[v[2] for v in curve]
    dist=np.full(x.shape,np.inf); target=np.zeros(x.shape)
    for i,((ax,ay),(bx,by)) in enumerate(zip(points,points[1:])):
        vx,vy=bx-ax,by-ay;t=np.clip(((x-ax)*vx+(y-ay)*vy)/(vx*vx+vy*vy),0,1)
        d=np.hypot(x-ax-t*vx,y-ay-t*vy)
        mask=d<dist;dist=np.minimum(dist,d)
        if levels is not None:target=np.where(mask,levels[i]*(1-t)+levels[i+1]*t,target)
    return dist,target


def terrain(variant=1):
    yy,xx=np.indices((1010,900));x=(xx-30)*10.;y=(yy-30)*10.
    broad=noise(x.shape,150,33);mid=noise(x.shape,48,34);fine=noise(x.shape,14,35)
    z=105+22*broad+8*mid
    # Long asymmetric spurs, not isolated circular cones. The ends overlap to
    # produce a broken mountain wall; passes are carved in a separate pass.
    ridges=[(400,4800,950,3100,-.17,820),(1350,7300,700,2400,.53,1050),
            (3350,9300,850,2500,1.1,1050),(7700,4400,800,3100,-.16,1050),
            (7100,1650,880,2300,.95,910),(2800,4550,500,1300,.38,490),
            (5500,5350,550,1250,.35,480)]
    if variant==0:ridges=ridges[:5]+[(4200,4850,1350,1800,0,750)]
    if variant==2:ridges=ridges[:5]+[(4200,4700,550,3000,1.05,650)]
    hills=np.zeros_like(z)
    for cx,cy,sx,sy,angle,height in ridges:
        dx=x-cx+55*mid;dy=y-cy+45*broad;c,s=math.cos(angle),math.sin(angle)
        u=(dx*c+dy*s)/sx;v=(-dx*s+dy*c)/sy
        mass=height*np.exp(-1.5*(u*u+v*v))
        hills=np.maximum(hills,mass)
    z+=hills*(1+.10*mid+.045*fine)
    # Eroded grooves grow on the mountains but disappear across army ground.
    z-=np.maximum(0,mid+.20*fine)*70*smooth(130,550,hills)
    route_levels=[[105,118,140,160,155,130],[105,175,235,260,190,130],[105,110,90,112,130,130]]
    dists=[]
    for i,(route,levels) in enumerate(zip(ROUTES,route_levels)):
        d,target=route_field(x,y,route,levels);dists.append(d)
        width=300 if i==0 else 240
        weight=1-smooth(width,width+620,d)
        z=z*(1-weight)+(target+3*mid+fine)*weight
    # The watch stands on a shoulder above the central field, with a wide ramp.
    cx,cy=3050,5520; d=np.hypot((x-cx)/1.05,y-cy)
    z+=(345-z)*(1-smooth(245,720,d))
    ramp,rz=route_field(x,y,[(3050,5520),(3500,5280),(3900,4780)],[345,260,148])
    weight=(1-smooth(95,300,ramp));z=z*(1-weight)+rz*weight
    # Broad softly feathered construction grounds. No cliff rings at bases.
    for (cx,cy),level in zip(STARTS,[105,130]):
        d=np.hypot(x-cx,y-cy);weight=1-smooth(650,1550,d)
        z=z*(1-weight)+level*weight
    return x,y,np.maximum(z,45),dists,broad,mid,fine


def preview(z,path,labels=None,annotated=False):
    dy,dx=np.gradient(z,10)
    norm=np.sqrt(dx*dx+dy*dy+1)
    shade=np.clip((-.45*dx-.55*dy+.70)/norm,.10,1.1)
    colors=np.array([[91,91,84],[68,65,60],[52,49,47],[89,92,93],[113,116,121],
                     [69,76,80],[101,92,77],[64,70,55],[114,106,92]])
    rgb=np.full((*z.shape,3),110.) if labels is None else colors[labels].astype(float)
    rgb=np.clip(rgb*(.40+.82*shade[...,None]),0,255).astype('u1')
    im=Image.fromarray(rgb).transpose(Image.Transpose.FLIP_TOP_BOTTOM).resize((900,1010))
    if annotated:
        d=ImageDraw.Draw(im)
        def point(p):return ((p[0]/10+30),1010-(p[1]/10+30))
        for route,c in zip(ROUTES,['#e0c294','#8dabb2','#a18caa']):d.line([point(p) for p in route],fill=c,width=4)
        for i,p in enumerate(STARTS,1):
            px,py=point(p);d.ellipse((px-12,py-12,px+12,py+12),fill='#dbc395');d.text((px+18,py-8),f'Start {i}',fill='white')
        for name,p in [('THE FALLEN WATCH',(3050,5520)),('ASH FIELD',(4100,4700)),('DEADWOOD',(5980,4250))]:
            d.text(point(p),name,fill='#f2e9ce',stroke_width=2,stroke_fill='#202124')
    path.parent.mkdir(parents=True,exist_ok=True);im.save(path)


def checkpoint(m,name,notes):
    data=m.encode();check=Map(data);check.report()
    CHECK.mkdir(parents=True,exist_ok=True)
    destination=CHECK/(name+'.map')
    if destination.exists():
        previous=destination.read_bytes()
        if previous!=data:
            history=CHECK/'history';history.mkdir(exist_ok=True)
            (history/(name+'-'+sha(previous)[:16]+'.map')).write_bytes(previous)
    destination.write_bytes(data)
    item=dict(phase=name,sha256=sha(data),bytes=len(data),objects=len(check.objects()),
              height_range=check.report()['height_range'],notes=notes)
    (CHECK/(name+'.json')).write_text(json.dumps(item,indent=2)+'\n')
    print(json.dumps(item),flush=True)
    return item


def materials(x,y,z,dists,broad,mid,fine):
    dy,dx=np.gradient(z,10);slope=np.hypot(dx,dy)
    labels=np.zeros(z.shape,dtype='u2')
    labels[broad+.38*mid>.22]=1
    labels[(mid>.35)&(z<220)]=2
    labels[(z>240)&(mid>-.45)]=3
    labels[slope>.55]=4
    labels[(slope>.32)&(mid>.22)]=5
    # Wide material masses, then road wear and pockets of exhausted scrub.
    road=np.minimum.reduce(dists)
    labels[(road<48+18*mid+12*fine)&(slope<.32)]=6
    grove=np.exp(-((x-5950)/950)**2-((y-4300)/1200)**2)
    labels[(grove+.25*mid>.56)&(road>280)&(slope<.32)]=7
    watch=np.hypot(x-3050,y-5520)
    labels[(watch<240+30*mid)&(slope<.2)]=8
    return labels,slope,road,grove


def decorate(m,x,y,z,slope,road,grove,polish=False):
    rng=random.Random(20261008);placed=Counter();occupied={}
    ini='\n'.join(p.read_text(encoding='cp1252') for p in (ROOT/'runtime/bfme-host/mod/data/ini/object').rglob('*.ini'))
    valid=set(re.findall(r'^\s*(?:Object|ChildObject|ObjectReskin)\s+(\w+)',ini,re.M))
    def put(template,px,py,angle=None,layer='Scenery',gap=35,protect=True):
        if template not in valid:raise ValueError('Missing native object '+template)
        ix,iy=round(px/10)+30,round(py/10)+30
        if not 15<px<8385 or not 15<py<9485:return False
        if protect and (road[iy,ix]<210 or any(math.hypot(px-a,py-b)<790 for a,b in STARTS)):
            return False
        cell=(int(px//100),int(py//100));n=math.ceil(gap/100)
        for cy in range(cell[1]-n,cell[1]+n+1):
            for cx in range(cell[0]-n,cell[0]+n+1):
                if any(math.hypot(px-a,py-b)<max(gap,g) for a,b,g in occupied.get((cx,cy),[])):return False
        add_object(m,template,px,py,rng.random()*math.tau if angle is None else angle,layer=layer)
        occupied.setdefault(cell,[]).append((px,py,gap));placed[template]+=1;return True
    # Reserve the defining landmark before optional debris/wall placement.
    if not put('TowerHills_TowerA',3050,5600,0,'FallenWatch',gap=80,protect=False):
        raise ValueError('The defining watch tower must be placed')
    # Hand-composed watch enclosure: broken crescent, open southern entrance,
    # statues at its threshold, collapsed habitation behind the curtain wall.
    for deg in [15,45,75,105,135,165,195,225,315,345]:
        a=math.radians(deg)
        put('GBWTopWall'+str(1+(deg//30)%4),3050+195*math.cos(a),5520+195*math.sin(a),a+math.pi/2,'FallenWatch',gap=60,protect=False)
    for tpl,px,py,a in [('OsgiliathRuin01',2945,5480,0),('OsgiliathRuin02',3160,5480,.6),
                         ('GBWTopStatue1',2990,5345,0),('GBWTopStatue2',3110,5345,0),
                         ('FireBonfire',3050,5480,0)]:
        put(tpl,px,py,a,'FallenWatch',gap=35,protect=False)
    # Distinct abandoned roadside settlements, aligned to their old streets.
    for cx,cy,angle in [(2550,3190,.6),(5020,6590,.7),(6400,5980,-.2)]:
        for i,(ox,oy) in enumerate([(-140,150),(110,180),(-190,-50),(190,-120)]):
            px=cx+ox*math.cos(angle)-oy*math.sin(angle);py=cy+ox*math.sin(angle)+oy*math.cos(angle)
            put(['OsgiliathRuin06','OsgiliathRuin08','OsgiliathRuin24','OsgiliathRuin22'][i],px,py,angle,'AbandonedHamlets',gap=100)
        put('FireCampfire',cx+45,cy+30,0,'AbandonedHamlets',gap=35)
    # Dead woodland follows a sheltered basin; ridges receive scree instead.
    for _ in range(15000):
        px=rng.uniform(80,8320);py=rng.uniform(80,9420);ix,iy=round(px/10)+30,round(py/10)+30
        s=slope[iy,ix];height=z[iy,ix];g=grove[iy,ix]
        if s>.75:continue
        chance=rng.random()
        if g>.28 and s<.30 and chance<g*.85:
            put(rng.choice(['TreeDead01','TreeDead02','TreeDead03','TreeDead02']),px,py,layer='Deadwood',gap=55)
        elif height>260 and chance<.28:
            put(rng.choice(['MordorRockClump03','MordorRockClump04','MordorRockClump07','MordorRockClump09']),px,py,layer='Scree',gap=65)
        elif height<250 and chance<.018:
            put(rng.choice(['TreeDead01','TreeDead02']),px,py,layer='LoneTrees',gap=140)
    if polish:
        for _ in range(1400):
            px=rng.gauss(5930,550);py=rng.gauss(4200,720)
            if not 100<px<8300 or not 100<py<9400:continue
            ix,iy=round(px/10)+30,round(py/10)+30
            if slope[iy,ix]<.32:
                put(rng.choice(['TreeDead01','TreeDead02','TreeDead03']),px,py,layer='Deadwood',gap=50)
        # Small vignettes rather than uniform scatter: scree at outcrop toes,
        # rubble by buildings and thin grass where shelter and moisture remain.
        for o in list(m.objects()):
            if o['template'].startswith(('Osgiliath','GBWTopR')):
                for _ in range(7):
                    a=rng.random()*math.tau;r=rng.uniform(50,150)
                    put(rng.choice(['MoriaRubble01','MoriaRubble02','DarkRockGrey07']),o['x']+r*math.cos(a),o['y']+r*math.sin(a),layer='RuinDebris',gap=22)
        for _ in range(11000):
            px=rng.uniform(120,8280);py=rng.uniform(120,9380);ix,iy=round(px/10)+30,round(py/10)+30
            if slope[iy,ix]>.35:continue
            if grove[iy,ix]>.30 or (.13<slope[iy,ix]<.28 and z[iy,ix]>180):
                put(rng.choice(['OptGrass08','OptGrass09','DarkRockGrey07']),px,py,layer='GroundDetails',gap=28)
    return dict(placed)


def route_audit(z,blocked):
    # This is an authoring-grid clearance check, never a claim about native hordes.
    result=[]
    for i,route in enumerate(ROUTES):
        samples=[]
        for (ax,ay),(bx,by) in zip(route,route[1:]):
            n=int(math.hypot(bx-ax,by-ay)//10)+1
            for t in np.linspace(0,1,n):samples.append((round((ay+(by-ay)*t)/10)+30,round((ax+(bx-ax)*t)/10)+30))
        heights=np.array([z[q] for q in samples]);hits=sum(bool(blocked[q]) for q in samples)
        result.append(dict(route=i+1,length=round(sum(math.dist(a,b) for a,b in zip(route,route[1:]))),blocked_samples=hits,
                           elevation_range=[float(heights.min()),float(heights.max())]))
    if any(r['blocked_samples'] for r in result):raise ValueError('Authored route crosses blocked terrain')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--phase',choices=['terrain','materials','detail','polish'],default='polish');args=p.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    stages=[];m=create();stages.append(checkpoint(m,'00-empty','Uniform elevation 100; no objects, roads, water or scripts.'))
    starts(m,STARTS);stages.append(checkpoint(m,'01-functional','Two authored starts only. Native empty-document loading verified separately.'))
    for i in range(3):
        _,_,study,*_=terrain(i);preview(study,OUT/f'02-composition-{i+1}.png',annotated=True)
    x,y,z,dists,broad,mid,fine=terrain(1)
    set_heights(m,z);stages.append(checkpoint(m,'03-landforms','Selected split-spur composition; high western road, lower eastern flank, central open approach.'))
    labels,slope,road,grove=materials(x,y,z,dists,broad,mid,fine)
    blocked=(slope>.72)|((z>620)&(slope>.25))
    routes=route_audit(z,blocked)
    set_materials(m,[PALETTE[0]],np.zeros(labels.shape,dtype='u2'),blocked)
    stages.append(checkpoint(m,'04-routes','Three continuous terrain routes; protected starts and a graded watch ramp.'))
    if args.phase!='terrain':
        set_materials(m,PALETTE,labels,blocked)
        stages.append(checkpoint(m,'05-materials','Nine native terrain materials, slope-driven scree, shelter-driven ground cover and directional blends.'))
    if args.phase in ('detail','polish'):
        decorate(m,x,y,z,slope,road,grove,polish=args.phase=='polish')
        stages.append(checkpoint(m,'07-polish' if args.phase=='polish' else '06-local-scenes','Fallen Watch, three ruined hamlets, deadwood basin, scree fields; main routes and base space protected.'))
    preview(z,OUT/'terrain-plan.png',labels,annotated=True)
    preview(z,OUT/'terrain-relief.png',labels)
    path=ROOT/'runtime/bfme-host/mod/maps'/NAME/(NAME+'.map');path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(m.encode())
    (path.parent/'map.ini').write_text('; The Ashen March: retain strategic-distance visibility.\nWeather\n  HardwareFogEnable = No\nEnd\nAIData\n  LowLodTreeName = TreeLowLODMordor\nEnd\n',encoding='ascii')
    # Original minimap artwork comes from the authored elevation/material plan.
    # The full native portrait is produced separately; this is cartographic art.
    radar=Image.open(OUT/'terrain-relief.png').crop((30,30,870,980)).resize((256,256),Image.Resampling.LANCZOS)
    for suffix in ('_art.tga','_pic.tga'):radar.save(path.parent/(NAME+suffix))
    cache_entry(path,m,NAME,'The Ashen March','A fallen Gondorian watch, ash fields and broken mountain roads on the edge of Mordor.')
    report=Map(path.read_bytes()).report()
    report.update(phase=args.phase,source_map=None,seed=20261008,checkpoints=stages,route_grid_audit=routes,
                  worldbuilder_verified=False,native_horde_paths_verified=False)
    (OUT/'build.json').write_text(json.dumps(report,indent=2)+'\n')
    (OUT/'tour.json').write_text(json.dumps(dict(output='artifacts/ashen-march/'+args.phase,
        map_sha256=sha(path.read_bytes()),photo_output='artifacts/ashen-march/photo',photo_name='The-Ashen-March',photo_focus=[4200,4750,120],shots=[
        ['fallen-watch',3050,5500,950],['deadwood-basin',5780,3940,1200],
        ['broken-ridge',5950,5400,1900],['strategic-overview',4200,4750,15500]]),indent=2))
    print(json.dumps(dict(map=str(path),objects=report['objects'],height_range=report['height_range'],routes=routes)))


if __name__=='__main__':main()
