"""Capture reproducible map screenshots from BFME2's D3D9 render target.

Launches an isolated test skirmish, reveals terrain and positions the camera.
Requires a prepared runtime and built strategic extension; refuses a running game.
"""

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path, PureWindowsPath
import re
import shutil

from bfmexbar.paths import ROOT
from bfmexbar.formats.map import Map, sha


def validate_shots(shots):
    if not isinstance(shots,list) or not 1<=len(shots)<=8:
        raise ValueError('Provide 1..8 camera shots')
    result=[]
    for shot in shots:
        if not isinstance(shot,(list,tuple)) or len(shot)!=4:
            raise ValueError('Each shot must contain NAME X Y HEIGHT')
        name,*values=shot
        if not isinstance(name,str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,63}',name):
            raise ValueError('Shot names must be lowercase names containing letters, digits or hyphens')
        try:
            values=[float(v) for v in values]
        except (TypeError,ValueError) as error:
            raise ValueError('Shot coordinates and height must be numbers') from error
        if not all(math.isfinite(v) for v in values) or values[2]<=0:
            raise ValueError('Shot coordinates must be finite and height must be positive')
        result.append([name,*values])
    if len({s[0] for s in result})!=len(result):
        raise ValueError('Shot names must be unique')
    return result


def resolve_map(mod, name):
    """Resolve a virtual map name within the prepared mod, never a retail fallback."""
    relative=PureWindowsPath(name)
    if relative.is_absolute() or relative.drive or '..' in relative.parts:
        raise ValueError('Map must be a relative maps\\...\\name.map path')
    if not relative.parts or relative.parts[0].lower()!='maps' or relative.suffix.lower()!='.map':
        raise ValueError('Map must be a relative maps\\...\\name.map path')
    mod=Path(mod).resolve()
    path=mod.joinpath(*relative.parts)
    if not path.exists() and len(relative.parts)==2:
        path=mod/'maps'/relative.stem/relative.name
    path=path.resolve()
    if not path.is_relative_to(mod) or not path.is_file():
        raise ValueError(f'Map not found in the prepared mod: {name}')
    return path, str(PureWindowsPath(path.relative_to(mod)))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--map',required=True,help='Installed map, e.g. maps\\name\\name.map')
    shots=parser.add_mutually_exclusive_group(required=True)
    shots.add_argument('--shot',nargs=4,action='append',metavar=('NAME','X','Y','HEIGHT'))
    shots.add_argument('--tour',type=Path,help='JSON with a shots array; output/hash fields are recomputed')
    parser.add_argument('--out',required=True,type=Path,help='New or empty output directory')
    parser.add_argument('--graphics',choices=['Low','Medium','High','UltraHigh'],default='Medium')
    args=parser.parse_args()
    try:
        views=validate_shots(json.loads(args.tour.read_text())['shots'] if args.tour else args.shot)
        config=json.loads((ROOT/'runtime/bfme-host/manifest.json').read_text())
        source,native_path=resolve_map(config['mod'],args.map)
        data=source.read_bytes()
        m=Map(data)
        t=m.heightmap()
        extent=[(t[k]-2*t['border'])*10 for k in ('width','height')]
        if any(not (0<=s[1]<=extent[0] and 0<=s[2]<=extent[1]) for s in views):
            raise ValueError('Shot focus must lie inside the playable map')
        out=args.out.resolve()
        if out.exists() and (not out.is_dir() or any(out.iterdir())):
            raise ValueError('Output directory must be new or empty; previous evidence is never overwritten')
    except (OSError,ValueError,KeyError) as error:
        parser.error(str(error))
    out.mkdir(parents=True,exist_ok=True)
    manifest=dict(schema=1,status='running',started_at=datetime.now(timezone.utc).isoformat(),
                  map=native_path,launch_map=args.map,map_sha256=sha(data),graphics=args.graphics,
                  capture_method='native-d3d9-render-target',terrain_revealed=True,
                  includes_hud=True,shots_requested=views)
    tour=out/'tour.json'
    tour.write_text(json.dumps(dict(output=str(out),map_sha256=sha(data),shots=views),indent=2)+'\n')
    evidence=out/'capture.json'
    evidence.write_text(json.dumps(manifest,indent=2)+'\n')
    try:
        from bfmexbar.cli import launch
        code=launch(['--map-check','--map',args.map,'--map-tour',str(tour),'--graphics',args.graphics])
        validation=json.loads((out/'native-validation.json').read_text())
        manifest.update(status='passed' if code==0 else 'failed',shots=validation['shots'],
                        errors=validation['errors'],extension_validation=validation['outcome'])
        if sha(source.read_bytes())!=manifest['map_sha256']:
            manifest['errors'].append('Source map changed during capture')
            manifest['status']='failed';code=1
        # Preserve this run's raw evidence before another test replaces it.
        shutil.copy2(ROOT/'runtime/bfme-host/verification/skirmish_retail.json',out/'engine-report.json')
        return code
    except BaseException as error:
        manifest.update(status='failed',error=str(error))
        raise
    finally:
        manifest['finished_at']=datetime.now(timezone.utc).isoformat()
        evidence.write_text(json.dumps(manifest,indent=2)+'\n')


if __name__=='__main__':
    raise SystemExit(main())
