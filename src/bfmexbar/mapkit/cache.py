"""Register a verified map document in the isolated native map cache."""
import re
import zlib
from bfmexbar.paths import ROOT

def cache_entry(path, m, name, title, description, root=ROOT):
    cache=root/'runtime/bfme-host/mod/maps/mapcache.ini'
    text=cache.read_text(encoding='cp1252')
    def escaped(raw):
        return ''.join(chr(c) if (48<=c<=57 or 65<=c<=90 or 97<=c<=122) else f'_{c:02X}' for c in raw)
    key=escaped(('maps\\'+name+'\\'+name+'.map').encode('ascii'))
    text=re.sub(r'(?ms)^MapCache '+re.escape(key)+r'\s*\n.*?^END\s*\n?', '',text)
    t=m.heightmap();w=(t['width']-2*t['border'])*10;h=(t['height']-2*t['border'])*10
    start_objects=[]
    for o in m.objects():
        for k,_,v in o['properties']:
            if k=='waypointName' and re.fullmatch(r'Player_\d+_Start',v):
                start_objects.append((v,o))
    expected={f'Player_{i}_Start' for i in range(1,len(start_objects)+1)}
    if not 2<=len(start_objects)<=8 or {v for v,_ in start_objects}!=expected:
        raise ValueError('Map cache requires 2..8 unique consecutive player starts')
    lines=[f'MapCache {key}',f'  fileSize = {path.stat().st_size}',
           f'  fileCRC = {zlib.crc32(path.read_bytes())}', '  timestampLo = 0','  timestampHi = 0',
           '  isOfficial = yes','  isMultiplayer = yes','  isScenarioMP = no',f'  numPlayers = {len(start_objects)}',
           '  extentMin = X:0.00 Y:0.00 Z:0.00',f'  extentMax = X:{w:.2f} Y:{h:.2f} Z:0.00',
           '  displayName = '+escaped(title.encode('utf-16-le')),
           '  description = '+escaped(description.encode('utf-16-le'))]
    for v,o in start_objects:
        lines.append(f'  {v} = X:{o["x"]:.2f} Y:{o["y"]:.2f} Z:0.00')
    lines.append('END')
    cache.write_text(text.rstrip()+'\n\n'+'\n'.join(lines)+'\n',encoding='cp1252')
