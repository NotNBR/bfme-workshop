# Recoil experiment

This earlier engine experiment is preserved independently of the BFME2 strategic
patch. `game/` and `client.lua` contain its Lua game code; `tools/` contains its
build and launch scripts. The shared W3D decoder lives in `src/formats/w3d.py`.

The default launchers under `scripts/launchers/` start original BFME2. Recoil setup and launch
remain explicit opt-in operations through this directory's tools. See
[experiment notes](../../docs/research/recoil.md).
