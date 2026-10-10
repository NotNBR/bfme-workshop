# Setup and first launch

Use Python 3.11 or later. Native integration supports the fingerprinted BFME2
1.06 executable. Supply your local game installation and the openbfme2 launch
helpers; retail game assets and the compiler are local inputs.

## Configure this machine

Copy [config.example.toml](config.example.toml) to `local/config.toml` if the
default paths do not match this machine. Paths resolve relative to the checkout.
The configuration identifies the game install, reference launch helpers and
MSVC 7.1 compiler used for the strategic extension.

## Prepare the environment and runtime

From the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup.ps1
```

The [setup shortcut](../../scripts/launchers/Setup%20Workshop.cmd) runs the same
workflow. It creates `local/venv`, installs the checkout and its dependencies,
builds local settings and initial example maps, prepares the isolated game copy
and compiles the strategic DLL.

To install only the tooling:

```powershell
python -m venv local/venv
.\local\venv\Scripts\python.exe -m pip install -e ".[video]"
.\local\venv\Scripts\workshop.exe --help
```

The tools run from their checkout, where native source and example assets are available.

## Launch

Use [Launch Workshop.cmd](../../scripts/launchers/Launch%20Workshop.cmd), or:

```powershell
.\local\venv\Scripts\python.exe scripts/workshop.py play --window --strategic
.\local\venv\Scripts\python.exe scripts/workshop.py play --greywater
```

Starting money defaults to 10,000 and starting command points to 1,000, clamped
to the player-count ceiling. Change these through `--starting-cash` and
`--starting-command-points`; values are saved for later launches.

Specialized shortcuts live in `scripts/launchers/`. Build additional examples
with `workshop map build <map-id>` before launching them on a fresh checkout.

## Verify

```powershell
.\local\venv\Scripts\python.exe scripts/check.py
node --test examples/browser/src/tests/simulation.test.mjs src/mapkit/tests/test_worldbuilder_session.mjs
.\local\venv\Scripts\python.exe scripts/workshop.py mod build --self-test
```

After building Greywater, `workshop play --test --greywater` runs a live isolated
skirmish check and closes its own session when finished. See the
[host reference](../reference/host.md) and [repository layout](repository-layout.md).
