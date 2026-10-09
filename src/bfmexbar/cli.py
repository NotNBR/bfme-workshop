"""One entry point for the strategic mod, map projects and showcases."""
import argparse
import importlib
import json
from pathlib import Path
import runpy
import shutil
import sys
from bfmexbar.paths import ROOT
from bfmexbar.runs import create_run, update_run, digest


def invoke(module, arguments):
    previous = sys.argv
    sys.argv = [module, *arguments]
    try:
        runpy.run_module(module, run_name='__main__', alter_sys=True)
    except SystemExit as result:
        return result.code or 0
    finally:
        sys.argv = previous
    return 0


def launch(arguments):
    from bfmexbar.host.launch import main as host_main
    previous = sys.argv
    sys.argv = ['bfx play', *arguments]
    try:
        return host_main() or 0
    finally:
        sys.argv = previous


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest='command', required=True)
    commands.add_parser('play', help='Launch BFME2; accepts existing launcher flags', add_help=False)
    commands.add_parser('screenshots', help='Capture native map views and camera evidence', add_help=False)
    commands.add_parser('host', help='Prepare or build the isolated BFME2 runtime').add_argument('action', choices=('build','prepare','prepare-worktree'))
    commands.add_parser('mod', help='Build or check the strategic extension').add_argument('action', choices=('build','check','zoom-check'))
    maps = commands.add_parser('map', help='Build maps or use the authoring toolkit')
    maps.add_argument('action', choices=('build','inspect','catalog','checkout','status','apply','preview','diff','handoff','checkpoint'))
    maps.add_argument('target')
    maps.add_argument('--run-id')
    scenario = commands.add_parser('scenario', help='Plan or play a prepared battle')
    scenario.add_argument('action', choices=('plan','play'))
    scenario.add_argument('project', choices=('eight-kingdoms-4v4',))
    scenario.add_argument('--output', type=Path)
    show = commands.add_parser('showcase', help='Capture or edit a showcase in its own run')
    show.add_argument('action', choices=('capture','edit'))
    show.add_argument('project', choices=('eight-kingdoms',))
    show.add_argument('--run-id')
    show.add_argument('--run-dir', type=Path)
    video = commands.add_parser('video', help='Create a verified size-limited video export')
    video.add_argument('source', type=Path)
    video.add_argument('--output', required=True, type=Path)
    video.add_argument('--profile', default='under20mb', choices=('master','mobile','under20mb'))
    video.add_argument('--profiles', type=Path, default=ROOT/'projects/showcases/eight-kingdoms/exports.toml')
    return p


def main(argv=None):
    p = parser(); args, rest = p.parse_known_args(argv)
    if rest and rest[0] == '--': rest = rest[1:]
    if args.command == 'play':
        return launch(rest)
    if args.command == 'screenshots':
        return invoke('bfmexbar.capture.screenshots',rest)
    if args.command == 'host':
        return invoke('bfmexbar.host.'+{'build':'build','prepare':'prepare','prepare-worktree':'prepare_worktree'}[args.action],rest)
    if args.command == 'mod':
        if args.action == 'build':
            return invoke('bfmexbar.strategic.build',rest)
        return launch(['--strategic-check' if args.action == 'check' else '--zoom-check',*rest])
    if args.command == 'map':
        if args.action != 'build':
            return invoke('bfmexbar.mapkit.cli',[args.action,args.target,*rest])
        available = [path.parent.name for path in (ROOT/'projects/maps').glob('*/build.py')]
        if args.target not in available:
            p.error('Unknown map project; choose '+', '.join(available))
        module = importlib.import_module('bfmexbar.projects.maps.'+args.target.replace('-','_')+'.build')
        output = create_run('maps',args.target,args.run_id)
        module.OUT = output
        previous = sys.argv; sys.argv = ['bfx map build',*rest]
        try:
            code = module.main() or 0
            if code: raise RuntimeError(f'Map builder returned {code}')
            source = ROOT/'runtime/bfme-host/mod/maps'/module.NAME/(module.NAME+'.map')
            if source.exists():
                shutil.copytree(source.parent,output/'map'/source.parent.name)
                update_run(output,status='built',map_sha256=digest(source))
            else:
                update_run(output,status='built')
        except BaseException:
            update_run(output,status='failed'); raise
        finally:
            sys.argv = previous
        for path in output.iterdir():
            if not path.is_file() or path.name == 'manifest.json': continue
            if path.suffix.lower() in ('.png','.jpg','.tga'):
                path.replace(output/'previews'/path.name)
            elif path.suffix.lower() in ('.zip','.map'):
                path.replace(output/'map'/path.name)
            elif path.name == 'build.json':
                path.replace(output/'validation'/path.name)
            elif path.name == 'tour.json':
                tour=json.loads(path.read_text())
                tour['output']=(output/'validation/native').relative_to(ROOT).as_posix()
                tour['photo_output']=(output/'previews/photo').relative_to(ROOT).as_posix()
                path.write_text(json.dumps(tour,indent=2)+'\n')
        print(output); return 0
    if args.command == 'scenario':
        if args.action == 'play': return launch(['--kingdoms-battle',*rest])
        if rest: p.error('Unexpected scenario plan arguments: '+' '.join(rest))
        from bfmexbar.scenarios.placement import plan
        output = args.output or create_run('scenarios',args.project)
        result = plan(ROOT/'runtime/bfme-host/mod',output=output)
        if not args.output: update_run(output,status='planned',map_sha256=result['map_sha256'])
        print(output/'battle-plan.json'); return 0
    if args.command == 'showcase':
        if rest: p.error('Unexpected showcase arguments: '+' '.join(rest))
        if args.action == 'capture':
            if args.run_dir: p.error('capture creates a new run; use --run-id')
            output = create_run('showcases',args.project,args.run_id)
            from bfmexbar.scenarios import kingdoms
            kingdoms.OUT = output/'capture'; kingdoms.VALIDATION_OUT = output/'validation'
            print(f'Capturing into {output}',flush=True)
            try:
                code = launch(['--kingdoms-trailer'])
                plan = json.loads((output/'capture/battle-plan.json').read_text())
                update_run(output,status='failed' if code else 'captured',map_sha256=plan['map_sha256'])
                return code
            except BaseException:
                update_run(output,status='failed'); raise
        if not args.run_dir: p.error('showcase edit requires --run-dir from a capture')
        if args.run_id: p.error('edit uses --run-dir, not --run-id')
        output = args.run_dir.resolve()
        manifest = json.loads((output/'manifest.json').read_text())
        if manifest['project'] != args.project or manifest.get('kind') != 'showcases':
            p.error('Run does not belong to this showcase')
        if manifest['status'] == 'complete': p.error('Completed runs are immutable; create another run')
        edit = importlib.import_module('bfmexbar.projects.showcases.eight_kingdoms.edit')
        edit.OUT=output/'intermediates'; edit.CAPTURE=output/'capture'
        edit.EXPORT=output/'exports'; edit.VALIDATION=output/'validation'
        try:
            edit.main(); update_run(output,status='complete')
        except BaseException:
            update_run(output,status='edit-failed'); raise
        print(output/'exports'); return 0
    if args.command == 'video':
        if rest: p.error('Unexpected video arguments: '+' '.join(rest))
        from bfmexbar.video.encoding import export_profile
        print(json.dumps(export_profile(args.source,args.output,args.profiles,args.profile),indent=2))
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
