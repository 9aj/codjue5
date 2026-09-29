# Map-specific reference implementations

These scripts document the actual Tunnel approach. **Do not batch-run this directory in a fresh project.** They contain pinned source hashes, historical capture directory names, expected counts, `/Tunnel` content paths and some dependencies on Project Jump's private Unreal assets/plugins.

The scripts live in `reference/pipeline/`, so their `Path(__file__).parents[1]` root is `reference/`. Configure/copy your own capture inputs into the corresponding ignored `reference/artifacts/` tree, or edit the path constants. Personal project paths were replaced with `C:/Path/To/...` placeholders. Original source hashes and count assertions were retained deliberately. Historical timestamp paths identify inputs to replace; they are not included fixtures.

Use source control or a separate project copy. Work with PIE stopped for editor mutations; run `verify_*` and teleport runtime checks in PIE only. Audit scripts for their world assertions before running them. No script should be allowed to silently modify a different loaded map.

## Stage order and dependencies

| Stage | Scripts | Required input / caveat |
|---|---|---|
| Initial world | `build_tunnel_map.py` | Validated world export and replacement manifest; configure `SOURCE`; refuses an existing level; provisional collision is later replaced |
| Surface split | `prepare_tunnel_surfaces.py`, `style_tunnel_world.py` | Prepared world OBJ/material metadata; imports per-material meshes and uses source coordinate convention |
| Brush facts | `extract_tunnel_collision.py` | Fastfile path argument plus configured entity-export path; exact SHA-256 required |
| Sloped collision | `find_tunnel_planes.py` (diagnostic), `reconstruct_tunnel_collision.py` | Decompressed fastfile and collision facts; hard-coded validated plane/side offsets |
| Collision placement | `apply_tunnel_collision.py`, `apply_tunnel_slopes.py` | Reconstructed brush facts / OBJ; correct level loaded |
| Terrain | `extract_tunnel_terrain.py`, `apply_tunnel_terrain.py` | Configure local fastfile path; exact hash and layout checks |
| Props | `decode_tunnel_models.py`, `import_tunnel_models.py` | Separate validated model capture; configure `SOURCE`; decoder then importer |
| Prop collision | `extract_tunnel_model_collision.py`, `apply_tunnel_model_collision.py` | Configured fastfile plus decoded models and placements |
| Teleports | `place_tunnel_teleports.py` | Entity/trigger metadata plus local Blueprint template and graph APIs; implement equivalents for a clean UE project |
| Runtime collision / gameplay | `verify_tunnel_runtime.py`, `verify_tunnel_model_collision.py`, `test_tunnel_teleports.py` | PIE with the appropriate pawn and actors; teleport test temporarily moves the pawn |
| Cave lighting | `prepare_tunnel_cave_lights.py`, `style_tunnel_cave.py`, `polish_tunnel_cave.py`, `tunnel_cave_readability.py`, `balance_tunnel_cave_lights.py` | Prior surface split and expected labels/materials; historical art-pass sequence |
| PBR and sky | `tunnel_pbr_upgrade.py`, `tunnel_storm_sky.py` | Locally prepared texture manifest; see advanced guide; texture compilation takes time |
| Timber details | `build_timber_beam.py`, `tunnel_timber_supports.py` | Offline generated OBJ, PBR materials, light-candidate positions and valid collision for anchoring |
| Local stair edit | `build_tunnel_landing_stairs.py`, `apply_tunnel_landing_stairs.py`, `refine_tunnel_stair_edge.py`, `verify_tunnel_landing_stairs.py` | Exact Tunnel geometry and labels; a case-specific edit, not a general stair generator |

The stair builder includes the final front-edge clipping correction. `refine_tunnel_stair_edge.py` is retained to explain the historical cleanup and is normally unnecessary after a fresh application of the corrected builder. `apply_tunnel_landing_stairs.py` makes a backup, refuses a repeated application, and includes a project-plugin path placeholder that must be configured first.

Some scripts are experimental iterations retained as source examples, not a supported installation sequence. In particular, the first cave styling pass contains a historical before/after snapshot assertion that was investigated during development. Use the algorithms and stage dependencies, then adapt and test them rather than bypassing assertions on an unknown project.

## Running an editor script after configuring it

Enable the Python Editor Script Plugin in your own Unreal project. With the correct map loaded and the required assets available, use Unreal's Python execution facility or its console command:

```text
py "C:/Path/To/codjue5/reference/pipeline/YOUR_CONFIGURED_SCRIPT.py"
```

This is an Unreal command, not a PowerShell command. Check the Output Log and the script's report file for completion. Save and inspect each stage before proceeding. The standalone core export guide does not require these reference scripts.
