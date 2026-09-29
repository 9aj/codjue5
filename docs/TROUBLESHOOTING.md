# Troubleshooting

| Symptom | Check / next step |
|---|---|
| `csc.exe` not found | Pass `build.ps1 -Compiler` the installed Visual Studio Roslyn compiler path. Do not use an arbitrary downloaded executable. |
| PowerShell blocks a script | Review the script and use your organisation's approved local script policy/signing process. This project does not change execution policy for you. |
| No process listed | Load the map in COD4 multiplayer and confirm the process is `iw3mp`. The exporter does not launch COD4. |
| Cannot open/read process | Ensure the selected PID is current and game/tool run under compatible permissions. Use the minimum privileges needed; inspect diagnostics before retrying. |
| `unsupported build`, `Cannot read COD4 memory`, invalid counts or unloaded/changing map | Keep the expected map loaded locally, re-list the PID and retry into a new capture directory. If it persists, treat that build/layout as unsupported. Keep diagnostic status/probe files; never disable checks or guess addresses. |
| Geometry capture works but props do not | Use the separate `capture-models` command. Legacy `-IncludeModelPlacements` is optional and failed on our Descent case. World export does not include prop meshes. |
| Only partial files appeared | Inspect `status.json`; only `validated_export` runs are accepted for world import. Partial files are kept intentionally. |
| Map is 2.54 times too large | World OBJ positions were already converted to centimetres. Import at scale 1. Placement metadata is different: it remains in source units. |
| World and props/collision are mirrored | Calibrate one coordinate convention. Our legacy OBJ path maps `(x,y,z)` to `(x,-y,z)`; don't mirror the world twice. |
| Missing surfaces / inside-out faces | Inspect material coverage, sky filtering, winding and normals. Do not infer playable geometry from material sort keys. A two-sided material is not a winding repair. |
| Player hits invisible walls | Remove provisional whole-map convex collision and inspect recovered collision actors. Check that visible meshes and recovered collision are not both blocking. |
| Thin slopes or edge probes miss | Check coordinate precision, triangle area and winding; inspect slivers separately. Do not suppress broad collision failures because some degenerate triangles are expected. |
| Python reports `No module named unreal` | Run editor scripts in Unreal's Python environment with its Python Editor Script Plugin enabled, not ordinary system Python. Offline extractors use ordinary Python. |
| Missing `/Tunnel` content path | The reference workflow used a content-enabled Tunnel plugin. Create/configure your own content mount or adapt paths to `/Game/...`; these scripts are not a plugin installer. |
| Missing Blueprint, TimerZone or graph API | That script depends on Project Jump's local project/plugins. Implement the equivalent gameplay actor in your project; it is not a generic UE dependency. |
| Texture queries report 32 x 32 during import | Wait for compression/compilation and streaming to settle, then inspect the texture asset and repeat the resolution check. |
| A manual edit disappears | A historical import/collision script may have restored the baseline. Keep explicit stage order and backup before rerunning scripts. |

When reporting an issue, provide the failing command, tool commit, UE version/importer, map identifier, game executable hash, map hash and redacted error text. Do not upload map files, memory captures, private local paths or original game assets into a public issue.

## Known limits

- Two known asset-pool addresses are probed; this is not support for every COD4/CoD4x build.
- Full conversion requires map-specific collision and gameplay work.
- The repository does not include Project Jump movement, Unreal Blueprints, map assets or texture downloads.
- Original collision data does not reconstruct the exact editable Radiant brush/patch source.
- Static-model capture is LOD0-focused; skins, foliage opacity and other asset behaviours require further work.
- The Tunnel case study's local tests are historical evidence, not a clean-room end-to-end test of every reference script in a fresh UE project.
