# Eight Kingdoms 4v4 scenario

This playable midgame setup is shared by normal play and trailer capture.
`scenario.toml` selects the map and data files. `armies.json` defines the factions,
battalion templates, heroes and heavy units. `buildings.json` defines each
faction's eight additional completed structures. `deployments.json` sets the
seed, four front anchors, approach axes and teams.

`bfmexbar.scenarios.placement` validates foundations, approach lanes and template
availability against the installed map and game assets. Generated positions go
into a run's `battle-plan.json`. The native runtime adapter is
`src/bfmexbar/scenarios/kingdoms.py`; native staging is in
`src/native/scenarios/kingdoms.inc`.

```powershell
python scripts/bfx.py scenario plan eight-kingdoms-4v4
python scripts/bfx.py scenario play eight-kingdoms-4v4
```

Camera timing, titles and music belong in `projects/showcases/eight-kingdoms/`.
