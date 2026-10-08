# bfmeXbar

**Development layout:** [Repository guide](docs/repository-layout.md) | [Strategic mod](projects/strategic/README.md) | [Map projects](projects/maps/eight-kingdoms/README.md) | [Battle scenario](projects/scenarios/eight-kingdoms-4v4/README.md) | [Showcase](projects/showcases/eight-kingdoms/README.md)

**Eight-player map:** [Eight Kingdoms](projects/maps/eight-kingdoms/README.md) follows the supplied reference terrain. Run **scripts/launchers/Launch Eight Kingdoms.cmd** for one human against seven easy AIs.

**New original map:** [The Ashen March](docs/ashen-march.md), a dark Gondorian frontier with broken ridges, ruined watches and a deadwood flank. Run **scripts/launchers/Launch Ashen March.cmd**. [Technical findings](docs/ashen-march-format-findings.md) document its from-scratch construction.

BFME2 remains the running game. Its native animation, skinning, movement, formations, cursor, combat and interface are preserved. Far zoom now transitions to an orthographic strategic view with unit and building symbols. The extension also increases camera zoom bounds and command-point ceilings; extreme-scale simulation work is still in development.

## Play

Double-click **Launch bfmeXbar.cmd**. The launcher uses the `openbfme2` compatibility and skirmish initialization code to start a native human-versus-easy-AI match on Udun. Factions are random. Use the original BFME2 controls, including the mouse wheel for zoom.

```powershell
.\src\tools\bfme_host\start.ps1 -Window
.\src\tools\bfme_host\start.ps1 -Window -Menu
```

For a prepared battle, use **scripts/launchers/Launch Orcs vs Elves.cmd** (or `start.ps1 -Window -Battle orcs-elves`). Grey Mountains opens with Mordor and Elven troops fighting in the central valley. Both sides have their original fortress plus eight resource, production and defensive buildings. The map is fully revealed. Twelve Mordor and eight Elven battalions open the battle; ten Mordor and four Elven reserve battalions march from their bases in four staggered groups. The Witch-king and Mouth of Sauron lead Mordor; Haldir and Glorfindel lead the Elves. All four heroes join the opening fight. The armies use native movement, formations and combat, and remain controllable.

For the new large map, use **scripts/launchers/Launch Ithilien Frontier.cmd**. [Ithilien Frontier](projects/maps/ithilien-frontier/README.md) expands the native Ithilien landscape to 840 x 953 playable tiles, about three times Grey Mountains' area, with sculpted ridges, mountain walls, rolling hills and 4,111 additional trees, plants, rocks and ruins. It starts a fully revealed Mordor-versus-Elves skirmish with normal base-building and a strategic camera ceiling of 16,000. Setup also builds and registers this map. Native load/render checks passed; long-match performance and crossing pathfinding still need playtesting.

The default entry point is now BFME2. Earlier Recoil and browser experiments are retained as reference code.

The launcher uses 1600 × 1200 with the original 4:3 aspect ratio. Zoom out with the mouse wheel; the Grey Mountains ceiling is now 7,200 (24x the original limit). Between camera heights 800 and 2,600 the view smoothly tilts overhead. Above 2,600 it settles into true orthographic projection. Symbols fade in separately between heights 1,400 and 2,000, and follow the native interpolated render positions every frame. The tilt responds every frame, and health bars shrink to compact widths at strategic distances. Native veterancy pips use a stable scale so the extended camera limit cannot inflate them. Symbols distinguish infantry, archers, pikes, cavalry, siege, monsters, heroes, builders and flying units. All buildings share one house-shaped symbol. Heroes use stars that are 40% larger than the other symbol classes. All symbol contours and glyphs are 12% larger than the previous version. Enemies are red; other units retain their owner color. Selected units have a brighter, thicker gold border, including every member of a selected battalion. Zooming back in restores the native perspective and removes the symbols. Native hidden, stealth and shroud checks exclude unseen objects.

Selection, box selection, the cursor and orders still run through BFME2. Orthographic picking uses parallel rays so screen positions remain aligned with the battlefield. To start without this extension, use `start.ps1 -Window -NoStrategic`.

## Setup

Run **scripts/launchers/Setup bfmeXbar.cmd**. On this machine it reads the complete installation at `D:\LAN\lotrbfme2\local\bfme2` and uses the adjacent `D:\LAN\openbfme2\tools` launch helpers. The previously used `D:\LAN\bfme2` directory lacked the APT menu assets.

```powershell
.\src\tools\bfme_host\setup.ps1 -BfmePath 'D:\LAN\lotrbfme2\local\bfme2' -ZoomFactor 24 -ArmyFactor 4
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
.\src\tools\bfme_host\start.ps1 -Test
.\src\tools\bfme_host\start.ps1 -ZoomCheck
.\src\tools\bfme_host\start.ps1 -StrategicCheck
.\src\tools\bfme_host\start.ps1 -Window -CameraTrace
```

The runtime check requires actual skirmish mode, at least 100 advancing simulation frames, no crash, a nonblank game window, and unchanged source installation / original profile. Its report and screenshot are saved in `runtime/bfme-host/verification`. Automated checks close their own game after the run. `-CameraTrace` records camera properties throughout movement to `runtime/bfme-host/verification/camera-trace.csv`; see the host integration notes for plotting and interpretation.

For designing an original map from an empty plane, see the [rough-to-polished map creation workflow](docs/map-creation-workflow.md) and its [worked theme example](docs/map-workflow-example.md).

## Project layout

The root has seven folders. [The repository guide](docs/repository-layout.md)
explains the commands and the folders inside each workstream.

- `projects/`: strategic patch, maps, scenarios and showcases.
- `src/`: shared Python/native code, compatibility modules and legacy experiments.
- `scripts/`: setup, CLI, configuration and specialized launchers.
- `tests/`: unit, integration and native verification.
- `docs/`: documentation and license notices.
- `runtime/`: ignored local game/runtime files.
- `artifacts/`: ignored generated maps, videos and validation reports.

The main launcher stays at the root. Other launch and setup shortcuts are in
`scripts/launchers/`. Previous video paths remain unchanged.

## Gameplay showcase

`python src/tools/bfme_host/launch.py --showcase` starts the prepared battle and records a 29-second camera tour at 1600 x 1200 / 30 fps. Install the optional recording dependency with `pip install imageio-ffmpeg==0.6.0`. It records the game window only, without audio. The tour opens with a gentle pan and rotation, settles at its original bearing, zooms out in two stages, then returns to the close-up. The camera returns to player control after 30 seconds; ordinary launches never enable the tour. The raw recording and diagnostics are saved in `artifacts/showcase/`.

Run `python src/tools/bfme_host/finish_showcase.py` after the recorder finishes to export the video without added captions as `artifacts/showcase/bfmeXbar-gameplay-showcase.mp4`. The completed showcase is 29 seconds of continuous gameplay at 30 fps, with no audio.
