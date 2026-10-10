# bmfe-workshop

Tools, native mods and documentation for Battle for Middle-earth II.

The shared tooling prepares isolated game runtimes, reads and writes native
formats, supports map authoring, launches scenarios, captures gameplay and
produces verified video exports. The strategic mod adds extended camera control
and readable unit areas. Maps and showcases demonstrate those tools.

Built with help from [openbfme2](https://github.com/Open-BFME/Open-BFME-2), whose
launch helpers and engine research support the native host.

## Start here

- [Setup and first launch](docs/getting-started/setup.md)
- [Repository layout and ownership](docs/getting-started/repository-layout.md)
- [Documentation index](docs/README.md)
- [Strategic mod](mods/strategic/README.md)
- [Map authoring workflow](docs/guides/map-workflow.md)

```powershell
python scripts/workshop.py --help
python scripts/workshop.py play --window --strategic
python scripts/workshop.py mod build --self-test
```

Windows shortcuts live in `scripts/launchers/`. Setup creates the checkout's
environment and runtime under ignored `local/`. Native play requires the
supported BFME2 1.06 game files and the configured openbfme2 launch helpers.

## Where things belong

| Folder | Purpose |
| --- | --- |
| `src/` | Shared tooling; each component owns its tests |
| `mods/` | Native mod source, settings and mod-specific assets |
| `docs/` | Getting started, guides, reference and research |
| `examples/` | Maps, scenarios, showcases and the browser prototype |
| `scripts/` | Thin entry points, setup and Windows launchers |
| `local/` | Ignored runtimes, content, environments, builds, captures and caches |

## Checks

```powershell
python scripts/check.py
node --test examples/browser/src/tests/simulation.test.mjs src/mapkit/tests/test_worldbuilder_session.mjs
python scripts/workshop.py mod build --self-test
```

Python checks include a real FFmpeg round trip. Native geometry tests use the
renderer's actual source. Live game checks require the prepared runtime;
the WorldBuilder session check uses a mock client.

## Examples

[Five authored maps](examples/maps/), [Eight Kingdoms 4v4](examples/scenarios/eight_kingdoms_4v4/README.md)
and [capture/edit templates](examples/showcases/eight_kingdoms/README.md) own their
settings and references. The
[Eight Kingdoms trailer](examples/showcases/eight_kingdoms/media/Eight-Kingdoms-Trailer.mp4)
is a 1080p MP4 under 20 MB.

The [browser example](examples/browser/README.md) and
[Recoil experiment](mods/recoil/README.md) have their own workflows.

Code is GPL-3.0-only; see [LICENSE.txt](LICENSE.txt) and
[third-party notices](docs/reference/licenses/README.md). Retail game assets
are user-supplied local inputs.
