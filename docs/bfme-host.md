# Original BFME2 host

BFME2 owns rendering, simulation, animation, locomotion, formations, selection, cursor, combat and UI. The project adds local configuration changes and a small, version-checked camera extension. No Forged Alliance executable or simulation runs in this build.

## Launch path recovered from openbfme2

The reference launcher uses `D:\LAN\lotrbfme2\local\bfme2`. Its `apt/` directory contains the native menus; the incomplete `D:\LAN\bfme2` installation used in the first attempt lacked those resources.

`src/tools/bfme_host/launch.py` imports the existing `openbfme2/tools/game_smoke.py` and `boot_smoke.py` helpers with bytecode writing disabled, and redirects their outputs into this project's runtime. Their Win32 debugger follows the original launcher into `game.dat`, applies the XP-version compatibility fix, redirects AppData, and prevents background focus changes from freezing loading.

Raw retail `-file` startup leaves the game-info pointer unset and player templates in observer state. The reference `fileSlotsSet` hook fills those slots before the native engine starts the match. The default entry point uses a human faction versus easy AI on Udun.

This machine's BFME2 registry entry selects a Witch-king-named profile directory. The wrapper reads that value and seeds Options.ini in the corresponding isolated directory. Seeding only the usual BFME2 directory caused the first-start CPU benchmark to run and crash. No registry value is changed.

## Graphics preset

The wrapper defaults to native Medium graphics instead of the reference smoke
helper's Low preset. Medium restores volume/decal shadows, scenery props and
full texture resolution. Use --graphics Low, Medium, High or UltraHigh to select
another native preset. All changes stay in the isolated Options.ini profile.
High enables shadow maps and terrain normal maps, but the Ashen March test only
advanced two simulation frames in 180 seconds, so it is not our default.

## Strategic camera extension

The mod changes only `cameraMaxHeight` in map metadata and the global fallback. Minimum height, pitch, terrain-related camera fields, and all other decompressed map bytes stay unchanged.

Extending the permitted camera height alone exposed BFME2's separate rendering cutoff: `W3DView::setCameraTransform` at RVA `0x8BE6B` computes the far plane as the global scalar at offset `0x950` multiplied by 1800. Its multiplication instruction is at RVA `0x8BED6`, and the constant is at RVA `0x7C7808`. These were checked against the local 1.06 binary and openbfme2's recovered symbols.

`camera.py` allocates a process-local float and redirects only that instruction's operand to 1800 times the zoom factor. It verifies the original instruction, original constant and written bytes. The near plane, shared constant, cursor camera and on-disk executable stay unchanged. The extension is installed once, so normal frames do not incur debugger callbacks. Exact executable SHA-256 is checked before launch:

`f008b587570bad693981dc7218588c81d192a1e064b0f7f861539c51156a7640`

## Scope

Twenty-fourfold zoom limits and fourfold multiplayer command-point ceilings are configured. Starting caps, production, resources, original units and animations are preserved. Strategic camera/symbols are implemented as described below. These changes are not a simulation scalability fix, nor a completed Supreme Commander engine splice. Improved strategic ordering and very large battle performance still need implementation and validation.

## Orthographic view and symbols

`src/native/host/strategic.cpp` compiles to a project-local 32-bit DLL. The launcher loads it on the game's own main thread through the existing debug call helper. Five complete, fingerprinted instruction spans are intercepted: `W3DView::setCameraTransform` (RVA 0x8BE6B), `W3DView::getPickRay` (0x89658), `DX8Wrapper::End_Scene` (0x122BE0), `W3DView::updateView` (0x85B36), and the native drawable UI-queue helper (0x239FCC). Original instructions run through trampolines, and disk binaries stay unchanged.

Between measured native heights 800 and 2600, a smoothstep plus a critically damped, per-frame tilt response moves the tactical camera overhead. Symbols fade in separately from height 1400 to 2000. Once the tilt settles overhead, the native camera switches to orthographic projection. The response rate is 18/s (approximately 0.26 seconds to complete 95% of a step). BFME2 retains its own zoom interpolation. The orthographic plane matches the perspective plane's ground scale at the transition. Zooming in restores the original camera transform/projection. Only TheTacticalView is changed; other view instances and the cursor camera are excluded.

Orthographic picking needs a separate correction: retail's getPickRay assumes all rays start at one camera point. The extension generates parallel rays through the corresponding orthographic-plane position. Native selection and order processing continue downstream. A diagnostic projects three points from those rays back through BFME2's own CameraClass::Project and measures the pixel error.

Symbols are batched Direct3D9 triangles drawn before the engine finishes the scene. A D3D state block preserves/restores game rendering state. Owner-colored geometric symbols identify broad native unit roles; one house-shaped symbol identifies every structure, including selectable construction plots. Native template KindOf bits distinguish infantry, archers, pikes, cavalry, siege, monsters, heroes, builders and flying units. Contained soldiers inherit their horde template role so banner bearers match the battalion. Heroes use five-point stars. Shape contours and internal strokes share a 1.12 size multiplier; ordinary outer radius is 8.4 pixels and selected outer radius is 9.52 pixels. Hero stars receive a further 1.4 multiplier, including their border geometry. The overlay reads native world objects and does not replace them. Positions come from Drawable::getTransform (RVA 0x27628E), the cached client-frame interpolation used by native Drawable::draw, rather than the discrete simulation position at Object +0x38. This adds no second smoothing filter. The exported bfxSymbols counters verify movement between simulation ticks during the battle regression. The same hidden, hiddenByStealth and fullyObscuredByShroud flags used by Drawable::draw are checked. Objects belonging to another player additionally require clear/partly-clear native shroud status. The symbol renderer does not change fog or stealth state. The optional battle preset permanently reveals the map for both participating factions.

The native palantir region is excluded from the symbol layer. Dense-army icon clustering remains future work. The extension currently activates in skirmish mode; campaign and multiplayer remain unvalidated.

The first native regression passed all four states (300 perspective, 1100 transition, 2400 orthographic, 300 restored). At maximum height it rendered both unit and building symbols without D3D or native exceptions. Native projection/picking round-trip error was 0.000077 pixel, with exactly parallel orthographic rays. Final reports/screenshots are saved under `runtime/bfme-host/verification/strategic-*`.

The final visibility-filtered build also passed on Grey Mountains: seven structure/plot symbols and two builder symbols were visible, 36 objects were excluded by visibility checks, and camera restoration passed. Picking error was below 0.000184 pixel. This validates projection and mouse-ray alignment; it is not a multiplayer or large-army performance benchmark.

The stock map has finite boundaries: black space outside its edges remains expected; ordinary skirmishes retain fog, while the battle preset reveals the map. Rendering the terrain at far zoom is distinct from expanding the playable map.

## Local checks

The native skirmish check reached mode 2 and advanced from frame 0 through frame 156 without a first-chance exception. Source-installation and original-profile guards passed. Runtime JSON and screenshots are under `runtime/bfme-host/verification`; retail content stays outside Git.

The camera regression check subsequently reached actual heights 300 and 2400, read back near/far planes 10 and 14400, and continued through simulation frame 160 without exceptions. Both screenshots were inspected: the terrain is visible at maximum zoom-out. The test also checks the upper central world region separately from the HUD so a black world with a visible interface cannot pass that check.

`start.ps1 -ZoomCheck` calls BFME2's native camera-height setter at a normal height of 300 and at the current map's maximum height, captures both views, records actual heights and near/far planes, and runs the same skirmish checks. The native setter is invoked on the game thread through the reference debugger's call helper. Screenshots must also be visually inspected: a nonblank HUD alone cannot prove the terrain is visible. A preliminary wheel-message test was inconclusive because it did not establish that the camera moved.

Source dependencies remain in the adjacent openbfme2 checkout, read only. See that checkout's license and the existing [third-party notices](../src/native/THIRD_PARTY.md) for the reverse-engineered and format references. Python dependencies are pinned in `src/tools/bfme_host/requirements.txt`.

## Camera movement tracing and health bars

`start.ps1 -Window -CameraTrace` records `runtime/bfme-host/verification/camera-trace.csv`. `-StrategicCheck` also records a trace. Ordinary launches do not write this potentially large CSV. Each trace launch replaces the latest CSV; copy evidence into `artifacts/` before another recording.

A bounded 4,096-row native ring records four phases: before the native view update, after the original camera transform, after the view update, and the actual rendered frame. The launcher drains it once per second without file IO in the rendering hook. Sequence numbers detect overwritten/partial rows. Fields include time, requested height, native previous-frame height, measured height used by the extension, native focus, camera XYZ/back vector/elevation, view-plane extents, projection type, near/far clipping planes, tilt blend, and health-bar widths.

The trace established that View +0x40 is the requested height, while +0x50 can still hold the preceding frame's height when `buildCameraTransform` has already interpolated the matrix. Neither is a reliable pivot distance during movement. The extension now measures the freshly built matrix's height above the native focus plane (+0x14). This removes the incorrect pivot displacement. A recorded Grey Mountains sweep reduced the maximum aim-point error from about 1,877 world units in the earlier test build to less than 0.001; the earlier build also briefly crossed below the focus plane. Camera angles continue updating on frames without mouse-wheel input.

The final part of the perspective transition moves the camera back and narrows its view plane together, approaching parallel rays before the orthographic switch. Far clipping is extended for that temporary camera position. The native perspective and its clipping values are restored on return.

Health rectangles are prepared by the native routine at RVA 0x278DFE and stored at Drawable +0x460. Its queue-0 call to 0x239FCC provides a fresh rectangle before UI rendering. Scaling there avoids repeatedly shrinking stale rectangles on the preparation routine's early-return paths. The extension first removes the old `1/getZoom()` size factor (getter 0x858E4 reads View +0xA8 times +0x3C), then scales by 300 divided by measured camera height. Bars retain their anchor, native colors, health amount, visibility rules and 3-pixel height. Width is bounded to 12–36 pixels overhead, with a smoothly increasing upper limit of 240 pixels at normal height.

The strategic regression selects an owned, visible starting structure, checks its health rectangle at near/intermediate/far heights, checks camera restoration and native picking, and rejects trace drift, below-focus camera positions or dropped samples. A manual wheel movement during a scheduled snapshot can change the requested height and invalidate that snapshot; the CSV retains those movements for diagnosis.

Plot a saved trace with the optional plotting dependency `matplotlib==3.10.7`:

```powershell
.\.venv\Scripts\python.exe src/tools/bfme_host/camera_trace.py artifacts/bfme-host/camera-trace/after-fix.csv --before artifacts/bfme-host/camera-trace/before-fix.csv --output artifacts/bfme-host/camera-trace/camera-movement
```

This writes a PNG and JSON summary. The plot uses only final rendered-frame samples; intermediate native transforms are retained in the CSV for diagnosis.

## Orcs versus Elves preset and extended zoom

The default package uses a 24x camera limit (Grey Mountains: 7,200, increased from 4,800). Its process-local far-plane multiplier is 43,200. Actual map boundaries still apply.

`--battle orcs-elves` selects Mordor and Elves in native skirmish slots. The helper identifies both existing fortresses and their owners before placing anything, excluding the separate hostile creep player. It creates 16 Orc Warrior, four Orc Archer, two Easterling, six Lorien Warrior, four Lorien Archer and two Mithlond Sentry battalions. Twelve Mordor and eight Elven battalions begin near contact in the central valley, with infantry forward, archers behind, and pikes on the flanks. The other fourteen battalions are placed near their own bases. Four releases at elapsed simulation frames 40, 90, 140 and 190 send them toward the fight through normal native attack-move/pathfinding. Reserves are already present on the map; no units spawn at the front. Each battalion receives one scenario order, leaving subsequent player commands intact.

Each original fortress gets eight additional structures. Mordor: three Slaughter Houses, two Orc Pits, a Haradrim Palace, a Troll Cage and a Battle Tower. Elves: three Mallorn Trees, two Barracks, a Green Pasture, an Eregion Forge and a Battle Tower. Placement checks terrain elevation and footprint samples and avoids nearby faction buildings. Completed native buildings notify the player construction handler (0x2A9D02) and module build-complete listeners (0x28CBFD), including final pathfinding footprint registration. The probe verifies construction state -1 at Object +0x280.

Permanent map reveal follows native ScriptActions 0x3BB9C6: TheShroudManager facade at global 0x9FE74C calls 0x739790 for each faction. The recovered donor names label this facade PartitionManager too; using the actual PartitionManager global is incorrect. Probe 0x7397F0 verifies that each faction can see the other fortress. Stealth rules remain native.

Factory creation alone leaves empty hordes. After placement, the preset invokes HordeContain's payload virtual (primary vtable 0x845050, slot 28, RVA 0x46E8EE), which delegates to TransportContain and initializes horde membership. Opening orders are sent immediately on the same game thread through each AICommandInterface; later game-thread callbacks release the reserves. Creation and initial orders happen once. Runtime counters, faction choices and screenshots are recorded under `verification/`; this is a local scenario preset, not a change to ordinary skirmish starting armies.

Addresses were checked against the supported binary: Player default-team offset +0x2EC from the native relationship loop at 0x2A7C70, Object ID +0x74 from the native factory, AI pointer +0x258, AICommandInterface +0x20, Object lookup 0x49DC5, and attack-move 0x295A0F. Source reconstruction labels alone were not sufficient for the default-team layout.

The expanded-range regression passed at heights 300, 1800, 4800 and back to 300. The intermediate view remained in perspective, full overhead picking error was below 0.000087 pixel, and near/far health-bar bounds passed. The Orcs-versus-Elves regression confirmed all 26 attack-move orders and 226 symbol movements between simulation ticks, with no first-chance exceptions. Evidence is preserved under `artifacts/bfme-host/camera-trace/` and `artifacts/bfme-host/battle/`.

Symbol styling uses 8.4-pixel outer radii (increased 12% from 7.5), with a thicker gold rim for selected objects. Selection reads Drawable +0x43C and follows Object +0x274 containment so battalion members inherit their horde selection. Enemy red uses the local player’s native relationship query (RVA 0x2AD0C6) against the object’s team; allies and neutral objects retain owner colors. The battle regression selects a native Mordor horde and checks selected-member and enemy-symbol counters. Launches set 1920 × 1440 (4:3) both on the command line and in the isolated Options.ini, whose Resolution value otherwise overrides the requested dimensions.

The Full HD battle check passed with a captured 1920 × 1080 client, selected battalion borders, enemy-red symbols, and zero native exceptions. The HUD exclusion scales with the viewport so symbols stay outside the enlarged controls. Evidence is in `artifacts/bfme-host/symbols/`.

The opening battle also includes native MordorWitchKing, MordorMouthOfSauron, ElvenHaldir and ElvenGlorfindel objects, two heroes per faction. They start just behind their infantry and receive one native attack-move order each. Heroes have separate spawn, order and survival counters; they are not included in the 34 battalion count. Symbol-type counters verify that all four heroes render as stars.

The latest scenario check exercises 34 battalions, 16 completed base buildings, four heroes and all four reinforcement releases. It also checks opening casualties before reserves, reserve movement, role-specific symbols, selected borders, enemy colors and interpolated symbol positions. Screenshots use 1920 x 1440. Evidence is saved under `artifacts/bfme-host/scenario/`.

## Veterancy marker scaling and short showcase

Retail Drawable's veterancy renderer at RVA 0x277DB4 divides pip dimensions by View::getZoom. That value is normalized against the map camera ceiling, so the extended limit magnified rank markers into large orange squares. The extension redirects only the verified six-byte zoom-getter call at 0x277E23 to a measured-height scale (height/300, bounded to 1..2). Original rank images, ranks, visibility, world anchors and the global zoom getter are preserved. The bfxPipScale export records call counts and both scales.

The optional showcase now records 29 seconds. A gentle 95-unit pan and 0.18-radian arc returns to the captured initial bearing and battle center by second 7. The camera pauses before zooming from height 600 to 2600 (seconds 8..13), holds, zooms to 7200 (15..20), holds, then returns to 600 (22..28). All segments ease in and out. The recorder starts about one second into the camera lead-in; camera control returns at second 30. Per-second camera height, bearing and native diagnostics are saved to artifacts/showcase/timeline.jsonl.

The current launcher uses a smaller 1600 x 1200 (4:3) client. The 29-second showcase exports at that size without added captions; native game UI remains visible. Earlier validation captures retain their original resolutions.
