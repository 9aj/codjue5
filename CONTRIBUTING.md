# Contributing

Start with synthetic fixtures. Do not attach COD4 fastfiles, IWDs, exported meshes, raw memory captures, Unreal map assets or private project files to a contribution.

## Local checks

From the repository root:

```powershell
& .\pipeline\build.ps1
& .\pipeline\bin\JumpConvert.exe self-test
python -m unittest discover -s pipeline/tests -v
python -m unittest discover -s map_pipeline/tests -v
python tools/check_distribution.py
```

Use Python 3.10 or later. The optional Descent material-coverage test is explicitly skipped when its private fixture is absent; the synthetic geometry tests still run. Passing these checks does not test a live game capture or an Unreal import.

To check new, unstaged source files too, run `python tools/check_distribution.py --include-untracked`. Create an isolated Unreal project with `python map_pipeline/tests/create_unreal_fixture.py`, build its editor target, and import `map_pipeline/examples/fixture.map` using `pipeline/import-map.ps1`. The `CodMapRuntime.Teleport.DelayAndFeet` Unreal automation test exercises actual overlap, delay, feet positioning and cooldown. Never run fixture commands against a production project's unsaved editor session.

Before proposing a new game build or map profile, document the executable/map hashes, layout evidence, bounds checks, expected failure behaviour and validation performed. Do not loosen memory bounds, remove map identity checks or silently fall back to guessed offsets.

Keep visible geometry, collision and gameplay changes separate and reviewable. New CLI stages should take explicit input/output paths, avoid overwriting earlier runs and write a machine-readable status/report. New reusable helpers must not depend on a private Project Jump folder or Blueprint.

Preserve all upstream copyright notices. Describe modifications to vendored code in `pipeline/NOTICE.md` and credit new dependencies in `CREDITS.md`. Contributions to project-authored code and documentation use GPL-3.0-or-later, consistent with the existing derived tool.

Project Jump regression tests cover content-only plugin ownership, layout and prohibited collision/scale settings. Validate and package a synthetic content plugin with the actual kit before changing its Blueprint generator. The isolated `CodMapRuntime.ContentOnlyTeleport` automation test accepts `-CodJueTeleportTestClass=/Plugin/Generated/Gameplay/BP_Name.BP_Name_C` to exercise a generated Blueprint. Keep that C++ test harness in the isolated fixture project; never add CodMapRuntime to a Project Jump map pack.

For fixed-coordinate or instant teleport fixtures, the test also accepts `-CodJueExpectedDestination="X=... Y=... Z=..."` (including the pawn half-height) and `-CodJueInstantTeleport`. Run it against an isolated project with only the generated content Blueprint copied into its content plugin.
