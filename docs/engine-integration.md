# Engine integration research

Research checked on **7 October 2026**, using primary project documentation. The implementation here is a local playable prototype, with no Recoil, Godot, or Supreme Commander runtime integration yet.

## Findings

| Approach | What actually gets shared | Implications for bfmeXbar |
|---|---|---|
| Port data and mechanics into one RTS engine | Converted assets/definitions and rewritten behavior | Most promising production direction: Recoil owns simulation, pathfinding and multiplayer; BFME concepts become unit definitions and game rules. |
| Embed a native subsystem in a host engine | A library API with explicit ownership | Godot's GDExtension can load native libraries, but it does not turn an incomplete retail executable reconstruction into a callable RTS library. |
| Run engines as separate processes | Commands and snapshots over an explicit protocol | Useful for tooling or visualization. One process must own gameplay; letting both resolve combat/pathfinding creates reconciliation problems. |
| Directly merge engine source trees | Source-level integration of loops, allocators, scene objects, rendering and networking | High maintenance cost, especially while one side still targets a particular historical executable ABI. |

Recoil documents a separation between synchronized simulation code and local interface code. Its game layer supports Lua rules and UI handlers; widgets/gadgets are conventions built on those entry points. This offers a concrete location for battalion rules and strategic controls. [Recoil: widgets and gadgets](https://recoilengine.org/docs/guides/getting-started/widgets-and-gadgets/).

Recoil's network model sends commands and reproduces the simulation on clients. Its documentation explicitly discusses hardware consistency and cascading desynchronization. **Inference:** keeping BFME and Recoil as independent authoritative simulations would defeat this model; the integration needs one owner of state and time. [Recoil: netcode overview](https://recoilengine.org/articles/netcode-overview/).

Godot's native extension interface loads shared libraries at runtime. That is a subsystem integration mechanism, not an automatic engine merger. An extracted BFME parser or simulation library could eventually use such a boundary if its dependencies were isolated. [Godot: GDExtension](https://docs.godotengine.org/en/stable/engine_details/engine_api/gdextension/what_is_gdextension.html).

OpenRA provides an instructive historical example: after original C&C source became available, the developers described using it as behavioral reference and translating concepts because the architectures differed. This is historical evidence from 2020, not a new 2026 announcement. [OpenRA developer discussion](https://www.openra.net/news/devblog-20200629/).

Recoil is actively published as a standalone RTS engine, with source, releases and build instructions. Its base installation does not itself provide the BFME-specific content and rules needed for this game. [Official Recoil repository](https://github.com/beyond-all-reason/RecoilEngine).

## Local evidence

Inspected `D:/LAN/openbfme2` at commit `2c6473861e7f437a13a4e3e622284873ec06b1b6` (the source repository continued receiving unrelated updates during this task).

- `README.md` describes byte-for-byte reconstruction of BFME2 1.06's `game.dat` and a roadmap that still includes source completion, larger maps and multi-CPU support.
- `docs/discord-progress.json` listed 11,720 unresolved symbols and 2,035,506 linked bytes in its recorded census. Those are progress indicators, not proof of a standalone reusable simulation library.
- `Code/GameEngine/Source/GameLogic/AI/AIGroupDoCommandButton.cpp` demonstrates group command dispatch to member objects. The prototype independently implements the battalion-to-individual command concept.
- `Code/GameEngineDevice/Source/W3DDevice/GameClient/W3DViewCameraModFinalZoomBfme.cpp` exposes recovered camera behavior and retail object offsets. The prototype has its own unrestricted strategic camera; it does not patch those offsets.
- `D:/LAN/bfme2/INI.big` contains readable unit and horde definitions. `Textures*.big` contains portrait textures referenced through INI `MappedImage` definitions. The implemented adapter reads these actual local archives.

No files in either source installation were changed. No engine code, `game.dat`, or retail model archives were copied into the new Git history.

## Chosen first implementation

`INI.big + optional texture archives → local content JSON/PNGs → fixed-step Simulation → Canvas renderer and DOM command UI`.

The content adapter is isolated from simulation. Camera and selection are local presentation state. A command carries squad IDs, kind, destination, and append/replace semantics. Individual units resolve attacks in a spatial grid. The simulation is seeded and tested for repeatability/save continuation in the same JavaScript runtime; this is **not** a cross-platform multiplayer determinism claim.

This smaller runtime makes the core controls and large battle loop directly playable on the installed tools. It validates the requested interaction and data-import path without requiring an unfinished engine rebuild. Its renderer and movement are placeholders for a full 3D RTS implementation.

## Production direction

For a real BAR/Recoil-based conversion, the next concrete milestone is a separately tested Recoil game package with a terrain map, one converted/skinned BFME unit, animation, weapon and a controllable battalion. Port the normalized content to UnitDefs/WeaponDefs, implement battalion coordination in synchronized rules, and implement selection/formation/zoom in the UI layer. Verify scale with engine pathfinding and collisions enabled before claiming production battle capacity.

Then add BFME archive precedence and inheritance, model/material/animation conversion, counter/armor tables, builders and structures, fog of war and faction powers. Multiplayer follows after the synced rules are deterministic. Recoil integration and these milestones remain unimplemented; this repository does not contain an untested stub advertised as a working second engine.
