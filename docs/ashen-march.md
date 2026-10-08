# The Ashen March

An original large battlefield on a ruined Gondorian frontier beneath Mordor's shadow. Built from a new native document, not by resizing or stripping an existing map.

## Composition and intent

The landscape uses charcoal soil, worn tracks, pale broken masonry and occasional small fires. Long mountain spurs frame a broad diagonal battlefield. The Fallen Watch sits on an elevated shoulder overlooking its center. A sheltered deadwood basin gives the lower flank a different silhouette from the bare upland road.

The map is 840 × 950 playable tiles (8,400 × 9,500 world units), approximately three times Grey Mountains' playable area. Two generously cleared starts occupy opposing ends. The shorter central approach carries the main army; the longer western route offers elevation; the eastern route winds through lower ground. These are design intentions, not a claim of measured competitive balance.

## Painting passes and decisions

1. **Empty canvas.** Construct the native chunks explicitly. Save a uniform 100-unit plane with no objects. Add two start waypoints in a separate checkpoint. Run the empty document in BFME2 before investing in scenery.
2. **Composition studies.** Compare central obstruction, split spurs and transverse ridge. Select split spurs because it frames an open central battle while separating both flanks. These are diagnostic terrain studies, not game screenshots.
3. **Large forms.** Build overlapping ridges, shoulders and secondary spurs. Keep the interior lower than the perimeter. Elevation spans roughly 84–1,191 world units.
4. **Routes and ground.** Grade three routes at different elevations; feather their margins into slopes. Flatten broad construction space gradually to avoid circular cliff rings. Add a ramp to the watch. Refine angular road control points into curves after reviewing the first pass.
5. **Materials.** Inspect native texture artwork. Use nine materials tied to slope, elevation, shelter and road wear, with directional blend records at region edges. Avoid lava because this is a ruined borderland, not a crater.
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

## Verification boundaries

The finished build contains 1,279 object records and nine terrain materials. Its
SHA-256 is `cc5803e6917baa36d0e681a9ce922ad42a83c3301835fcca59e24dc8bd42797a`.
The final four-view native test passed with zero extension faults and no change
to the original profile. The project's 35 automated tests also passed.

Native reports record loading, distinct camera views, simulation advancement, extension faults and original-profile checks. Structural tests cover bit-plane padding, texture ordering, blend ranges, start identities, empty sections and invalid elevations.

WorldBuilder open/save remains unverified because its control helper could not initialize. The route checks establish continuous terrain corridors; full native horde traversal, prolonged AI play, network play and competitive balance need further playtesting.

See [technical and file-format findings](ashen-march-format-findings.md) for byte layouts, evidence and unresolved fields, and the [general map workflow](map-creation-workflow.md) for the reusable method.
