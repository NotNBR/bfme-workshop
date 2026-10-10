# Consolidated feature inventory

The project is named **bmfe-workshop**. The consolidation combines the primary
checkout and the newer development worktree into one working source tree.

The source combines the newer worktree's committed and uncommitted additions
with features still present only in the older checkout.

## Retained features

| Area | Retained additions |
| --- | --- |
| Unit capacity and starting funds | Configurable starting money/capacity, economy overlay, direct-skirmish settings, native startup readback and regression checks |
| Strategic symbols, Greywater and graphics | Latest footprint unions, motion smoothing, subtle borders, hero stars, building markers, Greywater heightmap/forests/routes and graphics tooling |

The Crown of Cardolan's generator, documentation, launcher, native package and
captures were recovered from the older checkout too. Lighting, navigation,
script authoring, Eight Kingdoms, scenario and showcase tooling use the newer
canonical implementations.

## Current ownership

- Shared tooling and component tests: `src/`
- Strategic native source and configuration: `mods/strategic/`
- Maps, scenarios and showcases: `examples/`
- Browser prototype: `examples/browser/`
- Recoil experiment: `mods/recoil/`
- Local runtimes, imported content and captured output: ignored `local/`

Launchers use `scripts/workshop.py` and this checkout's `local/venv`. Current
source does not depend on the sibling worktree.

## Recovery

The earlier source is preserved in the local branch
`codex/preserve-main-before-consolidation`. Original inventories and snapshots
live in `local/cache/previous/consolidation/`; the pre-layout consolidated source
and move inventory live in `local/cache/restructure/`. Replaced local data is
retained in the former consolidation cache.

The sibling worktree remains available as a recovery copy. Future development
uses the primary checkout. No changes have been pushed remotely.
