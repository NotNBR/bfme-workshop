# bfmeXbar

A playable **single-player RTS prototype** combining Middle-earth battalions with Supreme Commander-inspired strategic zoom and army controls. Built in a separate local repository; `../openbfme2` is used as a read-only technical reference.

This is a new simulation with a Canvas renderer. It does **not** merge or launch BFME2, Supreme Commander, or Recoil binaries. It is a first playable foundation, not a complete remake or a finished BAR total conversion.

## Play

Double-click **`Launch bfmeXbar.cmd`**. Requires Node.js 20+ (Node 24 is installed on this machine). Alternatively:

```powershell
cd D:\LAN\bfmeXbar
npm start
```

Open **http://127.0.0.1:8077**, choose a battle size, and click **Enter the battlefield**. No npm install, CDN, account, or internet connection is required. The server binds to loopback only. The port can be overridden with `PORT`.

You command Gondor; Mordor is AI-controlled. Capture outposts for income, recruit battalions, and destroy the opposing fortress. Opening scenarios contain approximately 800, 2,400, or 6,000 individual soldiers across both sides. Counts round up to complete battalions, with Aragorn added separately. The production cap is 8,000 living plus queued soldiers per side; that cap is not a performance guarantee.

## Implemented

- Cursor-centered strategic zoom, overview toggle, minimap navigation, camera panning and selection focus.
- Battalion selection, selection box, visible same-type selection, nine control groups and whole-army selection.
- Move, attack-move, hold, stop, Shift-queued waypoints, and four movement formations.
- Individual health, targeting and attacks; melee, ranged, cavalry, hero, monster and siege archetypes.
- Spatial indexing and a fixed 20 Hz simulation, independent of rendering rate.
- Production queues, cancellation refunds, reinforcement rally points, resource outposts and an area-heal power.
- Enemy AI, fortress victory/defeat, pause, speed controls and browser-local save/load.
- Read-only BFME2 BIG/INI importer with per-field provenance, plus optional original unit portraits.

## Controls

| Action | Input |
|---|---|
| Select battalion / box-select | Left click / left drag |
| Add/remove selection | Shift + left click |
| Select visible battalions of same type | Double click |
| Move / contextual attack move | Right click |
| Attack move | A, then click destination |
| Queue orders | Hold Shift while issuing destinations |
| Hold / stop | H / S |
| Strategic zoom | Mouse wheel |
| Pan | Middle drag / arrow keys |
| Whole-map overview | Tab |
| Select whole army / focus selection | F2 / F |
| Store / recall control group | Ctrl + 1–9 / 1–9 |
| Heal area | Q, then click; costs 30 power |
| Pause | Space |

## Local BFME content

This checkout already has nine imported unit records and portraits under `local-content/`. Those files are ignored by Git. The default game is also playable without them, using explicitly approximate prototype values and generated visuals.

To refresh balance data from your own installation:

```powershell
python tools/import_bfme.py --game ..\bfme2 --reference ..\openbfme2
```

Add `--portraits` when using a Python environment with Pillow installed. This reads `Textures*.big`, resolves `MappedImage` regions, and writes small PNGs. The Python bundled with this Codex installation was used for the initial portrait conversion.

The importer reads the base **INI.big only**, not the installed patch/mod archive precedence. Supported fields are base health, horde count/cost/build time, and available numeric fields from the first primary weapon. Unsupported constants/fields remain prototype defaults. It does not execute SAGE behaviors, infer missing damage from projectile chains, resolve ChildObject inheritance, or claim patch-accurate balance. The pack includes source object names, source paths, archive SHA-256, and the inspected reference repository commit.

## What remains

Battlefield units and terrain are schematic original drawings; unit portraits can be original local assets. W3D mesh/animation import, BFME maps, collision-aware terrain navigation, fog of war, full armor/counter tables, hero powers, building placement, campaigns, the other factions, sound, and multiplayer are **not implemented**. Rivers, trees and ruins are decorative and traversable. Movement has no unit collision or crowd separation. Test results establish a playable prototype, not BFME engine compatibility.

## Development and verification

```powershell
npm test
python -m unittest discover -s tests -p 'test_*.py'
npm run benchmark
```

`tools/browser-smoke.mjs` is an optional Playwright test (Chrome required). Run the local server first. Install Playwright for development, or set `PLAYWRIGHT_MODULE` to an existing `playwright/index.mjs`. The smoke test expects the local BFME pack for this checkout. Screenshots and reports go to ignored `artifacts/`.

On 2026-10-07: 16 simulation tests, 4 importer tests, and a Chrome UI smoke test passed. The 6,000-unit headless simulation benchmark ran 600 ticks / 30 simulated seconds: approximately 2.05 ms mean and 6.14 ms p95 per tick, against a 50 ms budget. This includes an attack convergence workload and casualties; it does not keep every initial unit alive or include rendering. Browser smoke testing reached 6,024 living units without JavaScript exceptions. Results are machine/workload specific.

The engine integration research and technical decision are in [docs/engine-integration.md](docs/engine-integration.md). Content provenance and reuse boundaries are in [docs/provenance.md](docs/provenance.md).
