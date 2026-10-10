# The Greywater Marches

A large open six-player skirmish map, 13,500 × 9,000 world units, built from the supplied 3:2 heightmap. Both horizontal dimensions are enlarged by 1.5 relative to the original plan. Six spacious construction areas surround branching rivers, rocky grasslands and irregular mountains. Each start has an outpost and a creep camp nearby. Native stone bridges cross natural narrow reaches.

The supplied landscape guides the olive grass, dry earth, grey stone and blue water. Water reflections are disabled, and the height grid has 1,353,600 samples. Elevation follows the reference luminance linearly; local grading is limited to bases, bridge approaches and neutral foundations. Each build exports a comparison with the actual map heights.

## Ground and scenery pass

Playable dry ground receives land-weighted Gaussian smoothing with a 35-world-unit radius and 88% strength, limited to a 16-unit height change. The influence fades near shores, steep slopes and high ridges. The six existing starts and all bridge positions are retained. The recorded short-ripple RMS dropped from 6.08 to 3.04 on 338,734 measured ground cells; this measures terrain variation, not FPS.

Fourteen sheltered groves contain 1,800 native optimized trees: 1,050 in dense cores, 500 in open stands and 250 on sparse fringes. Deciduous species favour valleys; evergreen species become more common in the foothills. Irregular density fields and varying spacing avoid a uniform tree carpet. Ferns, bushes, stumps and fallen logs support the woodland edges.

Rock groups follow actual slope toes, with smaller fragments downhill and stones on dry river terraces. Small weathered ruins, rubble, crates, barrels and cart wheels sit around the neutral outposts. The current pass has 2,681 map records including starts and functional objects.

Six connecting routes, twelve expansion/creep approaches and eight bridge paths reserve corridors at least 360 world units wide. Placement checks reject water, steep or unsupported foundations, base clearings, bridge approaches and these corridors. A conservative terrain-plus-prop footprint check verifies that all six starts and neutral sites remain connected. Native movement validation tests the eight bridges with builders; it is separate from that grid approximation.

Authoring follows [the mapping workflow](../../../docs/guides/map-workflow.md), [heightmap conventions](../../../docs/reference/mapping/terrain-and-presentation/heightmaps.md), [terrain records](../../../docs/reference/mapping/terrain-and-presentation/terrain.md) and [native bridge evidence](../../../docs/reference/mapping/navigation/roads-and-bridges.md). Tree and prop choices are checked against the installed nature/civilian INI definitions; generic tree base classes are never placed.

Build: `python scripts/workshop.py map build greywater-marches`

Play: `python scripts/workshop.py play --greywater`

The generator records structural checks and terrain connectivity separately from native gameplay validation. The layout preview is an authored terrain plan, not a game screenshot. Reference images are copied without alteration.

Each build writes `validation/build.json`, `detail-placement.json`, a heightmap comparison, a layout preview and `tour.json`. Run the tour with `python scripts/workshop.py play --greywater --map-check --map-tour local/artifacts/maps/greywater-marches/<run-id>/tour.json`. Native screenshots and `native-validation.json` are saved beneath that run's `validation/native` directory.
