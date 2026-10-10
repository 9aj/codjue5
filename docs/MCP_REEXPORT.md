# Live Project Jump re-export

The movement contract follows https://project-jump.github.io/#movement (checked 2026-10-10): 2.54 cm per unit, boxes or convex hulls, no sphere/capsule mixed into movement meshes, default Kill Z, and `Slick` tags authored before PIE.

Project Jump convex source brushes use Geometry Script convex hull generation with simplification and sphere/capsule detection disabled. Voxel decomposition is unsuitable for these brushes: Echo's first runtime audit rejected five approximate hulls as nonconvex; direct source hulls passed. Surface/DOP approximations still require playtesting.

Prepare a fresh output folder using `python -m map_pipeline prepare SOURCE --output OUTPUT --config CONFIG`. Set `profile` to `project_jump` and `plugin_name` to the existing permanent plugin identity. Map materials through `materials.<source>.unreal_asset` to preserve existing material designs. Set `nanite` to the intended existing policy.

In the connected editor, open the destination map and stop PIE. Use VibeUE `execute_python_code`, starting with `import unreal`; add the codjue5 directory to `sys.path`. Call:

```python
from map_pipeline.unreal_mcp_import import stage, apply
stage(manifest_path, expected_project_path, 'R_unique_revision')
# Verify stage completion before applying.
apply(manifest_path, expected_project_path, 'R_unique_revision')
```

The staging call imports fresh assets below the map plugin's Generated/revision folder. Apply checks the project/map and saves an unreferenced recovery world under `/Game/Developers/Codjue5Backups/<Plugin>/`, outside PackageMod's map scan. It swaps mesh assets on existing source-owned actors in place. Actor identity, authored location/rotation/scale, attachments, tags, visibility, collision profiles, material overrides, and other actors remain intact. Absent source actors are recorded and skipped: an editor deletion must not be silently undone. Resetting the layout to source coordinates or restoring absent objects requires a separate explicit workflow. Earlier assets remain available to the backup. This path never launches, restarts or quits Unreal.

The checkpoint records pre-refresh transforms. Saved-level verification compares against those authored transforms, rather than assuming that the `.map` coordinates are the intended editor layout.

Rectangular brushes use analytic box collision, including exact oriented boxes. The exporter verifies all eight corners and orthogonal axes within 0.001 cm; wedges and sheared prisms retain their source convex hull. A box's rendered mesh still consists of triangles. Rendering wireframe does not show the collision representation.

Verification audits every pawn-blocking static mesh component, including hand-added environment meshes. Empty simple collision is an error even when the runtime log reports no skipped shapes. Concave environment geometry needs multiple collision pieces and a fresh runtime check: automatic decomposition can still produce hulls CmWorld rejects. Do not silently substitute one enclosing box, change source ledges, or report a successful shape-count audit as a successful bounce test.

Wrap mutations with VibeUE WorkflowService start_run/finish_run. After applying, call `map_pipeline.unreal_verify.main()` with `CODJUE_MANIFEST` set; call functions directly, or set `CODJUE_QUIT=0` before executing entrypoint scripts in a live editor. No changed Blueprint is needed for a geometry-only re-export.

Finally start PIE with an explicit spawn transform at the authored PlayerStart (avoid default-filled zero transforms), read the fresh CmWorld log segment, and capture the game with VibeUE `capture_image`. Require zero skipped source collision elements and inspect the player at the platform. Save/reload and shape counts alone cannot establish movement compatibility. Stop PIE and restore background throttling afterward. A spawn and brush-conversion check does not establish full-route bounce/elevator completion.

Duplicating a World leaves a resident map package: release its Python World reference and use `EditorLoadingAndSavingUtils.unload_packages` before any level reload. Garbage collection alone does not unload it.
