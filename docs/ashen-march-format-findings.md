# New native BFME2 map: technical findings

Work log, 8 October 2026. Scope: the verified BFME2 1.06 executable used by bfmeXbar. These findings are not a claim of universal SAGE compatibility.

## From-scratch document construction

`tools/worldbuilder/blank.py` constructs a fresh name table and all 20 top-level chunks. It does not open a donor map. `ashen.py` adds original coordinates, elevations, materials and objects. Installed game assets supply meshes and textures, not a landscape layout.

The `00-empty.map` checkpoint contains a uniform 100-unit plane, one terrain texture and no objects, water, roads or custom scripts. `01-functional.map` adds exactly two start waypoints. Checkpoints and hashes are in `runtime/worldbuilder/ashen-march/checkpoints/`. Native empty-map evidence is in `artifacts/ashen-march/01-functional/native-validation.json`.

**Observed:** the retail game loaded the new 840 × 950 playable-tile map, entered mode 2, advanced beyond 300 simulation frames, spawned both players, and rendered four distinct camera positions. The strategic extension reported zero faults; the original user profile was untouched. GDI window capture was blank, but direct D3D9 render-target captures were valid. A blank GDI image alone is therefore not evidence of a failed map load.

**Unverified:** WorldBuilder open/save round-trip. The computer-control helper failed during sandbox setup before it could connect to the editor. No editor operation is claimed.

## Container and name table

- An uncompressed native document starts with `CkMp`, then a little-endian uint32 string count.
- Name entries occur in descending index order, N through 1: 7-bit variable-length UTF-8 byte count, UTF-8 name, uint32 index.
- Chunk headers are uint32 name index, uint16 version, uint32 payload byte count. Nested chunks use the same header.
- Property dictionaries begin with uint16 count. Each field has a byte type and a **three-byte little-endian name index**. Types 0/1/2 are byte boolean, int32 and float32; types 3/5 use uint16-length CP1252 strings; type 4 uses uint16 character count followed by UTF-16LE.
- Name interning must finish before emitting the container header. A property encoder can add names while building payloads.
- Reparse plus byte-identical re-encoding is a useful structural check, but native loading remains necessary.

## Terrain

`HeightMapData` v5: four uint32 values (sample width, height, border width, border-record count), each border record contains two uint32 playable dimensions, then uint32 area and unsigned uint16 samples in row order. With one border record, the header is 28 bytes.

One sample step is 10 world units horizontally. Height is unsigned fixed point: stored sample × 0.0390625. A 30-sample border around 840 × 950 playable tiles produces a 900 × 1010 grid. Authored world coordinate (x,y) maps to sample (x/10+30,y/10+30). The original plane at 100 is stored as 2560. Map object Z is a terrain-relative offset, not the absolute sampled ground elevation.

`BlendTileData` v18 stores uint32 area followed by full-grid arrays: primary tile uint16; blend, three-way blend and cliff index uint32 each. Next are row-padded bit planes for impassability, impassability to players, passage widths, taintability and extra passability; byte-per-tile flammability; and a row-padded visibility bit plane. Bit packing is least-significant-bit first, with ceil(width/8) bytes per row.

The tail begins with uint32 texture-cell count, blend count, cliff count and texture count. A texture descriptor is four uint32 fields (cell start, count, side length, zero) followed by its terrain INI name. A 4 × 4 texture-cell grid contains 64 terrain subtiles. Their ordering is **2 × 2 subtiles within each texture cell**, not an ordinary 8 × 8 raster:

```python
4 * (((y // 2) % size) * size + (x // 2) % size) + (y % 2) * 2 + x % 2
```

Two uint32 zero fields follow the texture descriptors. Index zero means no blend; the payload contains blend_count−1 records. Each is 18 bytes: secondary tile uint32, four direction bytes, flags byte, two-sided byte, uint32 legacy value and uint32 0x7ADA0000. The constructor uses 0xFFFFFFFF for the legacy value. Cardinal direction bytes and flip bit are encoded using the OpenSAGE definitions. Native appearance of the new transitions is checked during the material pass. No cliff UV records are currently generated; steep terrain uses ordinary textured geometry.

The authoring grid explicitly blocks steep faces and high rocky slopes. Route sampling is only a terrain consistency check. It does not prove native battalion clearance, object collision clearance, AI quality or multiplayer balance.

## Players, scripts and objects

- `SidesList` v6 begins with byte 1, uint32 player count, then player property dictionaries and uint32 embedded build-list counts. The new map uses neutral/civilian/creep entries, six skirmish factions and two player slots.
- Each player has a singleton team. Empty per-player `LibraryMaps` v1 and `ScriptList` v1 child chunks are sufficient for the tested native skirmish load. No stock Gollum library or scenario scripts are imported.
- `MPPositionInfo` v1 uses three booleans (human, computer, load AI), uint32 team and uint32 restriction count. The new document writes eight available position descriptors; only two start waypoints are supplied.
- `ObjectsList` v3 contains `Object` v3 children. Payload: x/y/z/angle float32, flags uint32, template string, property dictionary. Newly authored scenery uses flags 0 and explicit default properties; no prototype record is copied.
- `*Waypoints/Waypoint` objects named `Player_1_Start` and `Player_2_Start`, with unique integer waypoint IDs, were sufficient to establish player starts. No `SkirmishSpawnPoint` objects were needed for the verified file-launch skirmish.
- Empty trigger, water, camera-animation and waypoint-path lists are uint32 zero. Empty objects and script children have zero-length payloads. Empty `PostEffectsChunk` v1 uses a **single zero byte**, not uint32 zero.

## Lighting and environment

`GlobalLighting` v8 is 1360 bytes. It contains uint32 time-of-day, four sets of nine lights, a packed shadow color, 44 legacy bytes and three no-cloud-factor floats. Each light is nine float32 values: ambient RGB, diffuse RGB, direction XYZ. Within each time set, the sequence is terrain/object/infantry for sun, then the same three for accent 1 and accent 2.

The new map encodes all values explicitly. Its cool ambient fill and subdued warm key are original art settings. The 44-byte legacy section uses conservative values observed in installed documents; its full semantics remain unresolved. This section is not described as decoded merely because the game accepts it.

`EnvironmentData` v3: water alpha-depth float, deep-water alpha float, macro-stretch boolean, macro texture string and cloud texture string. These engine asset references contain no spatial layout. The new map uses existing noise/cloud textures.

## Map discovery and testing

The isolated mod needs a matching `MapCache` entry marked multiplayer with two starts. The actual map file lives at `maps/<name>/<name>.map`, but the tested native command uses the short virtual path `maps\\<name>.map`. Forgetting the cache entry can put a file launch into shell behavior instead of the intended skirmish.

The current cache writer uses zlib CRC32, matching the existing working local authoring path. Equivalence to every original EA cache checksum remains unproven. Full paths, byte counts and extents are regenerated after installation.

Native QA uses the existing extension's opt-in render-target readback and persistent camera controls. Repeated native LookAt updates are necessary for reliable focus movement. The test records actual camera focus along with the requested view. A running game must exit fully before restarting or replacing its loaded extension.

## References and implementation provenance

Container and chunk layouts were cross-checked against [OpenSAGE map sources](https://github.com/OpenSAGE/OpenSAGE/tree/master/src/OpenSage.Game/Data/Map), particularly [GlobalLighting](https://github.com/OpenSAGE/OpenSAGE/blob/master/src/OpenSage.Game/Data/Map/GlobalLighting.cs), [GlobalLightingConfiguration](https://github.com/OpenSAGE/OpenSAGE/blob/master/src/OpenSage.Game/Data/Map/GlobalLightingConfiguration.cs), [BlendTileData](https://github.com/OpenSAGE/OpenSAGE/blob/master/src/OpenSage.Game/Data/Map/BlendTileData.cs) and [EnvironmentData](https://github.com/OpenSAGE/OpenSAGE/blob/master/src/OpenSage.Game/Data/Map/EnvironmentData.cs). Local schema caches are research material; generated maps are not copied from those sources. Existing licensing attribution remains in `native/THIRD_PARTY.md`.

## Material and scenery pass observations

The sculpted terrain and first scenery build both passed the four-view native test. The initial scenery build contained 1,181 records. Review revealed visual issues that a structural parser could not detect:

- BFME2 substitutes a global low-LOD tree model at distance. Merely placing `TreeDead01`/`TreeDead02` does not guarantee a deadwood silhouette at strategic camera heights. The map-local `AIData / LowLodTreeName = TreeLowLODMordor` setting addresses the unwanted green-tree substitution.
- Terrain textures are mostly in `Terrain.big`, not just `Textures*.big`. The palette contact sheet must search both archive families. All nine selected terrain images measured 256 × 256, matching 4 × 4 texture cells. A stock Mordor tile sequence independently confirmed the constructor's 2 × 2 subtile ordering.
- Native asset declarations include `ObjectReskin` as well as `Object` and `ChildObject`. A catalog that omits reskins wrongly reports valid dead-tree templates as missing. Placement now validates against all three declarations.
- Valid material transitions can still look too abrupt when adjacent colors differ greatly. The first road was too chalky and the soil patches too contrasting. The final palette moves these closer in tone. The writer currently generates cardinal, one-cell directional transitions; it does not claim to implement every WorldBuilder corner/three-way painting behavior.
- `DarkRockGrey` assets appeared too pale in the authored lighting. Mordor rock clumps better match the intended scree. Template names alone are insufficient aesthetic evidence; native views decide the choice.
- Hand-authored low ruins were too small to carry the focal point at distance. Additional original building placements give the watch a stronger tower and ruined-hall silhouette.

The minimap `_art.tga` and `_pic.tga` images are freshly rendered diagnostic terrain artwork. They are not copied stock sidecars or claimed photographs. Native photographic evidence remains separate.

Placement validation also needs scene-level assertions. A generic spacing filter silently rejected the first tower location because nearby wall fragments had reserved it. The defining tower is now placed before optional pieces and its placement is mandatory. Native INI geometry exposed another misleading name: `GondorBuildingIthilien17` has only a 6 × 7.2 radius footprint and is essentially a narrow architectural fragment. It cannot stand in for a large ruined hall. The final watch uses a 190-unit-high `TowerHills_TowerA` and larger `OsgiliathRuin01/02` footprints. These are original placements of existing models.

Subsequent checkpoint writes preserve a changed previous map in a hash-named `history` file. The camera-tour configuration carries the generated map's SHA-256 into the native validation report. Earlier exploratory reports predate that metadata field; their recorded camera positions and image files remain evidence of those earlier passes, not a claim that every later map byte was already tested.

## Final measured build

- 900 × 1010 stored samples, 840 × 950 playable tiles, border 30.
- Height range: 84.0625 to 1191.171875 world units.
- Nine terrain materials; 1,279 object records including two start waypoints.
- Three sampled route centerlines remain unblocked; the highest western route reaches approximately 261 units.
- Four native views passed, including the visible tower landmark and corrected dead-tree LOD. Extension faults: zero. Original profile changes: none.
- 35 project tests passed, including four new constructor invariants.
- Tested map SHA-256: `cc5803e6917baa36d0e681a9ce922ad42a83c3301835fcca59e24dc8bd42797a`.

The evidence report is `artifacts/ashen-march/polish/native-validation.json`. These checks establish native loading/rendering and authoring consistency, not full horde pathfinding or multiplayer balance.

The final native portrait also completed: 60 render-target tiles, 8,000 × 8,000 output pixels, 70-degree camera elevation (20 degrees off vertical), zero extension faults and no upscaling. `artifacts/ashen-march/photo/capture.json` records the capture. The JPEG is approximately 23.6 MB and the lossless PNG 78.8 MB. All tiles use the same fixed projection; the simulation advances between tiles, so this is a landscape portrait rather than a synchronized battle photograph.

The map was then launched interactively with Mordor as the human faction, Elves as the AI, revealed terrain and strategic controls. This verifies the new launch preset independently of the screenshot-only runs.
