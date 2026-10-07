# Original BFME2 host

BFME2 owns rendering, simulation, animation, locomotion, formations, selection, cursor, combat and UI. The project adds local configuration changes and a small, version-checked camera extension. No Forged Alliance executable or simulation runs in this build.

## Launch path recovered from openbfme2

The reference launcher uses `D:\LAN\lotrbfme2\local\bfme2`. Its `apt/` directory contains the native menus; the incomplete `D:\LAN\bfme2` installation used in the first attempt lacked those resources.

`tools/bfme_host/launch.py` imports the existing `openbfme2/tools/game_smoke.py` and `boot_smoke.py` helpers with bytecode writing disabled, and redirects their outputs into this project's runtime. Their Win32 debugger follows the original launcher into `game.dat`, applies the XP-version compatibility fix, redirects AppData, and prevents background focus changes from freezing loading.

Raw retail `-file` startup leaves the game-info pointer unset and player templates in observer state. The reference `fileSlotsSet` hook fills those slots before the native engine starts the match. The default entry point uses a human faction versus easy AI on Udun.

This machine's BFME2 registry entry selects a Witch-king-named profile directory. The wrapper reads that value and seeds Options.ini in the corresponding isolated directory. Seeding only the usual BFME2 directory caused the first-start CPU benchmark to run and crash. No registry value is changed.

## Strategic camera extension

The mod changes only `cameraMaxHeight` in map metadata and the global fallback. Minimum height, pitch, terrain-related camera fields, and all other decompressed map bytes stay unchanged.

Extending the permitted camera height alone exposed BFME2's separate rendering cutoff: `W3DView::setCameraTransform` at RVA `0x8BE6B` computes the far plane as the global scalar at offset `0x950` multiplied by 1800. Its multiplication instruction is at RVA `0x8BED6`, and the constant is at RVA `0x7C7808`. These were checked against the local 1.06 binary and openbfme2's recovered symbols.

`camera.py` allocates a process-local float and redirects only that instruction's operand to 1800 times the zoom factor. It verifies the original instruction, original constant and written bytes. The near plane, shared constant, cursor camera and on-disk executable stay unchanged. The extension is installed once, so normal frames do not incur debugger callbacks. Exact executable SHA-256 is checked before launch:

`f008b587570bad693981dc7218588c81d192a1e064b0f7f861539c51156a7640`

## Scope

Eightfold zoom limits and fourfold multiplayer command-point ceilings are configured. Starting caps, production, resources, original units and animations are preserved. Strategic camera/symbols are implemented as described below. These changes are not a simulation scalability fix, nor a completed Supreme Commander engine splice. Improved strategic ordering and very large battle performance still need implementation and validation.

## Orthographic view and symbols

`native/host/strategic.cpp` compiles to a project-local 32-bit DLL. The launcher loads it on the game's own main thread through the existing debug call helper. Three complete, fingerprinted instruction spans are intercepted: `W3DView::setCameraTransform` (RVA 0x8BE6B), `W3DView::getPickRay` (0x89658), and `DX8Wrapper::End_Scene` (0x122BE0). Original instructions run through trampolines, and disk binaries stay unchanged.

Between heights 800 and 1400, a smoothstep based on camera height tilts the tactical camera overhead and fades in symbols. At 1400 the native camera switches to its orthographic projection. The orthographic plane matches the perspective plane's ground scale at the transition. Zooming in restores the original camera transform/projection. Only TheTacticalView is changed; other view instances and the cursor camera are excluded.

Orthographic picking needs a separate correction: retail's getPickRay assumes all rays start at one camera point. The extension generates parallel rays through the corresponding orthographic-plane position. Native selection and order processing continue downstream. A diagnostic projects three points from those rays back through BFME2's own CameraClass::Project and measures the pixel error.

Symbols are batched Direct3D9 triangles drawn before the engine finishes the scene. A D3D state block preserves/restores game rendering state. Owner-colored diamonds identify selectable units; roof-marked squares identify structures, including selectable construction plots. The overlay reads native world objects and does not replace them. The same hidden, hiddenByStealth and fullyObscuredByShroud flags used by Drawable::draw are checked. Objects belonging to another player additionally require clear/partly-clear native shroud status. No fog or stealth state is changed.

The native palantir region is excluded from the symbol layer. Per-class artwork and dense-army icon clustering are future work. The extension currently activates in skirmish mode; campaign and multiplayer remain unvalidated.

The first native regression passed all four states (300 perspective, 1100 transition, 2400 orthographic, 300 restored). At maximum height it rendered both unit and building symbols without D3D or native exceptions. Native projection/picking round-trip error was 0.000077 pixel, with exactly parallel orthographic rays. Final reports/screenshots are saved under `runtime/bfme-host/verification/strategic-*`.

The final visibility-filtered build also passed on Grey Mountains: seven structure/plot symbols and two builder symbols were visible, 36 objects were excluded by visibility checks, and camera restoration passed. Picking error was below 0.000184 pixel. This validates projection and mouse-ray alignment; it is not a multiplayer or large-army performance benchmark.

The stock map has finite boundaries: black space outside its edges and normal fog of war remain expected. Rendering the terrain at far zoom is distinct from expanding the playable map.

## Local checks

The native skirmish check reached mode 2 and advanced from frame 0 through frame 156 without a first-chance exception. Source-installation and original-profile guards passed. Runtime JSON and screenshots are under `runtime/bfme-host/verification`; retail content stays outside Git.

The camera regression check subsequently reached actual heights 300 and 2400, read back near/far planes 10 and 14400, and continued through simulation frame 160 without exceptions. Both screenshots were inspected: the terrain is visible at maximum zoom-out. The test also checks the upper central world region separately from the HUD so a black world with a visible interface cannot pass that check.

`start.ps1 -ZoomCheck` calls BFME2's native camera-height setter at a normal height of 300 and at the current map's maximum height, captures both views, records actual heights and near/far planes, and runs the same skirmish checks. The native setter is invoked on the game thread through the reference debugger's call helper. Screenshots must also be visually inspected: a nonblank HUD alone cannot prove the terrain is visible. A preliminary wheel-message test was inconclusive because it did not establish that the camera moved.

Source dependencies remain in the adjacent openbfme2 checkout, read only. See that checkout's license and the existing [third-party notices](../native/THIRD_PARTY.md) for the reverse-engineered and format references. Python dependencies are pinned in `tools/bfme_host/requirements.txt`.
