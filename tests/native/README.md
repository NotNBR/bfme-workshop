# Native game checks

These checks require the licensed BFME2 installation, prepared isolated runtime
and compiled extension. They start the game; they are not part of unit discovery.

For configurable views and per-image camera/hash evidence, use the
[native screenshot command](../../docs/native-screenshots.md).

```powershell
python scripts/bfx.py mod build
python scripts/bfx.py mod check --map "maps\map mp bfmexbar eight kingdoms.map"
python scripts/bfx.py mod zoom-check --map "maps\map mp bfmexbar eight kingdoms.map"
python tests/native/check_cursor_zoom.py
python scripts/bfx.py showcase capture eight-kingdoms --run-id native-check-001
```

Projection/picking and camera reports remain in
`runtime/bfme-host/verification/`. Showcase battle/capture evidence is written
under the chosen run's `validation/` directory. Inspect actual screenshots and
capture frames alongside numeric reports. These checks do not establish live
WorldBuilder saving, network play or competitive map balance.

The cursor-zoom check measures terrain-anchor drift in native perspective and
orthographic cameras, in both zoom directions, and checks HUD exclusion. Its
report is `runtime/bfme-host/verification/cursor-zoom-regression.json`.

## Script behavior checks

The original script lab validates counters, flags, timing, branches and an area
trigger by observing named objects created by native map scripts. Its harness
does not create those objects. See [map scripts](../../docs/map-scripts.md) for
build/run commands, failed experiments and precise evidence limits.
