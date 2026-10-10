"""Create an original-BFME host package without changing the game install."""

from common.paths import ROOT, local_path
import argparse
import hashlib
import json
import pathlib
import re
import sys
import tomllib

from formats.big import BigArchive
from formats.map_archive import extend_camera


DEFAULT_STARTING_COMMAND_POINTS=1000
DEFAULT_STARTING_CASH=10000


def command_limits(text,factor,starting=DEFAULT_STARTING_COMMAND_POINTS):
    fields={}
    for faction in ('Good','Evil'):
        for players in range(2,9):
            key=f'{faction}CommandPointsMP{players}'
            match=re.search(r'^\s*'+key+r'\s*=\s*(\d+)\s+(\d+)',text,re.M)
            if not match: raise ValueError('Missing native cap field '+key)
            maximum=round(int(match[2])*factor)
            fields[key]=(min(starting,maximum),maximum)
    return fields


def gameplay_settings(mod,zoom_factor,army_factor,starting_command_points,starting_cash,write=True):
    """Refresh just the settings overlay, preserving authored maps and assets."""
    if not 1<=zoom_factor<=24 or not 1<=army_factor<=10:
        raise ValueError('Zoom factor must be 1–24, army factor 1–10')
    if not 1<=starting_command_points<=10000 or not 0<=starting_cash<=1000000:
        raise ValueError('Starting command points must be 1–10000, cash 0–1000000')
    game_data=(mod/'data/ini/gamedata.ini').read_text(encoding='cp1252')
    limits=command_limits(game_data,army_factor,starting_command_points)
    settings=['; bmfe-workshop: native BFME host. Unit and movement data are untouched.',
              'GameData',f'  DefaultCameraMaxHeight = {300*zoom_factor:g}',
              f'  DefaultStartingCash = {starting_cash}']
    settings.extend(f'  {key} = {a} {b}' for key,(a,b) in limits.items())
    settings.append('End\n')
    path=mod/'data/ini/object/workshop_gamedata.ini'
    content='\n'.join(settings)
    if write and (not path.exists() or path.read_text(encoding='ascii')!=content):
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(content,encoding='ascii')
    return limits


def main():
    preset=tomllib.loads((ROOT/'mods/strategic/config/default.toml').read_text())
    p=argparse.ArgumentParser()
    p.add_argument('--bfme',type=pathlib.Path,default=local_path('game',ROOT.parent/'lotrbfme2'/'local'/'bfme2'))
    p.add_argument('--zoom-factor',type=float,default=preset['zoom_factor'])
    p.add_argument('--army-factor',type=float,default=preset['army_factor'])
    p.add_argument('--starting-command-points',type=int,default=preset.get('starting_command_points',DEFAULT_STARTING_COMMAND_POINTS))
    p.add_argument('--starting-cash',type=int,default=preset.get('starting_cash',DEFAULT_STARTING_CASH))
    args=p.parse_args()
    if not 1<=args.zoom_factor<=24 or not 1<=args.army_factor<=10:
        p.error('Zoom factor must be 1–24, army factor 1–10')
    if not 1<=args.starting_command_points<=10000 or not 0<=args.starting_cash<=1000000:
        p.error('Starting command points must be 1–10000, cash 0–1000000')
    game=args.bfme.resolve()
    for file in ('lotrbfme2.exe','game.dat','INI.big','Maps.big','apt/AptLevel0.big','apt/Background.big'):
        if not (game/file).is_file():p.error('Missing BFME file: '+str(game/file))
    output=ROOT/'local/runtime'/'bfme-host';mod=output/'mod'
    mod.mkdir(parents=True,exist_ok=True)
    # Only base + known official patch archives participate. Never silently
    # blend unknown mods into the package.
    archives=[BigArchive(game/'INI.big'),BigArchive(game/'Maps.big')]
    archives.extend(BigArchive(path) for path in sorted(game.glob('*.big'))
                    if path.name.lower().startswith('data'))
    patches=sorted(game.glob('_patch*.big'))
    archives.extend(BigArchive(path) for path in patches)
    effective={}
    for archive in archives:
        for key in archive.entries:effective[key]=archive
    # BFME's folder-mod enumeration is not assumed to merge directory lists.
    # Supply complete native INI and map trees, with original bytes preserved,
    # before overlaying the explicitly listed camera/cap changes.
    baseline={}
    for key,archive in effective.items():
        if not key.startswith(('data/ini/','maps/')):continue
        relative=pathlib.PurePosixPath(key)
        if relative.is_absolute() or '..' in relative.parts:raise ValueError('Unsafe archive path')
        target=mod/relative;target.parent.mkdir(parents=True,exist_ok=True)
        content=archive.read_bytes(key);target.write_bytes(content)
        baseline[key]=hashlib.sha256(content).hexdigest()
    limits=gameplay_settings(mod,args.zoom_factor,args.army_factor,args.starting_command_points,args.starting_cash)
    report={'host':'BFME II original runtime','game':str(game),'mod':str(mod),'zoomFactor':args.zoom_factor,
        'armyFactor':args.army_factor,'startingCommandPoints':args.starting_command_points,
        'startingCash':args.starting_cash,'commandLimits':limits,'maps':[],'baselineSHA256':baseline,
        'gameDatSHA256':hashlib.sha256((game/'game.dat').read_bytes()).hexdigest(),
        'preserved':['unit definitions','W3D meshes and skinning','animation state machines','locomotors',
                     'horde formations','combat behaviors','mouse.ini and cursor resources','audio','HUD'],
        'validation':'Package built and camera-only byte differences checked; in-game verification separate.'}
    for key,archive in effective.items():
        if not key.endswith('.map') or not key.startswith(('maps/map mp ','maps/map wor ')):continue
        data,changes=extend_camera(archive.read_bytes(key),args.zoom_factor)
        if changes:
            target=mod/pathlib.PurePosixPath(key);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        report['maps'].append({'path':key,'source':archive.path.name,'cameraChanges':changes,
                               'sha256':hashlib.sha256(data).hexdigest(),'otherDecompressedBytesUnchanged':True})
    (output/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(f'BFME host package: {mod}\nOriginal maps with extended camera: {len(report["maps"])}\n'
          f'Army cap multiplier: {args.army_factor:g}; starting command points: {args.starting_command_points}; starting cash: {args.starting_cash}.')


if __name__=='__main__':main()
