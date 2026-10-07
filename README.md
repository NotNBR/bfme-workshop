# bfmeXbar

BFME2 remains the running game. Its native animation, skinning, movement, formations, cursor, combat and interface are preserved. Far zoom now transitions to an orthographic strategic view with unit and building symbols. The extension also increases camera zoom bounds and command-point ceilings; extreme-scale simulation work is still in development.

## Play

Double-click **Launch bfmeXbar.cmd**. The launcher uses the `openbfme2` compatibility and skirmish initialization code to start a native human-versus-easy-AI match on Udun. Factions are random. Use the original BFME2 controls, including the mouse wheel for zoom.

```powershell
.\tools\bfme_host\start.ps1 -Window
.\tools\bfme_host\start.ps1 -Window -Menu
```

For a prepared battle, use **Launch Orcs vs Elves.cmd** (or `start.ps1 -Window -Battle orcs-elves`). Grey Mountains opens with Mordor and Elven troops fighting in the central valley. Both sides have their original fortress plus eight resource, production and defensive buildings. The map is fully revealed. Twelve Mordor and eight Elven battalions open the battle; ten Mordor and four Elven reserve battalions march from their bases in four staggered groups. The Witch-king and Mouth of Sauron lead Mordor; Haldir and Glorfindel lead the Elves. All four heroes join the opening fight. The armies use native movement, formations and combat, and remain controllable.

The default entry point is now BFME2. Earlier Recoil and browser experiments are retained as reference code.

The launcher uses 1600 × 1200 with the original 4:3 aspect ratio. Zoom out with the mouse wheel; the Grey Mountains ceiling is now 7,200 (24x the original limit). Between camera heights 800 and 2,600 the view smoothly tilts overhead. Above 2,600 it settles into true orthographic projection. Symbols fade in separately between heights 1,400 and 2,000, and follow the native interpolated render positions every frame. The tilt responds every frame, and health bars shrink to compact widths at strategic distances. Native veterancy pips use a stable scale so the extended camera limit cannot inflate them. Symbols distinguish infantry, archers, pikes, cavalry, siege, monsters, heroes, builders and flying units. All buildings share one house-shaped symbol. Heroes use stars that are 40% larger than the other symbol classes. All symbol contours and glyphs are 12% larger than the previous version. Enemies are red; other units retain their owner color. Selected units have a brighter, thicker gold border, including every member of a selected battalion. Zooming back in restores the native perspective and removes the symbols. Native hidden, stealth and shroud checks exclude unseen objects.

Selection, box selection, the cursor and orders still run through BFME2. Orthographic picking uses parallel rays so screen positions remain aligned with the battlefield. To start without this extension, use `start.ps1 -Window -NoStrategic`.

## Setup

Run **Setup bfmeXbar.cmd**. On this machine it reads the complete installation at `D:\LAN\lotrbfme2\local\bfme2` and uses the adjacent `D:\LAN\openbfme2\tools` launch helpers. The previously used `D:\LAN\bfme2` directory lacked the APT menu assets.

```powershell
.\tools\bfme_host\setup.ps1 -BfmePath 'D:\LAN\lotrbfme2\local\bfme2' -ZoomFactor 24 -ArmyFactor 4
```

Setup creates a project Python environment, installs the pinned dependencies, copies the complete game into `runtime/bfme-host/game`, and builds a local mod. This needs roughly 5 GB of disk space. Proprietary game files, generated mods, profiles and logs remain ignored by Git. The original installation and `openbfme2` source are read only.

The strategic extension is compiled as a 32-bit DLL using the existing MSVC 7.1 toolchain in the adjacent openbfme2 reference checkout. It loads only into this launcher's verified local BFME2 1.06 process; generated binaries remain under `runtime/`.

The launcher checks the exact BFME2 1.06 binary hash before using the recovered addresses. It redirects saves/options to `runtime/bfme-host/appdata` and uses the existing XP-version and focus compatibility hooks. It also initializes the game-info pointer and player slots that the retail `-file` startup path omits. The Python launcher remains running until the game exits.

## Current changes and limits

- Original unit definitions, animation assets, horde logic, locomotors and cursor resources are preserved.
- Camera maximum height is multiplied by twenty-four in supported stock multiplayer/War of the Ring map metadata. All other decompressed map bytes are checked unchanged. Maps without an explicit limit inherit the global setting.
- The native world camera's far clipping distance is extended to match. This is a version-checked in-memory change; the original executable file stays unchanged.
- Maximum multiplayer command points are multiplied by four; starting command points stay unchanged. This raises the ceiling, not the starting army size. Normal recruitment and resource rules still apply.
- Strategic symbols distinguish broad unit roles and use one common building icon, including selectable building plots. Dense-army icon clustering, strategic order overlays, simulation scaling, and a Forged Alliance runtime splice are not implemented. A larger configured cap is not proof of large-battle performance.
- Multiplayer compatibility and long matches have not been validated. The current launcher is for local play.

## Verification

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_bfme_host -v
.\tools\bfme_host\start.ps1 -Test
.\tools\bfme_host\start.ps1 -ZoomCheck
.\tools\bfme_host\start.ps1 -StrategicCheck
.\tools\bfme_host\start.ps1 -Window -CameraTrace
```

The runtime check requires actual skirmish mode, at least 100 advancing simulation frames, no crash, a nonblank game window, and unchanged source installation / original profile. Its report and screenshot are saved in `runtime/bfme-host/verification`. Automated checks close their own game after the run. `-CameraTrace` records camera properties throughout movement to `runtime/bfme-host/verification/camera-trace.csv`; see the host integration notes for plotting and interpretation.

## Project layout

- `tools/bfme_host/`: original-game launcher, isolated runtime preparation, map-camera and command-limit builder.
- `tests/test_bfme_host.py`: binary-map preservation and decoder/cap checks.
- `tools/import_bfme.py`: shared BIG archive reader.
- `native/host/`: BFME2 strategic camera, picking and symbol-rendering extension.
- `native/game/`, `native/client.lua` and `tools/native/`: previous Recoil experiment; not the default launcher.
- `legacy/browser/`: archived browser prototype, also preserved at Git tag `browser-prototype`.

See [the host integration notes](docs/bfme-host.md) and [earlier engine research](docs/native-integration.md). Original game assets are not distributed in this repository.

## Gameplay showcase

`python tools/bfme_host/launch.py --showcase` starts the prepared battle and records a 29-second camera tour at 1600 x 1200 / 30 fps. Install the optional recording dependency with `pip install imageio-ffmpeg==0.6.0`. It records the game window only, without audio. The tour opens with a gentle pan and rotation, settles at its original bearing, zooms out in two stages, then returns to the close-up. The camera returns to player control after 30 seconds; ordinary launches never enable the tour. The raw recording and diagnostics are saved in `artifacts/showcase/`.

Run `python tools/bfme_host/finish_showcase.py` after the recorder finishes to export the video without added captions as `artifacts/showcase/bfmeXbar-gameplay-showcase.mp4`. The completed showcase is 29 seconds of continuous gameplay at 30 fps, with no audio.
