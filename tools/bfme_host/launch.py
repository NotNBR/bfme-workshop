"""Run native BFME2 using openbfme2's verified compatibility/slot setup."""
import argparse
import ctypes
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import winreg

from prepare import SUPPORTED_SHA256
import camera

ROOT = pathlib.Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--window', action='store_true')
    parser.add_argument('--menu', action='store_true')
    parser.add_argument('--test', action='store_true')
    parser.add_argument('--zoom-check', action='store_true')
    parser.add_argument('--strategic', action='store_true')
    parser.add_argument('--strategic-check', action='store_true')
    parser.add_argument('--camera-trace', action='store_true', help='Record native camera properties per frame to CSV')
    parser.add_argument('--vanilla', action='store_true', help='Diagnostic run without the bfmeXbar mod')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--map')
    parser.add_argument('--battle', choices=['orcs-elves'], help='Start a prepared Mordor-versus-Elves battalion battle')
    args = parser.parse_args()
    args.map=args.map or (r'maps\map mp grey mountains.map' if args.battle else r'maps\map mp tournament udun.map')
    if args.battle and args.map.lower()!=r'maps\map mp grey mountains.map':
        parser.error('The prepared battle uses Grey Mountains; omit --map for this preset.')
    if args.battle:args.strategic=True
    if args.zoom_check:
        args.test = True
    if args.strategic_check:
        args.strategic = args.test = True
    if args.camera_trace:
        args.strategic = True
    manifest = ROOT / 'runtime/bfme-host/manifest.json'
    if not manifest.exists():
        parser.error('Run Setup bfmeXbar.cmd first.')
    config = json.loads(manifest.read_text())
    if 'sandbox' not in config:
        parser.error('Run Setup bfmeXbar.cmd to prepare the complete game directory.')
    game_dir = pathlib.Path(config['sandbox'])
    game_args = ['-mod', config['mod']]
    if args.vanilla:
        game_args = []
    if args.window or args.test:
        game_args += ['-win', '-xres', '1920', '-yres', '1080']
    if not args.menu and not args.test:
        game_args += ['-file', args.map]
    print(subprocess.list2cmdline([str(game_dir / 'lotrbfme2.exe'), *game_args]), flush=True)
    if args.dry_run:
        return 0
    for binary in (game_dir / 'game.dat', pathlib.Path(config['game']) / 'game.dat'):
        if hashlib.sha256(binary.read_bytes()).hexdigest() != SUPPORTED_SHA256:
            parser.error(f'Unsupported game.dat; the hooks require verified BFME2 1.06: {binary}')
    reference = pathlib.Path(config['referenceTools'])
    if not (reference / 'game_smoke.py').is_file():
        parser.error(f'Missing openbfme2 launch helper: {reference}')
    # Keep the reference checkout untouched, including Python bytecode caches.
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(reference))
    import game_smoke
    if args.battle:
        import battle
        battle.register(game_smoke,pathlib.Path(config['mod']),test=args.test)
    if args.strategic_check:
        import strategic_check
        strategic_check.register(game_smoke)
    if args.zoom_check:
        import zoom_check
        zoom_check.register(game_smoke)
    if not args.vanilla:
        camera.register(game_smoke, config['zoomFactor'])
        if args.strategic:
            import strategic
            extension=ROOT/'runtime/bfme-host/extension/bfmexbar-strategic.dll'
            if not extension.is_file():
                parser.error('Strategic extension is missing. Run Setup bfmeXbar.cmd first.')
            strategic.register(game_smoke, extension, trace=args.camera_trace or args.strategic_check,battle=bool(args.battle))
    boot = game_smoke.boot_smoke
    # This installation's registry selects the Witch-king-named profile leaf,
    # even though the executable is BFME2. Seed the leaf the game actually uses.
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                r'SOFTWARE\Electronic Arts\Electronic Arts\The Battle for Middle-earth II',
                0, winreg.KEY_READ | winreg.KEY_WOW64_32KEY) as key:
            leaf = winreg.QueryValueEx(key, 'UserDataLeafName')[0]
    except FileNotFoundError:
        leaf = boot.PROFILE_LEAF
    if not isinstance(leaf, str) or pathlib.PureWindowsPath(leaf).name != leaf or leaf in ('', '.', '..'):
        parser.error('Invalid BFME2 profile directory name in the registry.')
    boot.PROFILE_LEAF = leaf
    output = manifest.parent / 'verification'
    output.mkdir(exist_ok=True)
    game_smoke.OUT = output
    boot.OUT = output / 'boot'
    boot.boot_image.OUT = boot.OUT
    boot.boot_image.build.EXE = pathlib.Path(config['game']) / 'game.dat'
    appdata = manifest.parent / 'appdata'
    # Retail loads Resolution from Options.ini after parsing the command line.
    # Update only the isolated profile, preserving the user's original profile.
    profile = boot.prepare_sandbox_profile(appdata)
    options = profile / 'Options.ini'
    text = options.read_text()
    text, replaced = re.subn(r'(?m)^Resolution\s*=.*$', 'Resolution = 1920 1080', text)
    if not replaced:text += '\nResolution = 1920 1080\n'
    options.write_text(text)
    if args.test:
        status = game_smoke.main([
            'skirmish', '--game-dir', str(game_dir), '--retail', '--appdata', str(appdata),
            '--args', subprocess.list2cmdline(game_args), '--map', args.map, '--player',
            '--seconds', '30', '--min-frames', '100', '--timeout', '180',
            '--guard', config['game'],
        ])
        if args.zoom_check and status == 0:
            return zoom_check.validate(output)
        if args.strategic_check:
            return strategic_check.validate(output)
        if args.battle:
            return battle.validate(output)
        return status
    running = game_smoke.other_games()
    if running:
        parser.error(f'Another BFME2 session is already running: {running}')
    ctypes.WinDLL('user32').SetProcessDPIAware()
    guard = boot.ProfileGuard()
    game = game_smoke.Game(game_dir, subprocess.list2cmdline(game_args), appdata)
    if not args.menu:
        game.on('fileSlotsSet', game_smoke.skirmish_setup(True, player=True))
    (manifest.parent / 'last-launch.json').write_text(json.dumps({
        'host': 'BFME2 1.06', 'game': str(game_dir), 'args': game_args,
        'referenceTools': str(reference), 'mode': 'menu' if args.menu else 'human vs easy AI',
    }, indent=2))
    print('Native BFME2 is running. Close the game to finish this launcher.', flush=True)
    result = game.run(7 * 24 * 3600)
    profile_report, touched = guard.check()
    (output / 'interactive.json').write_text(json.dumps({
        'run': result, 'profile_guard': profile_report, 'profile_touched': touched,
    }, indent=2, default=str))
    return 0 if result.get('stopped') == 'exit' and result.get('exit_code', 0) == 0 and not touched else 1


if __name__ == '__main__':
    sys.exit(main())
