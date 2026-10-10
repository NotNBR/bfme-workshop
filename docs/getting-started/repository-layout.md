# Repository layout

bmfe-workshop is organized around reusable tooling, self-contained mods and
documentation. Python components sit directly in `src/`; tests live beside
their implementation.

```text
src/
  cli/                 Command dispatcher
  common/              Checkout paths, run metadata and native ABI types
  host/                Runtime preparation, launch and gameplay settings
  formats/             BIG, INI, MAP, W3D and supporting codecs
  mapkit/              Authoring, terrain tools, diagnostics and validation
  strategic/           Mod compiler, injection and camera diagnostics
  scenarios/           Planning, native staging and validation
  capture/             Recordings, camera direction and screenshots
  video/               FFmpeg processing and verified exports
mods/
  strategic/
    native/            Canonical strategic DLL source
      tests/           Renderer geometry regressions
    config/            Settings and executable fingerprint
  recoil/              Experimental Recoil mod and its build tools
docs/
  getting-started/      Setup, layout and configuration example
  guides/              Practical workflows
  reference/           Formats, integration details and license notices
  research/            Experiments, findings and feature audit
examples/
  maps/                Authored sources, settings and references
  scenarios/           Prepared battle data
  showcases/           Shots, original score, edits and exports
  browser/             Browser prototype with source/tests
scripts/               Entry points, setup and Windows launchers
local/                 Ignored machine-specific and generated files
README.md
pyproject.toml
LICENSE.txt
```

## Ownership

Each feature has one canonical implementation. Shared Python behavior belongs
in its `src/` component. Native support lives with its owner, for example
`src/capture/native/`; the strategic renderer lives in `mods/strategic/native/`.
Native features currently compile into one DLL.

Tests belong in component folders such as `src/host/tests/`,
`src/formats/tests/` and `src/video/tests/`. Shared synthetic map fixtures live
in `src/formats/tests/fixtures.py`. Native renderer checks live in
`mods/strategic/native/tests/`; Recoil exporter checks live beside its tools.
Integration checks use the nearest owning component.

Example-specific geometry, armies, shots and editorial decisions belong in
`examples/`. Python example folders use underscores; CLI identifiers stay
readable, such as `eight-kingdoms`. Imports load the actual example files.

## Local files

```text
local/
  config.toml          Optional machine-specific configuration
  venv/                Python environment
  runtime/             Isolated game copy, profiles and installed mod
  content/             Imported balance data and portraits
  builds/              Compiler outputs
  artifacts/           Maps, screenshots, captures, videos and reports
  cache/               Downloads, scratch files and recovery data
```

The whole `local/` directory is ignored by Git. Existing maps and captures were
relocated here. Historical reports retain their evidence; current runtime
manifests use the new paths.

`scripts/workshop.py` runs from a checkout with dependencies installed.
An editable installation provides `workshop`. `WORKSHOP_ROOT` explicitly selects
a checkout; otherwise tools find it from their source location, independently
of the working directory. See [setup](setup.md).

## Commands

```powershell
python scripts/workshop.py mod build --self-test
python scripts/workshop.py play --window --strategic
python scripts/workshop.py map build eight-kingdoms --run-id terrain-001
python scripts/workshop.py map inspect "path/to/map.map"
python scripts/workshop.py scenario plan eight-kingdoms-4v4
python scripts/workshop.py showcase capture eight-kingdoms --run-id r005
python scripts/workshop.py showcase edit eight-kingdoms --run-dir local/artifacts/showcases/eight-kingdoms/r005
python scripts/workshop.py video "path/to/trailer.mp4" --output "path/to/small.mp4" --profile under20mb
python scripts/check.py
```

Map builds install into the isolated runtime and save a separate output run.
Run manifests record source hashes, Git state and map hashes where available.
New run IDs cannot overwrite previous runs. Completed showcases require a new
run for further revisions.

Game resource identifiers and DLL export names remain stable so existing maps
and native adapters interoperate. They do not dictate the repository's layout.
