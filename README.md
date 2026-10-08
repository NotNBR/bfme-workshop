# BFME Workshop

NotNBR's collection of **Battle for Middle-earth** mods, tools, maps, experiments
and showcases. Current projects focus on BFME II, including a strategic camera
mod, native map creation and battle trailers.

Built with help from [openbfme2 (Open-BFME-2)](https://github.com/Open-BFME/Open-BFME-2),
whose launch helpers, compatibility code and reverse-engineering work underpin
the native BFME2 integration.

https://github.com/user-attachments/assets/58612ed8-e734-4269-9eae-cec99b559f87

Eight Kingdoms trailer · 76 seconds · 5.77 MB preview ·
[1080p MP4 (19 MB)](projects/showcases/eight-kingdoms/media/Eight-Kingdoms-Trailer.mp4)

## What's inside

- **[Strategic mod](projects/strategic/README.md)** — extended zoom, an overhead
  view, unit and building symbols, and higher army caps.
- **[Map projects](projects/maps/)** — Eight Kingdoms, an eight-player map built
  from a heightmap reference; Ithilien Frontier; and The Ashen March.
- **[Battle scenarios](projects/scenarios/eight-kingdoms-4v4/README.md)** — a staged
  4 vs 4 battle with established bases, armies, siege units and monsters.
- **[Showcases and trailers](projects/showcases/eight-kingdoms/README.md)** — camera
  tours, gameplay capture, editing, music and video exports.

## Repository structure

| Folder | Contents |
| --- | --- |
| `projects/` | Strategic mod, individual maps, battle scenarios and trailers |
| `src/` | Shared tooling, native integration and earlier experiments |
| `scripts/` | Setup, command-line tools, configuration and launch shortcuts |
| `tests/` | Unit, integration and native game checks |
| `docs/` | Guides, technical notes and license notices |
| `runtime/` | Local game files and generated mod runtime; ignored by Git |
| `artifacts/` | Generated maps, previews, videos and reports; ignored by Git |

See the [repository guide](docs/repository-layout.md) for commands and the layout
inside each project.

## Getting started

Requires Windows, Python 3.11+, a local **BFME2 1.06** installation, and the
openbfme2 launch helpers and compiler toolchain described in the
[setup guide](docs/repository-layout.md#python-and-local-configuration).

1. Copy `scripts/config.example.toml` to `scripts/config.local.toml` and set your
   local paths.
2. Run **`scripts/launchers/Setup bfmeXbar.cmd`** to prepare the runtime.
3. Launch **`Launch bfmeXbar.cmd`**. Use the mouse wheel to move between normal
   gameplay and the strategic view.

Map and battle shortcuts are in `scripts/launchers/`. To build Eight Kingdoms,
use the project environment from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts/bfx.py map build eight-kingdoms
```

Then run **`scripts/launchers/Launch Eight Kingdoms.cmd`**.
Game assets must be supplied locally. Current
validation covers local play; multiplayer compatibility and long matches remain
unverified.

## Further reading

- [Map creation workflow](docs/map-creation-workflow.md)
- [Using a heightmap](docs/heightmap-workflow.md)
- [Native map-file structure](docs/map-format.md)
- [BFME2 integration and technical details](docs/bfme-host.md)
- [License](LICENSE.txt) and [third-party notices](docs/licenses/README.md)

This project is not endorsed by or affiliated with EA or its licensors.
