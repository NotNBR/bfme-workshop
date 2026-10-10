# Strategic extension

`native/strategic.cpp` owns the BFME2 strategic camera, orthographic picking,
symbol rendering and hook installation. `native/symbols.inc` contains the symbol
geometry. Shared capture and scenario features are included from
`src/capture/native/` and `src/scenarios/native/`, with shared ABI types under
`src/common/native/`.

Normal units render as unions of local footprints around their visible,
interpolated soldier positions. The interior uses a 24% translucent owner-color
fill (32% when selected); a softer border peaks at 70% opacity in the same hue,
with a feathered edge. Heroes keep individual stars and buildings keep legacy
house markers. Enemies use fixed red; allies and neutral objects retain owner
colors. There are no count badges, displaced markers or leader lines.

Each soldier contributes a local circular footprint with a projected
18-world-unit radius, bounded to 1.25..12 pixels. Overlapping footprints for the
same owner and selection state share one exterior border and one fill. The
signed-distance union preserves gaps, concavities and holes, so nearby groups
never acquire a straight convex-hull bridge. Merges happen as the local shapes
naturally intersect. The spatial grouping threshold is only a rendering broad
phase, including the 0.75-pixel soft fringe; it cannot enlarge a silhouette.

Footprint positions and radii use critically damped easing at 28/s (about
0.17 s to settle 95% of movement), retaining velocity through reversals.
Newly visible footprints grow smoothly into place. Merges and splits need no
replacement group contour, so their geometry stays continuous. Hidden members
are removed immediately. The field grid is anchored to viewport pixels to avoid
bounding-box jitter, at one-pixel resolution with scaling for large viewports.
Fog/stealth filtering runs before sampling and horde proxies are excluded.
Areas are clipped around the HUD with their existing alpha preserved.

`native/unit_areas.inc` owns bounded spatial grouping, footprint smoothing and
union rendering. It accepts up to 16,384 visible samples without fixed member
splits. Solid interior scanlines are combined to keep geometry economical.
Area admission reserves complete geometry budgets for stars and buildings;
heroes take priority if marker capacity is exhausted. Native selection and
orders retain their behavior.

Mouse-wheel zoom keeps the terrain beneath the cursor in place, including the
transition to the overhead view. `native/cursor_zoom.inc` handles this anchoring;
HUD input and scripted photo/trailer cameras keep their own behavior.

Build with `python scripts/workshop.py mod build`. The output remains
`local/runtime/bfme-host/extension/strategic.dll`.
Use `python scripts/workshop.py mod build --self-test` for the pure C++ grouping and
drawing regressions. `--output-dir local/artifacts/strategic/candidate` builds separately
while the installed DLL is in use. A new DLL requires restarting the game.
`python scripts/workshop.py play --symbols-check` starts an isolated prepared 4v4,
captures four native views, and checks unit areas, hero stars, building markers and draw
errors. Screenshots and the report go to `local/artifacts/strategic/unit-areas/native/`.
This test covers the overlay; it does not certify every faction's wall model or
replace the separate camera and visibility regressions.

Unit-area validation on 2026-10-10: the C++ connectivity/geometry regressions
passed, including natural collisions, concavities, holes, subtle borders, reversals,
frame-rate-independent easing and immediate removal of hidden extents. Native battle captures
are saved under `local/artifacts/strategic/unit-areas/native/`.

Historical counted-overlay validation on 2026-10-09: the native four-view battle check passed without
first-chance exceptions or dropped markers; the overview reduced 199 visible
candidates to 145 markers. The C++ self-test and 98 Python unit tests passed.
The separate camera sweep completed its four stages but still reported an
aim-point offset on Eight Kingdoms; that broader camera check is not a pass.

`compatibility/bfme2-1.06.json` supplies the launcher's executable hash guard.
Native instruction fingerprints remain next to their hooks. `presets/default.toml`
supplies the host builder's zoom and army-cap defaults; explicit build arguments
override them. Machine-specific compiler paths belong in `local/config.toml`.

See [repository layout](../../docs/getting-started/repository-layout.md) and
[native integration details](../../docs/reference/host.md).
