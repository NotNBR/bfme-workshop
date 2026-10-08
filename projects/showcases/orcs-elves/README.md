# Orcs versus Elves showcase

`edit.py` preserves the original 29-second showcase finishing workflow.
`src/bfmexbar/capture/showcase.py` records it, and
`src/bfmexbar/scenarios/orcs_elves.py` prepares the battle.

The historical commands remain available:

```powershell
python scripts/bfx.py play --showcase
python src/tools/bfme_host/finish_showcase.py
```

This older showcase keeps `artifacts/showcase/` as its output directory.
The revisioned capture/edit CLI currently supports Eight Kingdoms.
