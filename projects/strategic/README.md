# Strategic extension

`native/strategic.cpp` owns the BFME2 strategic camera, orthographic picking,
symbol rendering and hook installation. `native/symbols.inc` contains the symbol
geometry. Shared capture and scenario features are included from the repository's
`src/native/` directory and keep their existing exported ABI.

Mouse-wheel zoom keeps the terrain beneath the cursor in place, including the
transition to the overhead view. `native/cursor_zoom.inc` handles this anchoring;
HUD input and scripted photo/trailer cameras keep their own behavior.

Build with `python scripts/bfx.py mod build`. The output remains
`runtime/bfme-host/extension/bfmexbar-strategic.dll`.

`compatibility/bfme2-1.06.json` supplies the launcher's executable hash guard.
Native instruction fingerprints remain next to their hooks. `presets/default.toml`
supplies the host builder's zoom and army-cap defaults; explicit build arguments
override them. Machine-specific compiler paths belong in `scripts/config.local.toml`.

See [repository layout](../../docs/repository-layout.md) and
[native integration details](../../docs/bfme-host.md).
