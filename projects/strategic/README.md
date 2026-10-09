# Strategic extension

`native/strategic.cpp` owns the BFME2 strategic camera, orthographic picking,
symbol rendering and hook installation. `native/symbols.inc` contains the symbol
geometry. Shared capture and scenario features are included from the repository's
`src/native/` directory and keep their existing exported ABI.

As strategic symbols fade in, they represent battalions rather than individual soldiers.
Above height 2,400, nearby battalions of the same owner, role and selection state
merge into a role marker with a count. Heroes and builders remain separate.
Counts refer to battalions or standalone units, never individual horde members.
A soft 13% owner-coloured footprint shows the grouped positions. Fog/stealth
filtering runs before grouping; hidden units do not contribute to counts or areas.

Fortresses, production, economy, defenses, capturable objectives and gates have
separate glyphs, classified from native KindOf flags with a generic building
fallback. Visible wall objects use short orientation-aligned segment marks;
these are conservative strokes, not exact model outlines or inferred links
across gaps. Wall upgrades without a distinguishing flag retain the fallback.
Empty fortress expansion pads are hidden unless selected. Overlapping markers
can move a short distance with a leader line; footprints keep their real anchors.

`native/symbol_groups.inc` owns bounded grouping and merge/split hysteresis;
`native/symbol_overlay.inc` owns counts, tinted footprints and drawing priorities.
Groups have at most 64 members, a 480-world-unit anchor limit and a screen-space
radius. Buildings remain individual. Selected groups and heroes receive drawing
priority; capacity limits drop whole low-priority markers instead of triangles.
The overlay remains visual: clicking a count does not select the whole group.

Mouse-wheel zoom keeps the terrain beneath the cursor in place, including the
transition to the overhead view. `native/cursor_zoom.inc` handles this anchoring;
HUD input and scripted photo/trailer cameras keep their own behavior.

Build with `python scripts/bfx.py mod build`. The output remains
`runtime/bfme-host/extension/bfmexbar-strategic.dll`.
Use `python scripts/bfx.py mod build --self-test` for the pure C++ grouping and
drawing regressions. `--output-dir artifacts/strategic/candidate` builds separately
while the installed DLL is in use. A new DLL requires restarting the game.
`python scripts/bfx.py play --symbols-check` starts an isolated prepared 4v4,
captures four native views, and checks grouping, building categories and draw
errors. Screenshots and the report go to `artifacts/strategic/counted-symbols/native/`.
This test covers the overlay; it does not certify every faction's wall model or
replace the separate camera and visibility regressions.

Validation on 2026-10-09: the native four-view battle check passed without
first-chance exceptions or dropped markers; the overview reduced 199 visible
candidates to 145 markers. The C++ self-test and 98 Python unit tests passed.
The separate camera sweep completed its four stages but still reported an
aim-point offset on Eight Kingdoms; that broader camera check is not a pass.

`compatibility/bfme2-1.06.json` supplies the launcher's executable hash guard.
Native instruction fingerprints remain next to their hooks. `presets/default.toml`
supplies the host builder's zoom and army-cap defaults; explicit build arguments
override them. Machine-specific compiler paths belong in `scripts/config.local.toml`.

See [repository layout](../../docs/repository-layout.md) and
[native integration details](../../docs/bfme-host.md).
