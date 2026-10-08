"""Construct a BFME2 CkMp document from typed fields, without a donor map.

GPL-3.0-only. See docs/ashen-march.md for format references and verification.
All spatial data is generated here. No .map file is read by this constructor.
"""

from bfmexbar.paths import ROOT
import struct
import numpy as np
from bfmexbar.formats.map import Map, Chunk, string, tile_offset


def add_chunk(m, name, version, data):
    m.chunks.append(Chunk(m.intern(name), version, data))


def lighting():
    # Nine lights per time of day: terrain, objects, infantry for each direction.
    # Raking sunlight and restrained fill reveal terrain and model volume.
    out = bytearray(struct.pack('<I', 2))
    for _ in range(4):
        for ambient, color, direction in [
            ((.18,.19,.215),(.70,.65,.56),(.64,.54,-.55)),
            ((0,0,0),(.045,.06,.085),(-.65,-.3,-.70)),
            ((0,0,0),(.015,.02,.025),(.2,-.9,-.38))]:
            for target in range(3):
                gain = 1.10 if target else 1.0
                out += struct.pack('<9f',*ambient,*(v*gain for v in color),*direction)
    # BFME2 v8 legacy shadow/fog defaults, encoded explicitly (no opaque donor).
    out += struct.pack('<II9fI3f',0x80000000,0,*([.15686275]*3),*([.4980392]*6),0xFFA0A0A0,1,1,1)
    assert len(out)==1360
    return bytes(out)


def set_heights(m, values):
    t=m.heightmap(); h,w=values.shape
    assert (h,w)==(t['height'],t['width'])
    if not np.isfinite(values).all() or values.min()<0 or values.max()>2559:
        raise ValueError('Height outside native unsigned fixed-point range')
    m.chunk('HeightMapData').data=struct.pack('<7I',w,h,t['border'],1,w-2*t['border'],h-2*t['border'],w*h)+np.rint(values/.0390625).astype('<u2').tobytes()


def set_materials(m, palette, labels, blocked=None, blend_edges=True):
    h,w=labels.shape; yy,xx=np.indices((h,w)); n=w*h
    phase=tile_offset(xx,yy,4)
    tiles=(labels*64+phase).astype('<u2')
    blends=np.zeros((h,w),dtype='<u4'); records=[]; lookup={}
    # Native directional transitions around material regions. Tile phases match
    # primary terrain and blend descriptors are interned rather than per-cell.
    if blend_edges:
        for dy,dx,direction,flags in [(0,1,b'\1\0\0\0',0),(0,-1,b'\1\0\0\0',1),
                                      (1,0,b'\0\1\0\0',0),(-1,0,b'\0\1\0\0',1)]:
            other=np.roll(labels,(-dy,-dx),(0,1))
            mask=(other>labels)&(blends==0)
            mask[[0,-1],:]=False; mask[:,[0,-1]]=False
            for y,x in zip(*np.nonzero(mask)):
                key=(int(other[y,x]*64+phase[y,x]),direction,flags)
                if key not in lookup:
                    records.append(struct.pack('<I4sBBII',*key,0,0xffffffff,0x7ada0000))
                    lookup[key]=len(records)
                blends[y,x]=lookup[key]
    zero=np.zeros((h,w),dtype='u1'); blocked=zero if blocked is None else blocked.astype('u1')
    out=bytearray(struct.pack('<I',n))+tiles.tobytes()+blends.tobytes()+bytes(n*8)
    for a in (blocked,zero,zero,zero,zero):out+=np.packbits(a,axis=1,bitorder='little').tobytes()
    out+=bytes(n)+np.packbits(np.ones((h,w),dtype='u1'),axis=1,bitorder='little').tobytes()
    out+=struct.pack('<4I',len(palette)*16,len(records)+1,1,len(palette))
    for i,name in enumerate(palette):out+=struct.pack('<4I',i*16,16,4,0)+string(name)
    out+=bytes(8)+b''.join(records)
    m.chunk('BlendTileData').data=bytes(out)


def add_object(m, template, x, y, angle=0, layer='', extra=(), z=0):
    index=getattr(m,'_object_count',0)+1; m._object_count=index
    fields=[('objectInitialHealth',1,100),('objectEnabled',0,1),('objectIndestructible',0,0),
            ('objectUnsellable',0,0),('objectPowered',0,1),('objectRecruitableAI',0,1),
            ('objectTargetable',0,0),('objectBasePriority',1,40),('objectBasePhase',1,1),
            ('originalOwner',3,'PlyrCivilian/teamPlyrCivilian'),('uniqueID',3,f'Ashen_{index:05d}'),
            ('objectLayer',3,layer)]
    overrides={f[0] for f in extra}; fields=[f for f in fields if f[0] not in overrides]+list(extra)
    payload=struct.pack('<4fI',x,y,z,angle,0)+string(template)+m.encode_properties(fields)
    m.chunk('ObjectsList').data+=Chunk(m.intern('Object'),3,payload).encode()


def starts(m, points):
    for i,(x,y) in enumerate(points,1):
        name=f'Player_{i}_Start'
        add_object(m,'*Waypoints/Waypoint',x,y,layer='Starts',extra=[
            ('originalOwner',3,'/team'),('uniqueID',3,name),('waypointID',1,i),
            ('waypointName',3,name),('waypointTypeOption',3,'')])


def create(width=840,height=950,border=30,title='The Ashen March',elevation=100,player_count=2):
    if not isinstance(player_count,int) or not 2<=player_count<=8:
        raise ValueError('A skirmish map needs 2..8 player sides')
    if min(width,height)<64 or max(width+2*border,height+2*border)>2048:
        raise ValueError('Supported experimental sample dimensions: 64..2048')
    m=object.__new__(Map);m.names={};m.chunks=[];m._object_count=0
    w,h=width+2*border,height+2*border
    add_chunk(m,'HeightMapData',5,struct.pack('<7I',w,h,border,1,width,height,w*h)+np.full((h,w),round(elevation/.0390625),dtype='<u2').tobytes())
    add_chunk(m,'BlendTileData',18,b'');set_materials(m,['DirtMordor04'],np.zeros((h,w),dtype='u2'))
    fields=[('cameraMaxHeight',2,20000.),('cameraPitchAngle',2,37.5),('cameraYawAngle',2,0.),
            ('cameraScrollSpeedScalar',2,1.),('isLivingWorldScriptHolder',0,0),('weather',1,0),
            ('compression',1,0),('mapName',3,title),('mapDescription',3,'A ruined frontier beneath the shadow of Mordor.'),
            ('cameraGroundMinHeight',2,0.),('cameraGroundMaxHeight',2,1400.),('isScenarioMultiplayer',0,0),
            ('cameraMapHeightSmoothnessScalar',2,.75)]
    add_chunk(m,'WorldInfo',1,m.encode_properties(fields))
    mp=Chunk(m.intern('MPPositionInfo'),1,struct.pack('<3B2I',1,1,1,0xffffffff,0)).encode()
    add_chunk(m,'MPPositionList',0,mp*8)
    players=[('',''),('PlyrNeutral','Neutral'),('PlyrCivilian','Civilian'),('PlyrCreeps','Civilian')]
    players += [('Skirmish'+s,'Tutorial' if s=='Men' else s) for s in ['Men','Elves','Dwarves','Isengard','Mordor','Wild']]
    players += [(f'Player_{i}','Civilian') for i in range(1,player_count+1)]
    payload=bytearray(struct.pack('<BI',1,len(players)))
    for name,faction in players:
        payload+=m.encode_properties([('playerName',3,name),('playerIsHuman',0,0),
            ('playerDisplayName',4,name or 'Neutral'),('playerFaction',3,'Faction'+faction if faction else ''),
            ('playerAllies',3,''),('playerEnemies',3,'')])+bytes(4)
    add_chunk(m,'SidesList',6,bytes(payload))
    add_chunk(m,'LibraryMapLists',1,Chunk(m.intern('LibraryMaps'),1,bytes(4)).encode()*len(players))
    teams=struct.pack('<I',len(players))+b''.join(m.encode_properties([
        ('teamName',3,'team'+name),('teamOwner',3,name),('teamIsSingleton',0,1)]) for name,_ in players)
    add_chunk(m,'Teams',1,teams)
    add_chunk(m,'PlayerScriptsList',1,Chunk(m.intern('ScriptList'),1,b'').encode()*len(players))
    add_chunk(m,'BuildLists',1,bytes(4)); add_chunk(m,'ObjectsList',3,b'')
    for name,v in [('TriggerAreas',1),('StandingWaterAreas',2),('RiverAreas',2),('StandingWaveAreas',2)]:
        add_chunk(m,name,v,bytes(4))
    add_chunk(m,'GlobalLighting',8,lighting())
    add_chunk(m,'PostEffectsChunk',1,b'\0')
    add_chunk(m,'EnvironmentData',3,struct.pack('<ffB',3.,1.,0)+string('TSNoiseUrb.tga')+string('TSCloudMed.tga'))
    add_chunk(m,'NamedCameras',2,bytes(4));add_chunk(m,'CameraAnimationList',3,bytes(4));add_chunk(m,'WaypointsList',1,bytes(4))
    return m
