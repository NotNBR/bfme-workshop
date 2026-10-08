# BFME Workshop

NotNBR's collection of **Battle for Middle-earth mods, maps and tools**.
Current work focuses on BFME II: a SupCom-style strategic camera, original map
creation, battle scenarios and trailers.

Built with help from [openbfme2 (Open-BFME-2)](https://github.com/Open-BFME/Open-BFME-2),
whose launch helpers, compatibility code and engine research underpin the native integration.

https://github.com/user-attachments/assets/58612ed8-e734-4269-9eae-cec99b559f87

Eight Kingdoms showcase · 76 seconds · 5.77 MB preview ·
[1080p MP4, under 20 MB](projects/showcases/eight-kingdoms/media/Eight-Kingdoms-Trailer.mp4)

## Projects

- **[Strategic mod](projects/strategic/README.md)** — extended zoom centred on the
  cursor, overhead view, unit/building symbols and higher army caps.
- **[Maps](projects/maps/)** — Eight Kingdoms, Ithilien Frontier and The Ashen
  March, with original generators and terrain/scenery work.
- **[Battle scenarios](projects/scenarios/eight-kingdoms-4v4/README.md)** — staged
  battles with established bases, armies, siege and monsters.
- **[Showcases](projects/showcases/eight-kingdoms/README.md)** — camera tours,
  recording, editing, music and video exports.

## Mapping tools and reference

**[BFME II map-file specification](docs/mapping/file-structure/specification.md)**
describes what a map package contains and how its binary data is structured:
compression, chunks, fields, versions, references and companion files.

The [mapping guide](docs/mapping/README.md) organizes authoring tools, file layouts,
verified behavior and remaining work into six areas:

| Area | Contents |
| --- | --- |
| [File structure](docs/mapping/file-structure/README.md) | Containers, sections, properties, versions and format coverage |
| [Terrain and presentation](docs/mapping/terrain-and-presentation/README.md) | Heightmaps, textures, cliffs, water, lighting, scenery and cameras |
| [Navigation](docs/mapping/navigation/README.md) | Passability, slopes, roads, bridges and placement research |
| [Scripts](docs/mapping/scripts/README.md) | Script trees, typed authoring, conditions, actions and native experiments |
| [Players, economy and AI](docs/mapping/players-economy-and-ai/README.md) | Starts, ownership, teams, bases, build lists and libraries |
| [Compatibility](docs/mapping/compatibility/README.md) | Existing validation, screenshot tooling and unverified integration paths |

Playable maps can be created from scratch. All observed layouts across **270
map/base documents** decode and round-trip, but full gameplay semantics and
arbitrary feature authoring remain in progress. Multiplayer, save/load and
long-match compatibility are unverified; further compatibility checks are paused.

## Getting started

Requires **Windows, Python 3.11+, a complete BFME II 1.06 installation**, and the
openbfme2 launch helpers/compiler toolchain described in the
[setup guide](docs/repository-layout.md#python-and-local-configuration).

1. Copy `scripts/config.example.toml` to `scripts/config.local.toml` and configure
   the game, reference-tools and compiler paths.
2. Run **`scripts/launchers/Setup bfmeXbar.cmd`** to prepare the environment and
   isolated runtime.
3. Run **`Launch bfmeXbar.cmd`** for the strategic mod. Use the mouse wheel to
   move between normal gameplay and the strategic view.

**Bring your own game.** Setup uses your configured installation and leaves the
original untouched. It does not download BFME II; an openbfme2 source checkout
alone does not supply the game files. Local configuration and runtime files are
ignored by Git.

To build Eight Kingdoms from the repository root after setup:

```powershell
.\.venv\Scripts\python.exe scripts/bfx.py map build eight-kingdoms
```

Then use `scripts/launchers/Launch Eight Kingdoms.cmd`. See the
[map creation workflow](docs/mapping/workflow.md) for authoring and the
[command guide](docs/repository-layout.md#commands) for other projects.

## Repository layout

| Folder | Contents |
| --- | --- |
| `projects/` | Strategic mod, maps, battle scenarios and showcases |
| `src/` | Shared formats, authoring tools, native integration and capture code |
| `scripts/` | CLI, setup, local configuration and launch shortcuts |
| `tests/` | Unit, integration and native test instructions |
| `docs/` | Six-area mapping reference, project guides and license notices |
| `runtime/`, `artifacts/` | Local game runtime and generated outputs; ignored |

The package and launchers retain the internal name `bfmeXbar`. See the
[repository guide](docs/repository-layout.md) for detailed ownership and commands,
or the [documentation index](docs/README.md) to browse the guides.

Repository code is licensed under [GPL-3.0-only](LICENSE.txt); see
[third-party and media notices](docs/licenses/README.md) for separate terms.
Retail game assets are not included. This project is not endorsed by or affiliated
with EA or its licensors.
