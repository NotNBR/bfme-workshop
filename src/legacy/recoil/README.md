# Recoil experiment

This earlier engine experiment is preserved independently of the BFME2 strategic
patch. `game/` and `client.lua` contain its Lua game code; `src/tools/` contains its
import, build and launch scripts. Existing `src/tools/native/` paths forward here.

The default root launchers still start original BFME2. Recoil setup and launch
remain explicit opt-in operations through this directory's tools. See
[experiment notes](../../../docs/recoil-experiment.md).
