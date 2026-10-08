# Eight Kingdoms showcase

The [showcase trailer](media/Eight-Kingdoms-Trailer.mp4) is the revision-3
1080p, 76-second export, compressed to 18,959,430 bytes (under 20 MB).
This selected video is tracked in `media/`; generated captures and other exports
remain in the ignored `artifacts/` directory.

`project.toml` selects the scenario, native capture format and map portrait.
`shots.json` defines camera start/end positions, spans, elevations and frame
counts. Positions can anchor to a front from the generated battle plan.
`titles.json` supplies one chapter and title per shot. `score.py` contains the
original synthesized music; `edit.py` defines the visual edit. `exports.toml`
contains master, mobile and under-20-MB encoding settings.

```powershell
python scripts/bfx.py showcase capture eight-kingdoms --run-id r005
python scripts/bfx.py showcase edit eight-kingdoms --run-dir artifacts/showcases/eight-kingdoms/r005
```

The editor requires a passing native capture report. Completed runs are preserved;
use another run ID for another take. Encoding and full-frame checks are shared
through `src/bfmexbar/video/encoding.py`. The original
`src/tools/bfme_host/finish_kingdoms_trailer.py` command remains a compatibility entry
point using its old output directory.

See [repository layout](../../../docs/repository-layout.md) for the output tree and
the standalone size-limited export command.
