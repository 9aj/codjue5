# Contributing

Start with synthetic fixtures. Do not attach COD4 fastfiles, IWDs, exported meshes, raw memory captures, Unreal map assets or private project files to a contribution.

## Local checks

From the repository root:

```powershell
& .\pipeline\build.ps1
& .\pipeline\bin\JumpConvert.exe self-test
python -m unittest discover -s pipeline/tests -v
python tools/check_distribution.py
```

Use Python 3.10 or later. The optional Descent material-coverage test is explicitly skipped when its private fixture is absent; the synthetic geometry tests still run. Passing these checks does not test a live game capture or an Unreal import.

Before proposing a new game build or map profile, document the executable/map hashes, layout evidence, bounds checks, expected failure behaviour and validation performed. Do not loosen memory bounds, remove map identity checks or silently fall back to guessed offsets.

Keep visible geometry, collision and gameplay changes separate and reviewable. New CLI stages should take explicit input/output paths, avoid overwriting earlier runs and write a machine-readable status/report. New reusable helpers must not depend on a private Project Jump folder or Blueprint.

Preserve all upstream copyright notices. Describe modifications to vendored code in `pipeline/NOTICE.md` and credit new dependencies in `CREDITS.md`. Contributions to project-authored code and documentation use GPL-3.0-or-later, consistent with the existing derived tool.
