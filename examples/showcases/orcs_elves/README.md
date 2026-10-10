# Orcs versus Elves showcase

`edit.py` preserves the original 29-second showcase finishing workflow.
`src/capture/showcase.py` records it, and
`src/scenarios/orcs_elves.py` prepares the battle.

The historical commands remain available:

```powershell
python scripts/workshop.py play --showcase
python examples/showcases/orcs_elves/edit.py
```

This older showcase keeps `local/artifacts/showcase/` as its output directory.
The revisioned capture/edit CLI currently supports Eight Kingdoms.
