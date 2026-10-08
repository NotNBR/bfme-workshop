# File structure

BFME2 maps use a chunked binary document with a shared name table. Chunks describe
terrain, objects, sides, scripts, water, cameras and other map state; many records
refer to assets and rules in the installed game rather than embedding them.

| Reference | Use it for |
| --- | --- |
| [Container and terrain format](format.md) | Headers, compression, name IDs, properties, section offsets and spatial units |
| [Versioned reference and coverage](reference.md) | Corpus results, section/version tables, additional record layouts and authoring constraints |
| [Original-map construction findings](ashen-march-findings.md) | How The Ashen March was built without a donor map |
| [Bases and libraries](../players-economy-and-ai/bases.md) | `.bse` files, castle templates and script libraries |

The local audit covers **270 documents**, **23 section names** and **43
section/version pairs** from `Maps.big`, `Bases.big` and `Libraries.big`. Every
observed layout has a decoder and every document preserves its decompressed
bytes on round-trip. Unknown field meanings are retained and labelled.

## Tools

```powershell
python scripts/bfx.py map inspect 'path/to/map.map'
python -m bfmexbar.mapkit.analyze 'path/to/map.map' --out artifacts/map-analysis.json
python -m bfmexbar.mapkit.coverage 'path/to/Maps.big' --out artifacts/map-coverage.json
```

Run from an installed checkout; generated reports stay local. The corpus is not
redistributed. See the [repository setup](../../repository-layout.md#python-and-local-configuration).

## Limits

Observed versions are not an exhaustive list of legal files. Structural decoding
does not establish every field's meaning or permit arbitrary edits. Modern
terrain authoring requires v18; older versions have inspection support. Preserve
unknown data and references, and refuse spatial transforms whose coordinate-bearing
payloads cannot be updated safely. The [reference](reference.md) records the gaps.
