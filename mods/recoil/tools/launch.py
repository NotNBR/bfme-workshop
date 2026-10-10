"""Start only the isolated local Recoil runtime; no lobby or online services."""
import argparse
import json
import pathlib
import re
import subprocess
import sys

ROOT=next(p for p in pathlib.Path(__file__).resolve().parents if (p/'pyproject.toml').is_file())
ENGINE=ROOT/'local/runtime'/'engine'


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--test',action='store_true')
    p.add_argument('--headless',action='store_true')
    p.add_argument('--hidden',action='store_true')
    p.add_argument('--army-size',type=int,default=525)
    p.add_argument('--timeout',type=int,default=0)
    p.add_argument('--test-frames',type=int,default=2700)
    args=p.parse_args()
    exe=ENGINE/('spring-headless.exe' if args.headless else 'spring.exe')
    if not exe.exists() or not (ENGINE/'games'/'workshop.sdd'/'objects3d'/'gondor.s3o').exists():
        p.error('Native runtime/content missing. Run mods/recoil/tools/setup.ps1 first.')
    script=ROOT/'local/runtime'/'battle.txt'
    script.write_text('''[GAME]
{
  MapName=bmfe-workshop Pelennor 0.1;
  GameType=bmfe-workshop 0.1;
  IsHost=1;
  OnlyLocal=1;
  HostIP=127.0.0.1;
  MyPlayerName=Player;
  StartPosType=0;
  NumPlayers=1;
  NumTeams=2;
  NumAllyTeams=2;
  [PLAYER0] { Name=Player; Team=0; Spectator=0; }
  [TEAM0] { TeamLeader=0; AllyTeam=0; RGBColor=0.25 0.55 1; Side=Gondor; }
  [TEAM1] { TeamLeader=0; AllyTeam=1; RGBColor=0.8 0.12 0.08; Side=Mordor; }
  [ALLYTEAM0] { NumAllies=0; }
  [ALLYTEAM1] { NumAllies=0; }
  [MODOPTIONS] { armysize=%d; autotest=%d; testframes=%d; }
}
'''%(max(20,min(1500,args.army_size)),int(args.test),max(300,args.test_frames)))
    config=ROOT/'local/runtime'/'workshop.cfg'
    if not config.exists():
        config.write_text('''Fullscreen = 0
XResolutionWindowed = 1440
YResolutionWindowed = 900
WindowBorderless = 0
ShowFPS = 1
ShowClock = 1
VSync = 1
Shadows = 1
ShadowMapSize = 2048
AdvUnitShading = 1
AdvMapShading = 1
GroundDetail = 100
UnitLodDist = 1000
UnitIconDist = 150
CamMode = 1
LuaUI = 1
Sound = 0
HardwareCursor = 1
''')
    command=[str(exe),'--isolation','--isolation-dir',str(ENGINE),'--write-dir',str(ENGINE),
             '--config',str(config),'--only-local','--window',str(script)]
    if args.hidden: command.insert(1,'--hidden')
    print('Starting native Recoil:',exe,flush=True)
    try:
        result=subprocess.run(command,cwd=ENGINE,timeout=args.timeout or None)
        if args.test:
            log=(ENGINE/'infolog.txt').read_text(errors='replace')
            passed='BFX_NATIVE_TEST_PASS' in log and 'LUA_ERRRUN' not in log
            ticks=re.findall(r'BFX_NATIVE_TICK frame=(\d+) units=(\d+) moved=(\d+) damage=([\d.]+) deaths=(\d+)',log)
            report={'passed':passed,'armySize':args.army_size,'headless':args.headless,'exitCode':result.returncode,
                    'ticks':[dict(zip(['frame','units','moved','damage','deaths'],map(float,row))) for row in ticks]}
            (ROOT/'local/runtime'/'native-test.json').write_text(json.dumps(report,indent=2))
            print('Native battle test:', 'PASS' if passed else 'FAIL',flush=True)
            return 0 if passed and result.returncode==0 else 1
        return result.returncode
    except subprocess.TimeoutExpired:
        print('Native test timed out.',file=sys.stderr)
        return 124


if __name__=='__main__': sys.exit(main())
