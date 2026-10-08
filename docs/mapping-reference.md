# Mapping reference and coverage

This is the index of what the workshop knows about **BFME II 1.06 maps**:
their binary structure, authoring constraints and dependencies on game data.
It is not yet a complete semantic specification. Operating WorldBuilder is not
required to investigate these rules; source analysis, retail-file comparisons
and controlled engine tests provide different kinds of evidence.

Start with [map-file structure](map-format.md) for the container and terrain
planes, [terrain records](worldbuilder-terrain.md) for blends and cliffs, and
[heightmap authoring](heightmap-workflow.md) for image import. The
[creation workflow](map-creation-workflow.md) connects those to map builds.
This page tracks coverage and documents the additional record layouts.

## Project target

Understand the BFME2 mapping system well enough to create original maps from
scratch and use its supported capabilities deliberately. This includes the map
file, referenced assets and definitions, runtime interpretation and packaging.
Compatibility initially targets the unmodified **BFME2 1.06 engine**; features
requiring the workshop extension must be identified separately. Other patches
and expansion games need their own validation.

“Arbitrary maps” means arbitrary authored designs within the engine's supported
features and limits. It is not a promise of unlimited dimensions or arbitrary
new mechanics. Discovering those limits is part of the work.

For each capability, track five separate deliverables:

1. **Read:** versioned layout, raw-value preservation and representative files.
2. **Understand:** field meanings, units, legal values, references and interactions.
3. **Write:** original authoring support, independent of donor-map geometry.
4. **Validate:** a small native example with recorded inputs, expected and
   observed behavior, structural checks and the exact map hash.
5. **Document:** a usable example and explicit compatibility/limitation notes.

| Workstream | Capabilities to cover | Completion evidence |
| --- | --- | --- |
| Document and packaging | Sections, properties, sidecars, assets, map-local configuration, discovery/cache | New document loads through normal game entry points; unknown data survives safe edits |
| Terrain and presentation | Heights, materials, blends, cliffs, water, shores, lighting, weather/environment, cameras | Small feature maps and mixed-feature cases rendered by BFME2 |
| Navigation and placement | Terrain flags, slopes, roads, bridges, layers, collision, buildability, footprints | Movement/building-placement cases for relevant unit types and formations |
| Players and economy | Starts, ownership, diplomacy, resources, settlements, creeps, victory/defeat | Original skirmish scenarios work for the declared player configurations |
| AI | Build lists, bases, attack priorities, routes, recruitment and scripted teams | AI demonstrates intended behavior over a sustained match |
| Scripting and scenarios | Conditions/actions, timers, counters, references, reinforcements, objectives, cinematics and supported script/config hooks | Original minimal scenarios execute each claimed behavior, including failure/false branches |
| Compatibility and limits | Stock-engine use, multiplayer, save/load, performance and patch differences | Repeatable integration tests; extension-dependent cases labelled separately |

The first milestone is a reproducible capability inventory. The next is a library
of small original feature maps, followed by a combined scenario to expose
interactions that isolated tests miss. A blank skirmish load or screenshot alone
does not close the AI, scripting, multiplayer or performance workstreams.
The screenshot harness is evidence tooling; map compatibility must not silently
depend on its camera/reveal/scenario helpers.

## What the coverage means

The read-only audit on 8 October 2026 examined all **67 `.map` entries** in the
local BFME2 `Maps.big`: **22 top-level section names, 25 section/version pairs**.
Every container re-encoded to identical **decompressed** bytes. This does not
prove that opaque payloads were understood or that edits would behave correctly.

In the table, **decoded** means the implemented layout consumes the payload
exactly. **Partial** means useful fields are decoded but unknown fields or nested
payloads remain. Neither term certifies every engine rule. Versions not listed
are outside this audit. Optional sections absent from the corpus may still be
legal; this is not a whitelist of everything the engine can read.

| Section | Version | Maps | Current coverage |
| --- | ---: | ---: | --- |
| HeightMapData | 5 | 67 | Decoded; dimensions, borders, elevations |
| BlendTileData | 18 | 66 | Partial; all layouts consumed, Rhûn's 711 out-of-palette samples reported without normalization |
| BlendTileData | 14 | 1 | Read-only legacy layout decoded; modern authoring guards remain |
| WorldInfo | 1 | 67 | Decoded typed properties; property meanings depend on engine consumers |
| ObjectsList | 3 | 67 | Decoded Object v3 children; template behavior is external |
| MPPositionList | 0 | 67 | Decoded MPPositionInfo v0/v1 children |
| SidesList | 6 | 67 | Partial; leading boolean unresolved; embedded build lists decoded |
| Teams | 1 | 67 | Decoded property dictionaries |
| LibraryMapLists | 1 | 67 | Decoded LibraryMaps v1 children |
| PlayerScriptsList | 1 | 66 | Partial semantics; full stored hierarchy and arguments decoded, opcode behavior still under investigation |
| PlayerScriptsList | 5 | 1 | Stored hierarchy decoded, including Script v2 / Action v2 / Condition v4; semantics partial |
| BuildLists | 1 | 67 | Decoded BFME faction lists; nonempty entries source/synthetic tested only |
| TriggerAreas | 1 | 66 | Partial; polygons decoded, trailing integer unresolved |
| PolygonTriggers | 5 | 1 | Legacy layout decoded; retail example empty, nonempty layout synthetic-tested; semantics partial |
| StandingWaterAreas | 2 | 66 | Decoded polygons, height and material references |
| RiverAreas | 2 | 66 | Decoded cross-sections and water parameters |
| StandingWaveAreas | 2 | 66 | Partial; raw parameters retained alongside source-derived names |
| GlobalLighting | 8 | 66 | Full layout decoded and serialized; third light array and extension-field meanings partial |
| GlobalLighting | 7 | 1 | Same layout without the three v8 final values |
| PostEffectsChunk | 1 | 66 | Decoded effects, blend factors and lookup images |
| EnvironmentData | 3 | 67 | Decoded water alpha and macro/cloud texture settings |
| NamedCameras | 2 | 67 | Partial; bookmark fields include an unresolved float |
| CameraAnimationList | 3 | 66 | Partial; free/look tracks decoded, focal/interpolation semantics need verification |
| SkyboxSettings | 1 | 1 | Decoded transform and texture-scheme reference |
| WaypointsList | 1 | 67 | Decoded ID-to-ID links; positions live in ObjectsList |

The legacy combinations occur in `maps/shellmapbackup/shellmapbackup.map`.
Four maps have nonempty camera-animation lists and all four now decode. There
are **718 immediate script/group children in the modern maps**. The recursive
[script audit](map-scripts.md), now including the legacy file, decodes 3,340 scripts,
4,186 conditions and 10,254 actions. These counts do not establish complete opcode semantics.
All faction and embedded build lists in this corpus contain zero build entries;
passing them cannot establish real-world nonempty build-list compatibility.

Rhûn contains 711 primary-tile samples with IDs between 31501 and 31511 despite
a descriptor palette of 2432 subtiles. All 711 are outside the playable rectangle.
The read-only inspection consumes the terrain without dropping these values;
authoring operations still reject them. Their original intended meaning remains
unresolved. Do not clamp the IDs or label the retail map corrupt.

As of 9 October, every observed top-level section/version has a structural
decoder. This closes the corpus layout inventory, not all semantic, authoring
or runtime workstreams. Optional features absent from retail Maps.big still need
separate cases.

The expanded 9 October audit also includes **152 documents in `Bases.big`**
(150 `.bse` files and two `.map` files) and **51 in `Libraries.big`**. All 270
containers round-trip exactly, and every observed top-level section/version has
a decoder: **23 section names and 43 section/version pairs** overall.
This is a local corpus result, not a completeness claim for every
legal BFME2 file. Base files add `CastleTemplates v1–5`, real faction/side build
lists and additional legacy variants. See [bases and libraries](map-bases.md).

Reproduce from an installed workshop environment:

```powershell
.\.venv\Scripts\python.exe -m bfmexbar.mapkit.coverage `
  'C:\path\to\BFME2\Maps.big' `
  --out artifacts/worldbuilder-analysis/coverage.json
```

The report includes each map's hash, independent section results, unsupported
reasons and exact container round-trip status. One section's failure does not
hide the rest of the map. It exports no retail maps. The separate
`bfmexbar.mapkit.terrain_audit` command inventories detailed terrain records.

## Authoring rules and their limits

| Area | Rule or constraint | Evidence / limit |
| --- | --- | --- |
| Container | Keep chunk versions, lengths and name IDs consistent; preserve unknown payloads and their referenced IDs. | Parser and exact retail round-trips; byte preservation is not semantic editing support. |
| Primitives | Numbers are little-endian. Chunk names use variable-length UTF-8 lengths; record strings use uint16 byte lengths and CP1252. Property type 4 uses UTF-16LE character counts. | Current BFME layout; do not substitute one string encoding for another. |
| Properties | uint16 count; each key is byte type plus three-byte name ID. Types 0/1/2 are byte bool/int32/float32; 3/5 narrow strings; 4 wide string. | Known type layout; legal property names and effects are open-ended engine inputs. |
| Terrain coordinates | One XY sample step is 10 world units; sample coordinates are `(worldX / 10 + border, worldY / 10 + border)`. Elevation is uint16 × 0.0390625. | Source, retail measurements and authored native tests. |
| Heights and limits | The storage range is 0–2559.9609375 world units. Writer bounds and dimension guards are tool policy, not proven engine maximums. | uint16 representation; native loading of particular large maps does not establish a universal size limit. |
| Resizing | Height samples and all eleven texture/flag planes must agree; bits are padded per row. Transform spatial records, including script coordinates if present. | Binary layout; refuse transformations of unresolved coordinate-bearing payloads. |
| Textures | Resolve palette names through installed terrain definitions. Preserve 2×2 subtile ordering and native tile scale. Zero blend/cliff index means no record. | Retail layouts and native authored texture checks; see terrain reference for record counts and seams. |
| Objects | Resolve template names through Object, ChildObject and ObjectReskin definitions. Object Z is a terrain-relative offset; orientation is radians. | Source and native placement observations. Model footprint, collision and LOD come from game data. |
| Starts | Our skirmish writer emits distinct `Player_1_Start` through `Player_N_Start`, N=2–8, with unique waypoint IDs. | Tested authoring convention; eight MP-position slots do not imply eight active players. Campaigns differ. |
| Ownership | Keep owner/team references valid and per-side library/script entries aligned when adding or removing sides. | Known schemas and generated-map loads; side count includes neutral/faction roles. |
| Paths | Waypoint links reference waypoint IDs; road/bridge endpoint objects have separate flags. Texture-painted roads do not establish routing. | Record structure; destructible bridge logic and traversal need engine-specific evidence. |
| Water | Transform polygons and river cross-sections in XY; decide water heights separately. Shore-wave geometry is separate. | Decoded layout; water appearance does not prove impassability or a usable ford. |
| Clearance | Terrain flags, slopes, object collision, locomotors and formation size jointly affect movement/building placement. | No verified universal slope threshold or corridor width for all units. |
| Bounds | Border scenery, off-map spawns and camera bookmarks may lie outside playable bounds. | Retail examples; do not clamp all coordinates indiscriminately. |
| Discovery | Installed maps need matching discovery/cache data and start counts; update paths, byte counts and extents after edits. | Tested isolated file-launch path; exact EA checksum equivalence and all menu/network paths remain unverified. |
| Validation | Check structure, resolve referenced assets, then test relevant engine behavior with a recorded map hash. | Native load/screenshots prove the tested views, not combat balance or multiplayer compatibility. |

A concept image's labels are design intent. For example, “forest slows units”
does not automatically create a native movement modifier when trees are placed.
Likewise, map bytes do not contain all game rules: INI definitions, scripts,
object modules and the executable determine much of the result.

## Additional record layouts

Notation: `u8/u16/u32/i32/f32` are fixed-width values; `str` is a uint16 byte
length followed by CP1252 bytes; `vec2/vec3` are two/three f32 values. `props`
is the property dictionary above. Counts are u32 unless explicitly stated.
Each decoded collection must consume exactly its payload, with no trailing bytes.

### Players, build lists and links

- `Teams v1`: count, then `props` per team.
- `SidesList v6`: unresolved u8 boolean, player count; each player has `props`,
  embedded build-entry count and entries in the layout below.
- `BuildLists v1` (BFME): faction count; each faction has a property key
  (`u8 kind + 3-byte name ID`), entry count and entries. Other SAGE games can
  use different layouts even with this version number.
- Build entry: `str buildingName, str template, vec3 position, f32 angle,
  u8 initiallyBuilt, u32 rebuilds, str script, i32 health,
  u8 whiner, u8 unsellable, u8 repairable`. Source interprets `0xffffffff`
  rebuilds as unlimited; runtime behavior and `whiner` remain unverified here.
  Do not confuse this record with the larger savegame/persistence structure.
- `MPPositionList v0`: nested `MPPositionInfo` chunks. Child v0 contains
  `u8 human, u8 computer, u32 team`; v1 inserts `u8 loadAI` before team and
  appends a restriction count and that many side-name strings.
- `LibraryMapLists v1`: nested `LibraryMaps v1`, each containing a count
  followed by map-name strings. `PlayerScriptsList v1` instead holds ScriptList
  chunks; the [script reference](map-scripts.md) describes their nested records
  and stored operands. Runtime interpretation is a separate investigation.
- `WaypointsList v1`: count, then `(i32 startID, i32 endID)` per link.

### Trigger and water geometry

- `TriggerAreas v1`: count; each record is `str name, str layer, u32 id`,
  point count, vec2 points and one unresolved u32.
- All water v2 collections start with a count. Each record begins
  `u32 id, str name, str layer, f32 uvSpeed, u8 additive`.
- Standing water continues with `str bumpTexture, str skyTexture`, point
  count, vec2 points, `u32 waterHeight, str shader, str depthColors`.
- River continues with four strings (texture, noise, alpha edge, sparkle),
  four color bytes, `f32 alpha, u32 waterHeight, str minLOD`, cross-section
  count and four f32 XY endpoint values per cross-section.
- Standing waves continue with point count, vec2 points, unresolved u32,
  nine u32 parameters, `str texture, u32 enablePCA`. The nine source names are
  final width/height, initial width/height fraction, initial velocity, time to
  fade/compress, second-wave offset and distance from shore. Preserve their
  raw integer values; source names alone do not establish units or ranges.

### Environment and lighting

- `EnvironmentData v3`: `f32 waterMaxAlphaDepth, f32 deepWaterAlpha,
  u8 macroTextureStretched, str macroTexture, str cloudTexture`.
- `PostEffectsChunk v1`: **u8 count**, then `str name, f32 blendFactor,
  str lookupImage` per effect. An empty payload is one zero byte, not four.
- `GlobalLighting v7/v8`: u32 time of day; four configurations of nine light
  records; **f32 overbright**, u32 flag, three vec3 values, u32 shadow color;
  v8 appends three f32 final values. Each light is ambient RGB, diffuse RGB and
  direction XYZ. Total size: v7 1348, v8 1360 bytes. The native order is terrain
  sun, object sun/fill 1/fill 2, terrain fill 1/fill 2, then three lights in a
  third array whose role remains unresolved. Do not label it infantry without
  further evidence. [Lighting details and tests](map-lighting.md).
- `SkyboxSettings v1`: `vec3 position, f32 scale, f32 rotation,
  str textureScheme`.

### Cameras

- `NamedCameras v2`: count; each is `vec3 lookAt, str name`, then six f32:
  pitch, roll, yaw, zoom, field of view and an unresolved value.
- `CameraAnimationList v3`: count; each animation has a four-byte type,
  name, u32 frame count and u32 start offset, followed by a camera track.
  Type `look` also has a target track. Disk bytes are reversed four-character
  codes: `eerf` means `free`, `kool` means `look`.
- Each track: keyframe count; each frame has u32 frame index, interpolation
  code (`mtac` → `catm`, `enil` → `line`) and vec3 position/target.
  Free camera frames add four rotation floats and one focal/FOV parameter;
  look camera frames add roll and the focal/FOV parameter. Target frames add
  neither. The layout is tested; exact interpolation and focal interpretation
  are not yet established by this project.

These layouts are implemented in
[`analyze.py`](../src/bfmexbar/mapkit/analyze.py), cross-checked with
[OpenSAGE map sources](https://github.com/OpenSAGE/OpenSAGE/tree/master/src/OpenSage.Game/Data/Map),
[BuildListInfo](https://github.com/OpenSAGE/OpenSAGE/blob/master/src/OpenSage.Game/Logic/Map/BuildListInfo.cs)
and [SidesList](https://github.com/OpenSAGE/OpenSAGE/blob/master/src/OpenSage.Game/Logic/Map/SidesList.cs).
They are independent of whether an editor UI can be automated.

## Remaining work, in priority order

1. **Scripts:** the stored hierarchy and arguments now decode across all 67
   retail maps. Establish BFME2 opcode meanings and argument constraints,
   group activation, difficulty flags and timing. A typed writer, complete named
   template catalogue and twelve-script native lab now exist; the wider opcode
   behavior and scenario authoring work remains open. Spatial edits must account for
   coordinate arguments and named references. Campaign payloads provide cases
   that empty skirmish scripts cannot cover.
2. **Terrain exceptions and behavior:** resolve the intended meaning of Rhûn's
   border-only primary IDs, custom edge tables and arbitrary adjoining cliff/three-way seams.
   v14 terrain now has read-only layout support, not an authoring implementation.
   The existing [native terrain experiment](worldbuilder-terrain.md#isolated-native-experiment)
   demonstrates rendering effects, not a general projection algorithm.
3. **Gameplay constraints:** establish movement/buildability flag precedence,
   slopes and formation clearance for infantry, cavalry, siege and monsters;
   road/bridge flags, layers, destruction/rebuilding, AI base and rally footprints.
   Use controlled native cases, not visual similarity as evidence. The
   [corridor experiment](map-navigation.md) now measures path queries and
   scripted traversal for four unit types across selected terrain flags, water
   depths and height-only slopes. Tested integer water depths 5/6 straddle a
   passability boundary, while unflagged height ridges up to about 87° remain
   traversable. These do not settle placement, manual orders or other locomotors.
4. **Remaining fields and variants:** legacy runtime behavior, lighting's third
   array and extension-field meanings, camera unknowns, SidesList's leading byte, trigger/wave unknowns
   and optional sections outside this corpus. Validate nonempty build lists and
   edge tables against representative files or engine tests.
5. **Integration limits:** menu discovery, cache checksum rules, multiplayer
   transfer/hash agreement and sustained large-map performance.

A section is not complete merely because it round-trips. Completion requires
version-specific, bounds-checked decoding; nonempty test cases; evidence for
field units and references; and relevant engine tests for behavioral claims.
Until then, retain unknown values and label the limitation. The coverage report
deliberately has `semantics_complete: false` instead of a misleading percentage.
