# Native integration decision

Historical research for the earlier Recoil experiment. The accepted host is now the original BFME2 runtime, to preserve its animation, movement, formations and cursor. See [the current integration](bfme-host.md). The Recoil implementation below is retained as an experiment.

Research checked 7 October 2026.

## What the engine-splicing examples actually do

The [Skate 3 / MW2 mashup's implementation notes](https://github.com/chasmlol/2010-rust-rewrite-mashup/blob/main/docs/SKATE.md) describe a reconstructed Skate worker, collision conversion, animation-bank integration, and skeleton retargeting. That is a subsystem integration project with explicit boundaries. It does not establish that two arbitrary retail engine executables can simply be combined.

Practical integration choices are:

1. **Host engine plus adapted subsystems/content.** One engine owns the world, renderer and simulation clock. Assets and selected behavior cross an explicit interface. This avoids two pathfinders or physics systems both owning the same units.
2. **Worker processes.** A second runtime operates behind messages or shared memory. Collision, transforms, input, animation and timing need a documented protocol. This is appropriate when valuable donor behavior can be isolated.
3. **Source-level integration.** Recovered components become libraries in the host. This requires usable source, compatible data structures, and enough complete runtime dependencies to link and test.

For bfmeXbar, the first working step is option 1. A future SAGE behavior worker would be option 2. No such worker is claimed to exist in the current build.

## Why Recoil is the current host

[Recoil](https://github.com/beyond-all-reason/RecoilEngine) provides accessible native engine source and an existing large-scale RTS simulation. Its [game development guide](https://recoilengine.org/docs/guides/getting-started/first-steps-with-the-engine/) documents game packages and engine data directories. This lets us build and test the bridge now.

[FAForever/fa](https://github.com/FAForever/fa) exposes the Forged Alliance Lua game layer. [FA-Binary-Patches](https://github.com/FAForever/FA-Binary-Patches) supplies native binary patches; it is not a complete public source tree for the FA native engine. A verified local FA installation was not found during this work. FA remains a possible donor, but it adds a closed runtime and integration constraints without giving this first experiment a working native foundation.

This choice targets Supreme Commander-style controls and scale. It is **not** a claim that Recoil is the Supreme Commander engine or that their gameplay semantics match.

## The implemented boundary

```text
Local BFME II: INI.big + W3D.big + Textures*.big
                       |
                  read-only import
                       |
          W3D hierarchy + motion-channel decoder
                       |
     S3O bone pieces + texture atlas + sampled pose tables
                       |
       Recoil 2026.07.04 src/native renderer and simulation
```

BFME's skin vertices are stored in bone-local coordinates. The importer rebases each triangle to its selected bone, transforms Z-up/X-forward into Recoil's Y-up/Z-forward basis, and preserves face winding. The animation decoder handles BFME motion channels with time codes and 4/8-bit adaptive deltas. It composes animated offsets with the rest hierarchy and converts resulting poses to native script translation and Y-X-Z rotation.

The inspected `LocalModelPiece::SetPieceSpaceMatrix` implementation only updates its blocking flag, without assigning the supplied transform. The integration therefore uses `Spring.UnitScript.CallAsUnit`, `Move`, and `Turn`, verified through real engine screenshots. This is tied to the inspected version; future engine releases may change the API behavior.

The base-game INI reader maps selected infantry statistics. A Lua battle gadget creates real native units, issues fight orders, and records movement and damage. LuaUI adds strategic-view switching and battalion selection. The original SAGE behavior module graph is not executed.

## openbfme2 reference

The sibling repository was inspected read-only. Relevant material includes:

- `reference/open-bfme-1/game/Libraries/Source/WWVegas/WW3D2/w3d_file.h`: chunk, mesh, hierarchy and animation layouts.
- `Code/Libraries/Source/WWVegas/WW3D2/AdaptiveDeltaLoadW3D.cpp` and BFME2 motion-channel constructor reconstructions: animation-channel interpretation.
- `Code/GameEngine/Source/GameLogic/AI/AIGroupDoCommandButton.cpp`: group-command boundary.
- `Code/GameEngineDevice/Source/W3DDevice/GameClient/W3DViewCameraModFinalZoomBfme.cpp`: BFME camera boundary.

Its ongoing reconstruction is not a complete standalone donor library in this build. File-format interpretation also uses [OpenSAGE's W3D specification](https://github.com/OpenSAGE/Docs/blob/master/file-formats/w3d/index.rst) and [OpenSAGE's animation decoder](https://github.com/OpenSAGE/OpenSAGE/tree/master/src/OpenSage.FileFormats.W3d).

## Remaining engine work

The next substantial boundary is accurate skinned rendering, followed by a narrow recovered SAGE behavior component or worker with deterministic tick/input/output contracts. Battalion formation behavior, powers, upgrades and production should be ported with explicit parity tests rather than silently approximated. Those are future implementation tasks, not existing features.
