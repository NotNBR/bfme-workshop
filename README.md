# bfmeXbar

BFME2 remains the running game. Its native animation, skinning, movement, formations, cursor, combat and interface are preserved. The current extension increases camera zoom bounds and command-point ceilings; Supreme Commander-style strategic controls and extreme-scale engine work are still in development.

## Play

Double-click **Launch bfmeXbar.cmd**. The launcher uses the `openbfme2` compatibility and skirmish initialization code to start a native human-versus-easy-AI match on Udun. Factions are random. Use the original BFME2 controls, including the mouse wheel for zoom.

```powershell
.\tools\bfme_host\start.ps1 -Window
.\tools\bfme_host\start.ps1 -Window -Menu
```

The default entry point is now BFME2. Earlier Recoil and browser experiments are retained as reference code.

## Setup

Run **Setup bfmeXbar.cmd**. On this machine it reads the complete installation at `D:\LAN\lotrbfme2\local\bfme2` and uses the adjacent `D:\LAN\openbfme2\tools` launch helpers. The previously used `D:\LAN\bfme2` directory lacked the APT menu assets.

```powershell
.\tools\bfme_host\setup.ps1 -BfmePath 'D:\LAN\lotrbfme2\local\bfme2' -ZoomFactor 8 -ArmyFactor 4
```

Setup creates a project Python environment, installs the pinned dependencies, copies the complete game into `runtime/bfme-host/game`, and builds a local mod. This needs roughly 5 GB of disk space. Proprietary game files, generated mods, profiles and logs remain ignored by Git. The original installation and `openbfme2` source are read only.

The launcher checks the exact BFME2 1.06 binary hash before using the recovered addresses. It redirects saves/options to `runtime/bfme-host/appdata` and uses the existing XP-version and focus compatibility hooks. It also initializes the game-info pointer and player slots that the retail `-file` startup path omits. The Python launcher remains running until the game exits.

## Current changes and limits

- Original unit definitions, animation assets, horde logic, locomotors and cursor resources are preserved.
- Camera maximum height is multiplied by eight in supported stock multiplayer/War of the Ring map metadata. All other decompressed map bytes are checked unchanged. Maps without an explicit limit inherit the global setting.
- The native world camera's far clipping distance is extended to match. This is a version-checked in-memory change; the original executable file stays unchanged.
- Maximum multiplayer command points are multiplied by four; starting command points stay unchanged. This raises the ceiling, not the starting army size. Normal recruitment and resource rules still apply.
- Full Supreme Commander strategic icons, strategic order overlays, simulation scaling, and a Forged Alliance runtime splice are not implemented. A larger configured cap is not proof of large-battle performance.
- Multiplayer compatibility and long matches have not been validated. The current launcher is for local play.

## Verification

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_bfme_host -v
.\tools\bfme_host\start.ps1 -Test
.\tools\bfme_host\start.ps1 -ZoomCheck
```

The runtime check requires actual skirmish mode, at least 100 advancing simulation frames, no crash, a nonblank game window, and unchanged source installation / original profile. Its report and screenshot are saved in `runtime/bfme-host/verification`. Automated checks close their own game after the run.

## Project layout

- `tools/bfme_host/`: original-game launcher, isolated runtime preparation, map-camera and command-limit builder.
- `tests/test_bfme_host.py`: binary-map preservation and decoder/cap checks.
- `tools/import_bfme.py`: shared BIG archive reader.
- `native/` and `tools/native/`: previous Recoil experiment; not the default launcher.
- `legacy/browser/`: archived browser prototype, also preserved at Git tag `browser-prototype`.

See [the host integration notes](docs/bfme-host.md) and [earlier engine research](docs/native-integration.md). Original game assets are not distributed in this repository.
