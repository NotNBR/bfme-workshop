# bmfe-workshop

A playable **native Recoil integration of BFME II infantry**, built in its own local Git repository at `D:\LAN\bmfe-workshop`.

The current slice imports Gondor soldiers and Mordor orcs from the local BFME II installation: original meshes, textures, skeletons, idle/run/attack animation tracks, and selected INI balance values. Recoil provides the native renderer, simulation, pathfinding, selection, orders, strategic camera, and combat. The default battle starts with **1,050 units**.

This is an early content-and-animation bridge. It does **not** yet execute the recovered SAGE game runtime or the Supreme Commander/Forged Alliance executable. Full engine splicing remains unfinished. Recoil was chosen as the accessible native host for the first working integration; see [the engine decision and research](native-integration.md).

## Play

Run `.\src\legacy\recoil\tools\start.ps1` from the repository root to launch this
archived Recoil experiment. The [launcher](../../mods/recoil/tools/start.ps1)
uses its isolated native runtime. No browser, lobby, or account is used.

You control Gondor. Mordor advances automatically. This is a field-battle sandbox, with no recruitment or campaign yet.

| Action | Input |
|---|---|
| Select / box select | Left click / drag |
| Move or attack a target | Right click |
| Queue orders | Shift while issuing orders |
| Attack move | A, then click |
| Stop | S |
| Strategic zoom | Mouse wheel |
| Pan | Arrow keys / middle drag |
| Toggle whole-map view | Tab |
| Focus selected troops | Space |
| Expand selection to their battalions | B |
| Control groups | Ctrl + number / number |
| Exit | Escape, then Quit |

Different army sizes can be launched from PowerShell:

```powershell
.\src\tools\native\start.ps1 -ArmySize 525
```

The setting is per faction. It accepts 20–1,500 per faction; only 525 per faction has been verified in a full graphical battle so far.

## Rebuild from local BFME content

Run `scripts/launchers/Setup Workshop.cmd`. To use a different installation:

```powershell
.\src\tools\native\setup.ps1 -BfmePath 'D:\LAN\bfme2'
```

Setup uses Python with NumPy and Pillow, and 7-Zip if the engine must be unpacked. It prefers an existing local Python environment, including the bundled runtime on this machine. If dependencies are missing, it creates `local/venv` and installs the pinned requirements. The official Recoil **2026.07.04** archive is verified against its published SHA-256 before extraction.

BFME archives are read in place. Generated models, textures, animation tables, the engine, logs, and replays stay under ignored `local/runtime/`. They are not committed. The map is a generated SMF/SMT test field; it is not the original Pelennor map.

## Scope and limitations

- Two infantry unit types, six original animation clips, native melee combat, battalion selection, and strategic zoom are implemented.
- S3O uses rigid pieces. The importer assigns each triangle to a dominant bone and rebases its vertices; this approximates BFME skinning and can show seams around joints. Original poses are sampled at 10 Hz.
- Health, damage, reload time, and horde metadata come from base `INI.big`. Patch archive precedence, upgrades, armor sets, powers, and SAGE behaviors are not reproduced. A 27-unit melee range is an adapter choice.
- No buildings, production, heroes, cavalry, siege, campaign, multiplayer validation, or original audio yet. Do not confuse the native slice with the broader features of the archived browser prototype.
- `openbfme2` is a read-only reference for archive/model/animation and group-command integration. Its reconstructed runtime has not been linked into this executable.

## Validation

Six native format tests cover corrupt chunk bounds, signed adaptive deltas, quaternion interpolation, native Euler conversion, and SMF layout. Four existing BIG/INI importer tests also remain available.

```powershell
python -m unittest discover -s tests -p 'test_*.py'
.\src\tools\native\start.ps1 -Test -Hidden -ArmySize 525
```

The native test runs a 90-second battle and requires movement, damage, casualties, and no Lua runtime errors. Results are written to `local/runtime/native-test.json`; the engine log is `local/runtime/engine/infolog.txt`. Screenshots are captured by the actual native renderer under `local/runtime/engine/screenshots/`.

The verified 1,050-unit run completed with **554 casualties** and **89,715.4 recorded damage**, without Lua runtime errors. Evidence from that run is saved locally under `local/artifacts/native/`. This is a smoke test on this machine, not a general performance guarantee.

## Source layout

- `mods/recoil/game/`: Recoil game definitions, battle rules, and animation playback.
- `mods/recoil/client.lua`: native camera, battalion selection, and minimal HUD.
- `mods/recoil/tools/`: W3D decoder, S3O/texture/map exporter, setup and launcher.
- `src/formats/big.py`: BIG archive and selected INI parsing.
- `examples/browser/`: superseded browser experiment, also preserved by the `browser-prototype` Git tag.

See [third-party notices](../reference/licenses/THIRD_PARTY.md) for source references and licenses. Original BFME retail assets are not included in the source repository.
