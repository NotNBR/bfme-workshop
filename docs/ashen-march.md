# The Ashen March

An original large battlefield on a ruined Gondorian frontier beneath Mordor's shadow. Built from a new native document, not by resizing or stripping an existing map.

## Composition and intent

The landscape uses charcoal soil, worn tracks, pale broken masonry and occasional small fires. Long mountain spurs frame a broad diagonal battlefield. The Fallen Watch sits on an elevated shoulder overlooking its center. A sheltered deadwood basin gives the lower flank a different silhouette from the bare upland road.

The map is 840 × 950 playable tiles (8,400 × 9,500 world units), approximately three times Grey Mountains' playable area. Two generously cleared starts occupy opposing ends. The shorter central approach carries the main army; the longer western route offers elevation; the eastern route winds through lower ground. These are design intentions, not a claim of measured competitive balance.

## Revision 2: natural terrain and denser scenery

Following feedback about blandness and tiling, the map now uses domain-warped
gradient noise, rotated fBm octaves, ridged relief and thermal erosion around
the composed landforms. Clear routes and base footprints are restored after
erosion. The method does not simulate hydraulic drainage.

Scenery increased from 1,279 to **4,521 objects**: 1,764 trees in woodland pockets,
1,404 scree objects, 726 ground details, 309 more isolated trees, and 316 combined
ruins, settlement debris, boundary walls, watch pieces and start records.
Six settlement sites and six woodland regions replace the sparse first pass.

Ground uses quieter materials with smaller irregular patches and less contrast
between neighbouring soils. The macro texture is stretched across the map, and
the tracks are narrower and broken. Finite native textures still repeat; this
pass targets visible regularity rather than claiming a new terrain shader.
The [research and technical log](ashen-march-format-findings.md#revision-2-repetition-density-and-natural-terrain)
links the open algorithm references and records what was actually implemented.

## Painting passes and decisions

1. **Empty canvas.** Construct the native chunks explicitly. Save a uniform 100-unit plane with no objects. Add two start waypoints in a separate checkpoint. Run the empty document in BFME2 before investing in scenery.
2. **Composition studies.** Compare central obstruction, split spurs and transverse ridge. Select split spurs because it frames an open central battle while separating both flanks. These are diagnostic terrain studies, not game screenshots.
3. **Large forms.** Build overlapping ridges, shoulders and secondary spurs. Keep the interior lower than the perimeter. Revision 2 spans roughly 76–1,271 world units, with domain warping and thermal relaxation before route grading.
4. **Routes and ground.** Grade three routes at different elevations; feather their margins into slopes. Flatten broad construction space gradually to avoid circular cliff rings. Add a ramp to the watch. Refine angular road control points into curves after reviewing the first pass.
5. **Materials.** Inspect native texture artwork. Use nine palette slots (eight unique textures in revision 2) tied to slope, elevation, shelter and road wear, with directional blend records at region edges. Avoid lava because this is a ruined borderland, not a crater.
6. **Local scenes.** Compose the watch, broken enclosure, threshold statues and open approach. Align small ruin groups to former settlement streets. Concentrate dead trees in the basin and rock debris on mountain shoulders.
7. **Polish and correction.** Place rubble near ruins and ground detail in sheltered pockets. Review native images: change the pale road to darker worn dirt, reduce color contrast between soil patches, replace pale scree with Mordor rock, strengthen the watch silhouette and set the correct distant-tree model. Add original minimap art. Disable distance fog for strategic zoom.
8. **Native review.** Photograph four distinct locations through BFME2's renderer. Keep empty, terrain and final evidence separately. Do not treat an image or grid check as proof of full gameplay balance.

Checkpoints and hashes are in `runtime/worldbuilder/ashen-march/checkpoints`. Studies, native screenshots and build reports are in `artifacts/ashen-march`. Rebuilding is deterministic for the saved seed and generator version.

## Run and rebuild

Double-click **Launch Ashen March.cmd** for Mordor versus Elves with revealed terrain and strategic controls. This starts a normal skirmish on the new landscape. The Grey Mountains prepared battle remains its own preset.

```powershell
.venv/Scripts/python.exe -m tools.worldbuilder.ashen --phase polish
.venv/Scripts/python.exe tools/bfme_host/launch.py --ashen
```

Native map: `runtime/bfme-host/mod/maps/map mp bfmexbar ashen march/map mp bfmexbar ashen march.map`.

Four-view native verification:

```powershell
.venv/Scripts/python.exe tools/bfme_host/launch.py --window --map-check --map 'maps\map mp bfmexbar ashen march.map' --map-tour artifacts/ashen-march/tour.json
```

Use `--map-photo` instead of `--map-check` for the native 8K portrait. It tiles BFME2's renderer; the simulation continues between tiles.

Revision-2 portrait destination: `artifacts/ashen-march/revision-2/photo/The-Ashen-March-v2-8000.jpg`. Close views and their native validation report are in `artifacts/ashen-march/revision-2/`. The original portrait and first-release screenshots remain in `photo/` and `polish/` for comparison.

## Verification boundaries

Revision 2 contains 4,521 object records and nine terrain palette entries. Its
SHA-256 is `5cf6aa168c25b6bc06f8b80fb8fec7a3d507eb9d40362b4a7f6fad904cfdbd5e`.
The project's 38 automated tests pass. All four native camera views passed for
this hash, with zero extension faults and no original-profile changes. The native
report stores the tested map hash alongside its actual camera positions and screenshots.

Native reports record loading, distinct camera views, simulation advancement, extension faults and original-profile checks. Structural tests cover bit-plane padding, texture ordering, blend ranges, start identities, empty sections and invalid elevations.

WorldBuilder open/save remains unverified because its control helper could not initialize. The route checks establish continuous terrain corridors; full native horde traversal, prolonged AI play, network play and competitive balance need further playtesting.

See [technical and file-format findings](ashen-march-format-findings.md) for byte layouts, evidence and unresolved fields, and the [general map workflow](map-creation-workflow.md) for the reusable method.
