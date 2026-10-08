# Repository layout

bfmeXbar keeps the strategic extension, map projects and showcases in one
repository. Reusable Python code lives in `src/bfmexbar`. Project-specific
geometry, armies, camera shots and editorial choices live beside their project.
The game installation and adjacent openbfme2 checkout remain read-only inputs.

The root contains seven folders and one main launcher:

```text
projects/       Strategic patch, maps, scenarios and showcases
src/            Shared Python/native code and archived experiments
scripts/        CLI, setup, configuration and specialized launchers
tests/          Unit, integration and native checks
docs/           Documentation and license notices
runtime/        Ignored local game runtime
artifacts/      Ignored generated maps, videos and reports
Launch bfmeXbar.cmd
README.md
pyproject.toml
LICENSE.txt
```

Map/battle shortcuts and the setup shortcut are in `scripts/launchers/`.
Compatibility Python modules now live under `src/tools/`; the old root `tools/`
directory is gone. Use `scripts/bfx.py` for current commands, or install the
checkout in editable mode when using the older `tools.*` module imports.

## Ownership

| Directory | What belongs here |
| --- | --- |
| `projects/strategic/` | Native camera, picking and symbols; default multipliers; supported executable fingerprint |
| `projects/maps/<map>/` | Map generator, geometry, materials, scenery, references and design notes |
| `projects/scenarios/<scenario>/` | Factions, armies, buildings, teams, deployment anchors and random seed |
| `projects/showcases/<showcase>/` | Camera shots, chapter titles, original score, edit template and export profiles |
| `src/bfmexbar/host/` | Game launch, isolated runtime preparation and integration with openbfme2 |
| `src/bfmexbar/strategic/` | Extension compilation, injection and camera diagnostics |
| `src/bfmexbar/formats/` | BIG archives and native map decoding/encoding |
| `src/bfmexbar/mapkit/` | Reusable terrain operations, map cache, authoring CLI and validation |
| `src/bfmexbar/scenarios/` | Terrain-checked placement, native army staging and battle validation |
| `src/bfmexbar/capture/` | Camera orchestration, native recordings and map photography |
| `src/bfmexbar/video/` | FFmpeg execution, full-decode validation and size-constrained exports |
| `src/native/common/` | Shared 32-bit ABI types |
| `src/native/scenarios/` | Native spawning and order execution |
| `src/native/capture/` | Native frame capture and camera director |
| `scripts/` | Supported Python and PowerShell entry points |
| `tests/unit/`, `tests/integration/`, `tests/native/` | Fast tests, FFmpeg round trips and instructions for actual game checks |
| `docs/licenses/` | Existing project and third-party notices |
| `src/legacy/` | Browser and Recoil experiments |
| `src/tools/`, `src/native/host/` | Compatibility entry points for existing commands and imports |

The native features still compile into one DLL with the existing exported ABI.
Moving a source file does not require adding a second injected DLL. The include
order in `projects/strategic/native/strategic.cpp` supplies the existing native
dependencies; the feature includes are not independent translation units.

## Python and local configuration

Python 3.11 or later is required. From a checkout with dependencies installed:

```powershell
python scripts/bfx.py --help
```

For an editable installation in this checkout's own environment:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[video]"
.\.venv\Scripts\bfx.exe --help
```

This is a checkout-based toolset. Map projects, showcase templates and native
sources are loaded from the checkout, not bundled into a standalone game mod
wheel. `bfmexbar.projects.maps.eight_kingdoms.build`, for example, loads the one
canonical `projects/maps/eight-kingdoms/build.py` file. No duplicate generator is installed
under `src`.

Copy `scripts/config.example.toml` to ignored `scripts/config.local.toml` when installation
paths differ. Relative paths resolve against the checkout, independently of the
current working directory. `BFMEXBAR_ROOT` can explicitly select a checkout.
`scripts/setup.ps1` creates its own environment; it does not install into the
original repository's environment. Existing runtime manifests retain their
configured game locations until setup is run again.

## Commands

```powershell
# Strategic extension and normal play
python scripts/bfx.py mod build
python scripts/bfx.py play --window --strategic
python scripts/bfx.py play --eight-kingdoms

# Rebuild a map and retain a separate output run
python scripts/bfx.py map build eight-kingdoms --run-id terrain-001
python scripts/bfx.py map inspect "path/to/map.map"

# Prepare or play the battle without recording
python scripts/bfx.py scenario plan eight-kingdoms-4v4
python scripts/bfx.py scenario play eight-kingdoms-4v4

# Record, then edit that exact capture
python scripts/bfx.py showcase capture eight-kingdoms --run-id r005
python scripts/bfx.py showcase edit eight-kingdoms --run-dir artifacts/showcases/eight-kingdoms/r005

# Export an existing video below 20,000,000 bytes
python scripts/bfx.py video "path/to/trailer.mp4" --output "path/to/trailer-under20mb.mp4" --profile under20mb
```

Map builds install the generated map into the isolated runtime, as before.
Capture starts the actual game and closes its own test session when complete.
It needs the prepared runtime, the compiled extension and the Eight Kingdoms map.
The Eight Kingdoms editor also uses the existing rendered map portrait configured
in `projects/showcases/eight-kingdoms/project.toml`; render that photo before editing on a
fresh checkout.

`scenario.toml` currently selects the supported Eight Kingdoms eight-player
adapter. The adapter requires slots 1–4 versus slots 5–8. Templates, placements,
shot lists and titles are editable data; new team arrangements or different
native capture dimensions require a corresponding adapter change. The current
edit template uses six-second opening and closing cards at 30 fps.

## Generated files

```text
runtime/                              # Ignored game copy, profile, DLL and scratch state
artifacts/
  projects/maps/eight-kingdoms/<build-id>/
    manifest.json
    map/                              # Native map, sidecars and package
    previews/
    validation/
    tour.json                         # Native inspection/photo configuration
  projects/scenarios/eight-kingdoms-4v4/<run-id>/
    manifest.json
    battle-plan.json
  projects/showcases/eight-kingdoms/<run-id>/
    manifest.json
    capture/                          # Battle plan, live state and raw frames
    intermediates/                    # Compressed footage, score, edit segments, logs
    exports/                          # Master/mobile MP4s and trailer metadata
    validation/                       # Native battle and video export checks
```

New run IDs cannot overwrite existing runs. Completed showcase runs cannot be
edited again through the CLI; start another run for a new revision. The generic
video command refuses an existing destination and publishes its temporary output
only after validation succeeds. Run manifests record Git state, source hashes
including untracked project sources, and the map hash when available.

The original `artifacts/eight-kingdoms/` videos and revision folders stay at their
existing paths. Old tool entry points retain their historical output locations.
New `bfx` workflows use the layout above. Raw 1600×720 BGRA recording is about
8.8 GB for 64 seconds; retain the compressed footage and validation before
removing that temporary raw file.

## Checks

```powershell
python -m unittest discover -s tests/unit -t . -q
python -m unittest discover -s tests/integration -t . -q
node tests/test_worldbuilder_session.mjs
python scripts/bfx.py mod check --map "maps\map mp bfmexbar eight kingdoms.map"
```

Legacy named Python test modules forward to `tests/unit`. Use the commands above
to avoid discovering the compatibility modules twice. The WorldBuilder JavaScript
test uses a mock client; it does not claim a live editor check. Native capture
validation verifies combat and recording, not multiplayer balance or long-match
performance.
