# Agentic WorldBuilder workflow

For original maps starting from an empty plane, follow the
[rough-to-polished map creation workflow](../../docs/map-creation-workflow.md)
and its [worked design example](../../docs/map-workflow-example.md). The commands
below describe existing editing capabilities. The separate [Ashen March builder](../../docs/ashen-march.md)
now constructs a fresh native document and has passed a BFME2 empty-map loading test.
Its [format findings](../../docs/ashen-march-format-findings.md) distinguish native evidence from unverified editor behavior.

See [the native world-file analysis](../../docs/map-format.md) for measured section
layouts, dependency relationships, and the constraints on enlarging our maps.

This toolset lets an agent make reproducible bulk edits to a native BFME2 map,
then use WorldBuilder for visual refinement and its native save pass. The map
remains a normal `.map` document. Original maps and installed game files are
read-only inputs. Run commands from the bfmeXbar root using its Python venv.

## Current status

The binary reader, editor, previews and transaction/checkpoint tools run locally.
The WorldBuilder UI adapter is implemented but has **not been connected to a live
editor**: this session's Computer Use Node helper crashes during initialization.
Do not interpret a successful file parse or diagnostic preview as an editor or
game verification. A first native [Ithilien Frontier build](../../maps/ithilien-frontier/README.md)
now uses the measured format and has a separate native game verification workflow.

Supported: BFME2 HeightMapData v5, BlendTileData v18, Object v3. Unknown top-level
chunks are preserved byte-for-byte. Unsupported formats fail explicitly.
General-purpose resizing is not implemented. The dedicated `ithilien` builder
handles its verified source layout: water, borders, terrain, blend arrays, objects,
start positions and camera bookmarks. It refuses unhandled scripted coordinates.

## Fast authoring loop

1. `inspect` measures an existing map and validates terrain/texture references.
2. `catalog` returns exact texture and object names already available in it.
3. `checkout` makes an isolated editable copy, including native sidecar files.
4. Save and close that map in WorldBuilder before file edits; an unsaved document
   could later overwrite them. `status` supplies the saved file's SHA256.
5. `apply` accepts a seeded JSON recipe and that SHA256. It validates the entire
   result before replacing the working file. It retains before/after maps, the
   recipe, a chunk diff, and checkpoints. Reapplying a recipe is rejected.
6. `preview` produces a quick height/texture-category/objects diagnostic.
7. Open the working map in WorldBuilder, inspect, refine, save, then checkpoint.
8. `diff` checks exactly what the editor changed. Run the native game and verify
   crossings, starts, horde movement, camera coverage and battle frame rate.

```powershell
$py = '.\.venv\Scripts\python.exe'
$map = 'runtime/bfme-host/mod/maps/map wor ithilien/map wor ithilien.map'
& $py -m tools.worldbuilder.cli inspect $map
& $py -m tools.worldbuilder.cli catalog $map
& $py -m tools.worldbuilder.cli checkout $map ithilien-lab
& $py -m tools.worldbuilder.cli status ithilien-lab
& $py -m tools.worldbuilder.cli apply ithilien-lab maps/ithilien-frontier/authoring-demo.json --expect-sha <file_sha256>
& $py -m tools.worldbuilder.cli handoff ithilien-lab
& $py -m tools.worldbuilder.cli checkpoint ithilien-lab --note 'Saved and visually checked in WorldBuilder'
& $py -m tools.worldbuilder.cli diff <checkpoint.map> <working.map>
```

Checkpoint notes are user/agent descriptions, not proof that a native editor
check happened. `status` leaves the editor/game gates unverified. Keep actual
screenshots, save hashes and native match logs alongside the checkpoint before
claiming verification. Generated files live in ignored `runtime/worldbuilder`;
recipes and tooling belong in Git. A checkpoint can be branched with `checkout`.
There is no destructive restore command.

## Recipe operations

All XY positions/radii/spacing are **world units** (10 units per terrain tile),
relative to the playable area; angles use degrees in recipes. Heights are world
units. Map object Z remains the original terrain-relative donor offset.

- `raise`: `x`, `y`, `radius`, `amount`; smooth radial falloff, positive or negative.
- `flatten`: `x`, `y`, `radius`, `height`, optional `strength` (0..1).
- `paint`: `x`, `y`, `radius`, `texture` from the map's catalog. Repeats its native
  tile cells and clears old blends in that footprint. Edges need WorldBuilder's
  blend brush; this is a bulk base coat, not a finished texture transition.
- `scatter`: `template`, `count`, `rect: [x0,y0,x1,y1]`, `spacing`, `max_slope`.
  Uses existing unnamed scenery as a prototype; checks map bounds, painted
  impassability, slope, exclusions and minimum center distance from other objects.
- `place`: one existing unnamed landmark template at `x`, `y`, optional
  `angle_degrees`, `spacing`, `max_slope`. Preserves its properties and creates a
  fresh `uniqueID`. Does not clone scripted names, roads, waypoints or references.

Recipes have `schema: 1`, a unique lowercase `id`, `seed`, `operations`, and optional
`exclude_rects` protecting bases, lanes and crossings from scenery placement.
Insufficient valid positions abort the whole transaction. Center-distance and
painted passability checks do not replace native collision/pathfinding tests.
Existing water, script, team, camera and start chunks survive unchanged. Terrain
edits under water or existing structures require visual review.

## WorldBuilder UI adapter

Follow the installed `computer-use:computer-use` skill first, including its
guidance and confirmations. In its initialized `node_repl`:

```javascript
globalThis.WBClass = (await import('file:///D:/LAN/bfmeXbar/tools/worldbuilder/sky-session.mjs')).WorldBuilderSession;
globalThis.wb = new WBClass(sky);
nodeRepl.write(await wb.discover());
```

Inspect returned windows. In a separate call, `wb.attach(returnedId)` produces a
fresh screenshot and observation ticket. Inspect it. Then one `wb.act(ticket,
{type, reason, ...})` performs one action and immediately refreshes. Stop and inspect
again. Use accessible fields when available; coordinates must come from the current
screenshot. No stored coordinates, blind menu macros, guessed handles or shell UI.

Action types: `click` (element_index or x/y), `key` (key chord), `text` (text plus
focusConfirmed after inspecting focus), `value` (element_index/value), `drag`
(from_x/from_y/to_x/to_y), `scroll` (x/y/scrollX/scrollY). Failed input invalidates
the observation and records an unknown outcome; it never retries automatically.
`journal` records actions without screenshot payloads or typed content.

Open/Save operations are driven from observed menus/dialogs, not guessed hotkeys.
If a dialog is a separate window, rediscover and attach its returned id. Do not
report an editor save successful until the disk hash and map parse are checked.
If the helper cannot initialize, stop UI actions; continue only file operations.

## Three-times-area sizing

```powershell
& $py -m tools.worldbuilder.cli plan-size 'runtime/bfme-host/mod/maps/map mp grey mountains/map mp grey mountains.map' --area-factor 3
```

Grey Mountains measures 485 x 550 playable tiles (585 x 650 samples including its
50-tile border). Three times its area at the same proportions is approximately
840 x 953 playable tiles. This is a **proposal, not a supported-size claim**.
The editor and engine must be probed before committing the detailed map to those
dimensions. Three times each dimension would instead mean nine times the area.

## Format references

Layouts were cross-checked against [OpenSAGE's map parsers](https://github.com/OpenSAGE/OpenSAGE/tree/master/src/OpenSage.Game/Data/Map)
and the existing read-only openbfme2 MapObject writer. The bit planes are padded
per row, not across the whole map. See `native/THIRD_PARTY.md` for attribution.
