"""The Greywater Marches: six-player native terrain from the supplied references."""
from collections import Counter, deque
import json
import math
from pathlib import Path
import random
import re
import struct
import zipfile

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from common.paths import ROOT
from formats.map import Map, Reader, sha, string
from mapkit.blank import create, starts, set_heights, set_materials, add_object
from mapkit.cache import cache_entry
from mapkit.analyze import analyze
from mapkit.earth import fbm

PROJECT = ROOT / 'examples/maps/greywater_marches'
OUT = ROOT / 'local/artifacts/greywater-marches'
MOD = ROOT / 'local/runtime/bfme-host/mod'
NAME = 'map mp bfmexbar greywater marches'
TITLE = 'The Greywater Marches'
SCALE = 1.5
WIDTH, HEIGHT, BORDER = 1350, 900, 30
WATER, GROUND, SEED = 135., 195., 101026
STARTS = [(1670,7250),(5870,7690),(11270,7090),(10820,2070),(5500,1090),(1600,2150)]
PALETTE = ['GrassMediumType40', 'GrassMediumType44b', 'IthilienDirt07',
           'SandType3wet', 'RockRohan04', 'CliffMediumType16b', 'CliffMediumType15', 'RocksType3']
COLORS = [(123,130,74), (95,110,60), (148,130,92), (154,145,112),
          (113,116,110), (104,107,104), (157,160,151), (129,126,109)]


def smooth(a, b, v):
    t = np.clip((v-a)/(b-a), 0, 1)
    return t*t*(3-2*t)


def blur(a, radius):
    return np.array(Image.fromarray(np.uint8(np.clip(a, 0, 255))).filter(ImageFilter.GaussianBlur(radius)), float)


def gaussian(a, sigma):
    """Float-preserving separable smoothing, with closed map boundaries."""
    radius=math.ceil(sigma*3)
    offsets=np.arange(-radius,radius+1)
    weights=np.exp(-.5*(offsets/sigma)**2);weights/=weights.sum()
    result=a.astype(float)
    for axis in (0,1):
        padding=[(0,0),(0,0)];padding[axis]=(radius,radius)
        padded=np.pad(result,padding,mode='edge');filtered=np.zeros_like(result)
        for i,weight in enumerate(weights):
            selection=[slice(None),slice(None)];selection[axis]=slice(i,i+result.shape[axis])
            filtered+=padded[tuple(selection)]*weight
        result=filtered
    return result


def world(p):
    return p[0]*10, (HEIGHT-1-p[1])*10


def cell(p):
    return round(p[1]/10)+BORDER, round(p[0]/10)+BORDER


def components(mask):
    labels = np.zeros(mask.shape, dtype=np.int32)
    sizes = []
    h, w = mask.shape
    for y, x in zip(*np.nonzero(mask)):
        if labels[y, x]:
            continue
        label = len(sizes)+1
        labels[y, x] = label
        queue = deque([(y, x)])
        size = 0
        while queue:
            a, b = queue.popleft(); size += 1
            for c, d in ((a-1,b), (a+1,b), (a,b-1), (a,b+1)):
                if 0 <= c < h and 0 <= d < w and mask[c,d] and not labels[c,d]:
                    labels[c,d] = label; queue.append((c,d))
        sizes.append(size)
    return labels, sizes


def choose_starts(z, water):
    # Clockwise open layout. Search low, dry ground within each reference region.
    anchors = [(round(x*SCALE),round(y*SCALE)) for x,y in
               [(110,115), (390,88), (750,125), (720,460), (365,525), (125,455)]]
    search=round(65*SCALE)
    result = []
    for ax, ay in anchors:
        choices = []
        for py in range(max(65,ay-search), min(HEIGHT-65,ay+search+1), 5):
            for px in range(max(65,ax-search), min(WIDTH-65,ax+search+1), 5):
                region = z[py-55:py+56,px-55:px+56]
                if water[py-55:py+56,px-55:px+56].any():
                    continue
                score = math.hypot(px-ax,py-ay) + .5*np.ptp(region) + .1*region.mean()
                choices.append((score,px,py))
        if not choices:
            raise ValueError(f'No dry construction area near {(ax,ay)}')
        _,px,py = min(choices)
        result.append(world((px,py)))
    return result


def crossing_plan(water, raw):
    # Search natural narrow reaches near authored strategic crossings.
    anchors = [('northwest',210,80,0), ('upper-west',345,185,90),
               ('upper-east',450,195,90), ('northeast',540,120,0),
               ('western-bend',205,275,135), ('lower-west',375,355,90),
               ('lower-east',610,510,135), ('eastern-bend',790,345,90)]
    result = []
    for name, ax, ay, direction in anchors:
        ax,ay=round(ax*SCALE),round(ay*SCALE)
        search=round(40*SCALE)
        candidates = []
        for py in range(max(60,ay-search), min(HEIGHT-60,ay+search+1), 3):
            for px in range(max(60,ax-search), min(WIDTH-60,ax+search+1), 3):
                if not water[py,px]:
                    continue
                for angle in range(direction-30, direction+31, 15):
                    a = math.radians(angle); vx,vy = math.cos(a),math.sin(a)
                    ends=[]
                    for sign in (-1,1):
                        for d in range(1,36):
                            y=round(py+sign*vy*d); x=round(px+sign*vx*d)
                            if not water[y,x]:
                                ends.append((d,x,y)); break
                    if len(ends)!=2 or not 8 <= sum(e[0] for e in ends) <= 44:
                        continue
                    # Full banks and low foothills on both sides, not little river islets.
                    valid=True
                    for sign in (-1,1):
                        for d in (30,38,46,54):
                            for cross in (-6,0,6):
                                y=round(py+sign*vy*d+vx*cross); x=round(px+sign*vx*d-vy*cross)
                                if not (0<=y<HEIGHT and 0<=x<WIDTH) or water[y,x] or raw[y,x]>225:
                                    valid=False; break
                            if not valid:break
                        if not valid:break
                    if not valid:continue
                    midpoint = .5*(ends[1][0]-ends[0][0])
                    cx,cy = px+vx*midpoint,py+vy*midpoint
                    score=math.hypot(cx-ax,cy-ay)+abs(sum(e[0] for e in ends)-32)*.7
                    candidates.append((score,cx,cy,vx,vy,sum(e[0] for e in ends)))
        if not candidates:
            raise ValueError('No natural bridge reach near '+name)
        _,px,py,vx,vy,span=min(candidates)
        center=world((px,py)); axis=(vx,-vy)
        result.append(dict(name=name,center=center,axis=axis,water_span=span*10,
                           ends=[(center[0]+axis[0]*d,center[1]+axis[1]*d) for d in (-340,340)]))
    return result


def terrain():
    reference=Image.open(PROJECT/'references/heightmap.png').convert('L').resize((WIDTH,HEIGHT),Image.Resampling.LANCZOS)
    raw=np.array(reference,float)
    water=raw<18
    # Reference luminance is elevation, not an exposure mask. A linear transfer
    # retains the mid-grey hills instead of isolating white pixels into needles.
    low=blur(raw,.65)
    elevation=70+1.15*low
    elevation[water]=20
    # Shores ease from river bed into the grassland without a straight bank wall.
    land=blur((~water)*255,1.3)/255
    elevation=np.where(water,20,20+(elevation-20)*smooth(.38,.95,land))
    # Remove short ground ripples selectively. Weighted land-only filtering
    # prevents river beds leaking into the banks; high ridges stay untouched.
    original=elevation.copy()
    valid=(~water).astype(float)
    softened=gaussian(elevation*valid,3.5)/np.maximum(gaussian(valid,3.5),1e-9)
    broad=gaussian(elevation,6)
    by,bx=np.gradient(broad,10);broad_slope=np.hypot(bx,by)
    weight=.88*(1-smooth(.28,.65,broad_slope))*(1-smooth(255,310,elevation))
    weight*=smooth(WATER+22,WATER+52,elevation)*(~water)
    elevation=elevation+np.clip((softened-elevation)*weight,-16,16)
    measured=(weight>.6)&(original>WATER+50)
    before=(original-gaussian(original,3.5))[measured]
    after=(elevation-gaussian(elevation,3.5))[measured]
    smoothing=dict(radius_world_units=35,strength=.88,measured_cells=int(measured.sum()),
        ripple_rms_before=float(np.sqrt(np.mean(before**2))),
        ripple_rms_after=float(np.sqrt(np.mean(after**2))),
        maximum_change=float(np.max(np.abs(elevation-original))),
        preserved='river beds and shores, high ridges; existing six start positions')
    start_positions=STARTS
    bridges=crossing_plan(water,low)
    z=np.pad(np.flipud(elevation),BORDER,mode='edge')
    wet=np.pad(np.flipud(water),BORDER,mode='edge')
    yy,xx=np.indices(z.shape); x=(xx-BORDER)*10.; y=(yy-BORDER)*10.
    protected=np.zeros(z.shape,bool); decks=np.zeros(z.shape,bool)
    for px,py in start_positions:
        dist=np.hypot(x-px,y-py)
        target=float(np.median(z[dist<330]))
        blend=(1-smooth(360,500,dist))*(~wet)
        z=z*(1-blend)+target*blend
        protected|=dist<760
    for b in bridges:
        px,py=b['center'];vx,vy=b['axis']
        along=(x-px)*vx+(y-py)*vy; across=-(x-px)*vy+(y-py)*vx
        # Native ramp ends sit on graded stone abutments. River remains below the deck.
        bank=(1-smooth(390,660,np.abs(along)))*(1-smooth(85,180,np.abs(across)))
        bank*=smooth(205,255,np.abs(along))
        z=z*(1-bank)+GROUND*bank
        bed=(1-smooth(220,250,np.abs(along)))*(1-smooth(75,115,np.abs(across)))
        z=z*(1-bed)+20*bed
        decks|=(np.abs(along)<=285)&(np.abs(across)<=60)
        protected|=(np.abs(along)<760)&(np.abs(across)<210)
    # A nearby approach may feather into a base's outer edge. Restore the dry
    # construction circle last, keeping its bank at the same elevation.
    for px,py in start_positions:
        dist=np.hypot(x-px,y-py)
        target=float(np.median(z[dist<300]))
        blend=(1-smooth(360,500,dist))*(~wet)
        z=z*(1-blend)+target*blend
    dy,dx=np.gradient(z,10); slope=np.hypot(dx,dy)
    blocked=(z<WATER+8)|(slope>.82)
    proxy=(~blocked)|decks
    # All six bases must share a sizeable land/deck component, no diagonal corner joins.
    connectivity,sizes=components(proxy)
    groups=[int(connectivity[cell(p)]) for p in start_positions]
    if not groups[0] or len(set(groups))!=1:
        raise ValueError('Disconnected six-player terrain: '+str(groups))
    n=fbm(x,y,scale=700,seed=SEED,octaves=3)
    labels=np.zeros(z.shape,dtype='u2')
    labels[n<-.11]=1
    labels[(n>.17)&(z<310)]=2
    labels[z<WATER+34]=3
    scree=(slope>.26)|(z>275)
    labels[scree]=7
    labels[(slope>.40)|(z>300)]=4
    labels[(slope>.65)&(z>240)]=5
    labels[z>330]=6
    labels[z<WATER]=3
    return dict(z=z,water=wet,slope=slope,blocked=blocked,labels=labels,x=x,y=y,
                protected=protected,starts=start_positions,bridges=bridges,decks=decks,
                audit=dict(start_components=groups,connected_cells=sizes[groups[0]-1],
                           method='four-neighbour terrain proxy with native bridge footprints',
                           native_paths_verified=False),smoothing=smoothing)


def decorate(m,t):
    rng=random.Random(SEED); placed=Counter(); occupied=[];buckets={};largest_gap=0
    valid=set(re.findall(r'(?m)^\s*(?:Object|ChildObject|ObjectReskin)\s+(\w+)',
                        '\n'.join(p.read_text(encoding='cp1252') for p in (MOD/'data/ini/object').rglob('*.ini'))))
    def put(template,px,py,layer,gap=55,extra=(),z=0,angle=None):
        nonlocal largest_gap
        if template not in valid:raise ValueError('Unknown installed template: '+template)
        cx,cy=int(px//100),int(py//100);reach=math.ceil(max(gap,largest_gap)/100)
        if any(math.hypot(px-a,py-b)<max(gap,g) for yy in range(cy-reach,cy+reach+1)
               for xx in range(cx-reach,cx+reach+1) for a,b,g in buckets.get((xx,yy),[])):return False
        add_object(m,template,px,py,rng.random()*math.tau if angle is None else angle,
                   layer=layer,extra=extra,z=z)
        occupied.append((px,py,gap));buckets.setdefault((cx,cy),[]).append((px,py,gap))
        largest_gap=max(gap,largest_gap);placed[template]+=1; return True
    for b in t['bridges']:
        px,py=b['center'];vx,vy=b['axis']
        iy,ix=cell((px,py))
        put('GondorIthilienBridge2',px,py,'Bridges',z=GROUND-1-t['z'][iy,ix],
            angle=math.atan2(vy,vx)-math.pi/2,
            extra=[('objectName',3,'Greywater_Bridge_'+b['name'])])
    capture=[('originalOwner',3,'PlyrNeutral/teamPlyrNeutral'),('objectTargetable',0,1)]
    creeps=[('originalOwner',3,'PlyrCreeps/teamPlyrCreeps'),('objectTargetable',0,1)]
    sites=[]
    # Equal expansion/creep counts per start. Terrain foundations are graded locally.
    for i,(sx,sy) in enumerate(t['starts']):
        for template,radius,extra in [('Outpost',980,capture),('WargLair',1450,creeps)]:
            choices=[]
            for a in np.linspace(0,math.tau,72,endpoint=False):
                for r in (radius-140,radius,radius+140):
                    px,py=sx+math.cos(a)*r,sy+math.sin(a)*r
                    if not (220<px<WIDTH*10-220 and 220<py<HEIGHT*10-220):continue
                    iy,ix=cell((px,py));patch=t['z'][iy-12:iy+13,ix-12:ix+13]
                    if t['blocked'][iy-12:iy+13,ix-12:ix+13].any() or np.ptp(patch)>55:continue
                    if any(math.hypot(px-x,py-y)<760 for x,y in t['starts']):continue
                    if any(math.hypot(px-x,py-y)<350 for x,y,_ in occupied):continue
                    choices.append((np.ptp(patch)+abs(r-radius)*.1,px,py))
            if not choices:raise ValueError(f'No {template} near player {i+1}')
            _,px,py=min(choices)
            dist=np.hypot(t['x']-px,t['y']-py); blend=1-smooth(105,160,dist)
            target=float(t['z'][cell((px,py))]);t['z']=t['z']*(1-blend)+target*blend
            t['protected']|=dist<300
            put(template,px,py,'NeutralSites',gap=200,extra=extra)
            sites.append(dict(player=i+1,template=template,position=(px,py),distance=math.hypot(px-sx,py-sy)))
    import sys
    from examples.maps.greywater_marches.scenery import populate
    detail=populate(sys.modules[__name__],m,t,put,rng,sites)
    return dict(templates=dict(placed),neutral_sites=sites,total=sum(placed.values()),detail=detail)


def preview(t,m):
    z=t['z'];dy,dx=np.gradient(z,10);norm=np.sqrt(dx*dx+dy*dy+1)
    light=np.clip((-.45*dx-.5*dy+.78)/norm,.08,1.10)
    rgb=np.array(COLORS)[t['labels']].astype(float)*(.43+.72*light[...,None])
    wet=z<WATER;rgb[wet]=(38,85,105)
    im=Image.fromarray(np.uint8(np.clip(rgb,0,255))).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    def pixel(p):return (p[0]/10+BORDER,z.shape[0]-1-(p[1]/10+BORDER))
    draw=ImageDraw.Draw(im)
    for o in m.objects():
        if o['template'].startswith(('Tree','PTree')):
            px,py=pixel((o['x'],o['y']))
            draw.ellipse((px-2,py-2,px+2,py+2),fill=(44,77,40))
    for b in t['bridges']:draw.line([pixel(p) for p in b['ends']],fill=(190,181,153),width=9)
    im.save(OUT/'terrain-overview.png')
    radar=im.crop((BORDER,BORDER,WIDTH+BORDER,HEIGHT+BORDER))
    annotated=im.copy();draw=ImageDraw.Draw(annotated)
    colors=['#e35548','#438fe5','#55bd56','#e3cb51','#b56bea','#42c6c3']
    for i,p in enumerate(t['starts']):
        px,py=pixel(p);draw.ellipse((px-9,py-9,px+9,py+9),fill=colors[i],outline='white',width=2)
        draw.text((px-3,py-5),str(i+1),fill='white')
    draw.rectangle((40,38,407,80),fill='#1d2827')
    draw.text((50,45),'THE GREYWATER MARCHES | 6 PLAYERS',fill='#f0e7cb')
    draw.text((50,61),'TERRAIN PLAN - NOT AN IN-GAME SCREENSHOT',fill='#b4c4bc')
    annotated.save(OUT/'layout.png')
    return radar


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    print('Sculpting the supplied heightmap and grading six construction areas...',flush=True)
    t=terrain()
    m=create(WIDTH,HEIGHT,BORDER,title=TITLE,player_count=6)
    starts(m,t['starts'])
    scenery=decorate(m,t)
    # Recheck the final foundations; grading must not cut any approach off.
    dy,dx=np.gradient(t['z'],10)
    t['blocked']=(t['z']<WATER+8)|(np.hypot(dx,dy)>.82)
    connected,sizes=components(((~t['blocked'])|t['decks'])&(~t['scenery_solids']))
    groups=[int(connected[cell(p)]) for p in t['starts']]
    if not groups[0] or len(set(groups))!=1:raise ValueError('Disconnected final terrain')
    for site in scenery['neutral_sites']:
        if int(connected[cell(site['position'])])!=groups[0]:raise ValueError('Inaccessible neutral site')
    t['audit']['start_components']=groups
    t['audit']['connected_cells']=sizes[groups[0]-1]
    t['audit']['neutral_sites_connected']=True
    t['audit']['construction_areas']=[]
    for p in t['starts']:
        region=np.hypot(t['x']-p[0],t['y']-p[1])<=350
        relief=float(np.ptp(t['z'][region]))
        if relief>.01 or t['blocked'][region].any():raise ValueError('Uneven or blocked construction area')
        t['audit']['construction_areas'].append(dict(center=p,radius=350,relief=relief))
    set_heights(m,t['z']);set_materials(m,PALETTE,t['labels'],t['blocked'])
    from formats.water import standing_water
    m.chunk('StandingWaterAreas').data=standing_water([dict(id=1,name='Greywater rivers',layer='Water',
        uv_speed=.035,additive=0,bump_texture='WaterRippleBump.tga',sky_texture='SkyEnv.tga',
        points=[(-300,-300),(WIDTH*10+300,-300),(WIDTH*10+300,HEIGHT*10+300),(-300,HEIGHT*10+300)],water_height=int(WATER),
        shader='wtr_Riv03.W3D',depth_colors='LUTDepthTint.tga')])
    description='Six open realms across rocky grasslands, mountain passes and branching rivers.'
    fields=m.properties(Reader(m.chunk('WorldInfo').data))
    m.chunk('WorldInfo').data=m.encode_properties([(k,kind,
        description if k=='mapDescription' else 30000. if k=='cameraMaxHeight' else v) for k,kind,v in fields])
    from formats.lighting import decode,encode
    lighting=decode(m.chunk('GlobalLighting').data,8)
    for configuration in lighting['configurations']:
        for light in configuration:
            if light['light_index']==0:
                light['ambient']=(.26,.28,.30)
                light['diffuse']=(.76,.73,.65)
    m.chunk('GlobalLighting').data=encode(lighting)
    m.chunk('EnvironmentData').data=struct.pack('<ffB',3.,1.,1)+string('TSNoise2kNoGreen.tga')+string('TSCloudMed.tga')
    data=m.encode();report=analyze(data)
    if report['unresolved_sections']:raise ValueError(report['unresolved_sections'])
    target=MOD/'maps'/NAME;target.mkdir(parents=True,exist_ok=True)
    path=target/(NAME+'.map');path.write_bytes(data)
    (target/'map.ini').write_text('; The Greywater Marches\nWeather\n  HardwareFogEnable = No\nEnd\n'
        f'WaterTransparency\n  ReflectionPlaneZ = {WATER:g}\n  ReflectionOn = No\nEnd\n',encoding='ascii')
    radar=preview(t,m).resize((256,256),Image.Resampling.LANCZOS)
    for suffix in ('_art.tga','_pic.tga'):radar.save(target/(NAME+suffix))
    cache_entry(path,m,NAME,TITLE,description)
    with zipfile.ZipFile(OUT/'Greywater-Marches.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for p in sorted(target.iterdir()):
            if p.is_file():archive.write(p,Path(NAME)/p.name)
    report.update(title=TITLE,seed=SEED,starts=t['starts'],bridges=t['bridges'],scenery=scenery,
        grid_audit=t['audit'],source_map=None,reference_height_sha256=sha((PROJECT/'references/heightmap.png').read_bytes()),
        reference_landscape_sha256=sha((PROJECT/'references/landscape.png').read_bytes()),
        native_validation_status='pending',worldbuilder_verified=False,smoothing=t['smoothing'])
    # Publish the actual native heights alongside the input so terrain fidelity
    # can be reviewed independently of textures, lighting and perspective.
    native=t['z'][BORDER:BORDER+HEIGHT,BORDER:BORDER+WIDTH]
    normalized=np.uint8(np.clip((np.flipud(native)-70)/1.15,0,255))
    Image.fromarray(normalized).save(OUT/'actual-heightmap.png')
    supplied=Image.open(PROJECT/'references/heightmap.png').convert('L').resize((WIDTH,HEIGHT),Image.Resampling.LANCZOS)
    comparison=Image.new('RGB',(WIDTH*2,HEIGHT+30),'#202623')
    comparison.paste(supplied.convert('RGB'),(0,30))
    comparison.paste(Image.fromarray(normalized).convert('RGB'),(WIDTH,30))
    draw=ImageDraw.Draw(comparison)
    draw.text((15,10),'SUPPLIED HEIGHTMAP',fill='white')
    draw.text((WIDTH+15,10),'ACTUAL MAP HEIGHTS - LOCAL BASE / BRIDGE GRADING',fill='white')
    comparison.save(OUT/'heightmap-comparison.png')
    report['height_conversion']=dict(method='linear: z = 70 + 1.15 * luminance',
        reference_smoothing_pixels=.65,local_edits='selective playable-ground ripple smoothing, river shores, bases, bridge banks and neutral foundations')
    (OUT/'build.json').write_text(json.dumps(report,indent=2)+'\n')
    probes=[]
    for b in t['bridges']:
        p=np.array(b['center']);axis=np.array(b['axis'])
        probes.append(dict(name=b['name'],source=[*(p-axis*360),GROUND],
                           destination=[*(p+axis*360),GROUND],center=[*p,GROUND]))
    (OUT/'tour.json').write_text(json.dumps(dict(output='local/artifacts/greywater-marches/native',
        map_sha256=sha(data),required_players=6,bridge_probes=probes,
        shots=[['woodland-fringe',*scenery['detail']['woodland_centers'][0]['center'],1600],
               ['dense-valley-forest',*scenery['detail']['woodland_centers'][6]['center'],1600],
               ['river-crossings',*t['bridges'][2]['center'],1800],
               ['outpost-and-scree',*sites_position(scenery,5),1700],
               ['strategic-overview',WIDTH*5,HEIGHT*5,14500*SCALE]]),indent=2)+'\n')
    print(json.dumps(dict(map=str(path),sha256=sha(data),objects=report['objects'],
                         height_range=report['height_range'],bridges=len(t['bridges'])),indent=2))


def sites_position(scenery,player):
    return next(s['position'] for s in scenery['neutral_sites'] if s['player']==player and s['template']=='Outpost')


if __name__=='__main__':main()
