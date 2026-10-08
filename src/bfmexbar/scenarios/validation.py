"""Validate native Eight Kingdoms battle evidence and complete capture."""
from pathlib import Path
import json
from bfmexbar.paths import ROOT
OUT=ROOT/'artifacts/eight-kingdoms/trailer'

def validate(output, capture=None, destination=None):
    from bfmexbar.capture.kingdoms import resolve_shots
    plan=json.loads((Path(capture or OUT)/'battle-plan.json').read_text())
    shots=resolve_shots(plan['fronts'])
    expected_frames=sum(s[-2] for s in shots)
    report=json.loads((output/'skirmish_retail.json').read_text());run=report['run']
    battle=run.get('kingdoms_battle',{});movie=run.get('kingdoms_movie',{});errors=[]
    if battle.get('spawned')!=200 or battle.get('owned')!=[25]*8:errors.append('Missing armies or developed bases')
    if battle.get('heavySpawned')!=32 or battle.get('heavyOrders')!=32 or battle.get('heavyMoved',0)<16:
        errors.append('Heavy reinforcements not verified')
    if battle.get('enemyPairs')!=4:errors.append('Enemy relationships not verified')
    if battle.get('alliedPairs')!=12:errors.append('Four-player alliances not verified')
    if battle.get('completedBuildings')!=64:errors.append('Missing completed mid-game buildings')
    if battle.get('moved',0)<40 or battle.get('casualties',0)<10:errors.append('Insufficient verified combat')
    if len(battle.get('frontCasualties',[]))!=4 or min(battle.get('frontCasualties',[0]))<10:
        errors.append('Combat not verified at all four fronts')
    if battle.get('error') or movie.get('error'):errors.append('Native battle/capture error')
    if movie.get('frames')!=expected_frames or not movie.get('complete') or movie.get('exitCode'):errors.append('Incomplete video')
    if movie.get('strategicFrames',0)<300 or movie.get('peakIcons',0)<20:errors.append('Strategic views/icons not verified')
    if not run.get('capture_hero_notifications_suppressed'):errors.append('Cinematic notification suppression not enabled')
    if run.get('battalion_symbols',{}).get('peakCollapsed',0)<100:errors.append('Battalion marker grouping not verified')
    if run.get('strategic',{}).get('faults',1) or report.get('profile_touched'):errors.append('Extension/profile check failed')
    raw=Path(capture or OUT)/'battle-footage.bgr0'
    if not raw.exists() or raw.stat().st_size!=expected_frames*1600*720*4:errors.append('Incomplete native frame data')
    result=dict(outcome='fail' if errors else 'pass',errors=errors,map_sha256=run.get('authored_map_sha256'),
        battle=battle,movie=movie,battalion_symbols=run.get('battalion_symbols'),slots=run.get('eight_player_slots'),extension_faults=run.get('strategic',{}).get('faults'),
        original_profile_untouched=not report.get('profile_touched'))
    destination=Path(destination or OUT)
    destination.mkdir(parents=True,exist_ok=True)
    (destination/'battle-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    return int(bool(errors))
