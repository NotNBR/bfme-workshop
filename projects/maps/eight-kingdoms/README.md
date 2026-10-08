# Eight Kingdoms

Canonical generator: `projects/maps/eight-kingdoms/build.py`. New builds: `python scripts/bfx.py map build eight-kingdoms`. See [repository layout](../../../docs/repository-layout.md).

An eight-player BFME2 battlefield following the supplied references: eight outer
kingdoms, winding waterways, mountain-framed shores, a raised central citadel and
two small sanctuary islands. The kingdoms occupy a 900 x 960 tile region covering
9,000 x 9,600 world units. Surrounding ocean expands the active map to 1,140 x 1,200
tiles. Twenty-four native stone bridges link the realms and their inner passes.
There are eight neutral outposts, eight warg lairs, two inns and a central signal
fire, with clear 550-unit construction circles at all starts.

## Play

Run **scripts/launchers/Launch Eight Kingdoms.cmd** in this worktree. It starts a standard native
skirmish: one human playing Men and seven easy AI opponents. Strategic zoom is
enabled. Normal fog, recruitment and faction economies remain active.

The generated map lives in
`runtime/bfme-host/mod/maps/map mp bfmexbar eight kingdoms/`.

`artifacts/eight-kingdoms/Eight-Kingdoms.zip` contains the map folder, map settings
and minimap artwork. This worktree's mod, profile and reports are separate from
the original checkout. The launcher reads the existing local BFME2 game assets.

## Prepared battle and trailer

The separate **scripts/launchers/Launch Eight Kingdoms Battle.cmd** preset stages a mid-game 4v4
battle. All eight slots have fixed starts and verified alliances. Each player
receives 12 native battalions, one hero and eight completed faction buildings:
96 battalions, eight heroes and 64 buildings across four fronts. The initial
battalions contain 1,548 members. Reinforcements receive staggered attack orders.
Each army also receives four heavy units, for 32 total: Ents, attack trolls,
cave trolls, mountain giants, trebuchets, catapults, ballistas and rams. Ranged
engines begin behind infantry; melee monsters enter from the forward flanks.
Buildings form uneven production clusters beside the approaches, with resource
buildings farther out and entrances oriented toward nearby routes. Each base
has a distinct seeded layout. Two fights take place around bases; two take
place on inland routes with a 1,250-unit exclusion zone for player buildings.
Army approaches and headings vary between fronts instead of repeating a grid.
Each battalion, hero and heavy unit receives a separate terrain-checked contact
lane, avoiding fortress footprints and rock props at the destination. Prepared
battles show one strategic marker per battalion; heroes and heavy units retain
their individual symbols. Visibility checks run before marker grouping.
The map file and normal skirmish launcher retain their existing behavior.

`artifacts/eight-kingdoms/trailer/Eight-Kingdoms-Trailer.mp4` is a 76-second,
1920 x 1080, 30 fps trailer. It combines a full-map title card, 64 seconds of
native battle footage, and a closing card, with an original synthesized score.
The footage is cropped to exclude the HUD and lightly brightened during editing.
The recorder suppresses the verified native hero-death notification wrapper
in its recording process so popups do not cover the action. Interactive play
keeps notifications enabled; the game binary on disk is never changed.
It portrays a prepared battle, rather than a match played from an empty base.
The four close battle scenes devote 16 seconds to base sieges and 16 seconds
to open-field fighting. Another 32 seconds show overhead strategic views and
continuous zooms between theatre and battle scales. These use the native
tactical symbol renderer, with icons fading out as the camera approaches.
Zooms use eased logarithmic scale changes, land exactly on the next shot, and
move closer to the siege engines and monsters. Chapter titles fade in and out;
the score's percussion and musical phrases follow the eight-scene edit.
The 720p `Eight-Kingdoms-Mobile.mp4` stays below the 10 MiB cloud upload limit.

To reproduce the capture and edit (requires `imageio-ffmpeg`):

```powershell
& ..\bfmeXbar\.venv\Scripts\python.exe src/tools/bfme_host/build_strategic.py
& ..\bfmeXbar\.venv\Scripts\python.exe src/tools/bfme_host/launch.py --kingdoms-trailer
& ..\bfmeXbar\.venv\Scripts\python.exe src/tools/bfme_host/finish_kingdoms_trailer.py
```

The native recorder temporarily writes about 8.8 GB of raw frames. The encoded
footage and trailer can be retained after removing the temporary `.bgr0` file.
Battle and export checks are recorded beside the video in
`battle-validation.json` and `export-validation.json`.
Native checks also record movement and battalion casualties at each of the
four fronts, heavy-unit orders and movement, and strategic frames with visible
symbols, including duplicate soldier markers collapsed into battalion markers.
Both delivery videos are decoded in full and checked for all 2,280 frames.
The master audio is checked against its loudness and true-peak targets before
export validation passes.

## Terrain authoring

The two reference images were supplied by NotNBR and confirmed as AI-generated
on 8 October 2026. See the [media provenance notes](../../../docs/licenses/README.md#media-provenance).

See the [heightmap workflow](../../../docs/mapping/terrain-and-presentation/heightmaps.md) for source-image
processing, grid orientation, native elevation precision and rebuild outputs,
and the [map-file structure](../../../docs/mapping/file-structure/format.md) for binary sections.

The source document begins as an empty native plane; no stock `.map` landscape
is loaded. `reference-height.jpg` supplies relative elevation and coastline
shape. The header/legend are excluded and small disconnected text fragments
are removed. Bright point markers are softened before elevation conversion.
The colored reference guides woodland groups and the landmark composition.

The native map uses 16-bit elevations. Erosion softens local slopes. Cleared
starts, curved routes, building foundations, bridge banks and underwater bridge
beds are authored separately. Native walk-on-wall bridge models supply deck
and ramp geometry. The grayscale image's shading is an artistic elevation guide.

The terrain plan and minimap are diagnostic cartography generated from the map
data. Native screenshots are kept separately as evidence of the game's appearance.
The detail palette uses green meadow and woodland textures, natural grey cliff
rock, scree below exposed slopes, shaded forest soil and snow on high, gentler
surfaces. Steep river banks use rock instead of grass. Native terrain projection
is retained; the custom cliff projection trial was rejected after a render check.

Dark natural boulders and smaller fragments form rockfall groups at cliff toes.
Leafy valley woods and evergreen foothill stands have undergrowth and sparse
fringes. Ruins, street-aligned buildings, broken boundaries and debris compose
small scenes around the neutral settlements. Each added scenery footprint is
checked for shoreline clearance and local relief; building plots can move locally
to find a sound foundation. Roads, approaches and starting circles remain clear.
`detail-placement.json` records placements and foundation checks. The two internal bridges are removed. Their gaps remain as irregular water-filled rocky hollows with sloping banks.

The native terrain grid grows to 1,200 x 1,260 samples. A 1,200-world-unit ocean
margin surrounds the original kingdom region inside the active boundary, with
another 30 border tiles beyond it. The original relief is retained apart from those two reshaped hollows;
all objects and test cameras receive the same 1,200-unit X/Y translation.
Scenery audit coordinates are local to the kingdom region; `build.json` records
the translation as `world_coordinate_offset`. No custom ocean model or shader is
required. The map is finite, so sufficiently distant or off-center views can
still reach its outer edge. Larger trials exceeded native graphics-memory limits and are not distributed.

## Rebuild

Run from this worktree with the existing project environment or a local venv
containing `src/tools/bfme_host/requirements.txt`:

```powershell
$py = '..\bfmeXbar\.venv\Scripts\python.exe'
& $py src/tools/bfme_host/prepare_eight_kingdoms.py
& $py -m tools.worldbuilder.eight_kingdoms
& $py -m unittest tests.test_eight_kingdoms tests.test_blank_map tests.test_worldbuilder tests.test_bfme_host -v
& $py src/tools/bfme_host/launch.py --eight-kingdoms --map-check --map-tour artifacts/eight-kingdoms/tour.json
```

The seeded generator saves empty, functional, terrain and detailed checkpoints,
retains superseded checkpoint hashes, validates the complete native document,
registers eight start positions and exports a map archive. `build.json` records
the reference SHA-256, map SHA-256, scenery counts and authoring-grid checks.

## Verification scope

The authoring-grid audit checks clear construction circles, all starts connected
through the intended bridge decks, reachable bridge banks and central access.
The native check loads BFME2, verifies eight instantiated player builder groups,
captures four locations and checks extension faults and the original profile.
It also orders two actual builders over horizontal and diagonal bridge spans,
recording positions across the decks and arrival on the opposite banks.
Measured outcomes are in `artifacts/eight-kingdoms/detail-pass/native/native-validation.json`.

The crossing probes cover individual builders on two bridges. They do not
establish all-bridge horde movement, prolonged AI performance, network play or
competitive balance. WorldBuilder open/save has not been verified.

## Recorded build

The finished build contains 3,731 object records and passed 29 automated tests.
BFME2 loaded the map, instantiated all eight player builder groups, rendered all
four camera views and completed both native builder crossing probes with no
extension faults or original-profile changes. The packaged map SHA-256 is
`f4d7f626bc2863adb86abddbea90b3545187b0d5570623090b8691218a0d21ea`.

The native tour and current 8K photograph include both reshaped internal
hollows. The photograph metadata records the matching map hash.
