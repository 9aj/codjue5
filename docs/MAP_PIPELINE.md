# Import a Radiant .map into Unreal

The `map_pipeline` path reads the source map directly. Each brush and patch gets its own Static Mesh asset and actor. Moving a wall moves only that source object, including its attached teleport trigger. This path does not use a previously imported full-map mesh.

The everyday entry point is `./codue5 mp_mymapname`. On first use, it asks for local paths, installs/builds the runtime and saves ignored local settings. Use `./codue5 -SetupOnly` to configure without importing, or `-DryRun` to inspect settings. The detailed commands below expose individual stages for diagnostics and custom workflows.

## Requirements

Windows, Python 3.10+, an Unreal project with Python Editor Script Plugin enabled, and Unreal Editor. Geometry imports do not require the native runtime. Teleports require the included CodMapRuntime C++ plugin, a C++ editor target, and the compiler/SDK dependencies required by your Unreal installation. The runtime was developed against UE5.8.

Save and close the destination Unreal project before importing. The command launches an isolated editor process, checkpoints the import, then launches another editor process to verify the saved level. It refuses an already open destination project.

## One command per map

To dump directly from an installed IW3xo client, then prepare and import that fresh snapshot:

```powershell
.\Import_Map.cmd -Cod4Root 'C:\Games\Call of Duty 4' -MapName mp_example `
  -Mod 3xp_cj -Project 'C:\Projects\MyGame\MyGame.uproject' `
  -Editor 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe' `
  -Config 'C:\Maps\my_map.config.json' -Open
```

Use the actual folder name under `Mods`: `3xp_cj` is the default; `-Mod` also accepts other installed mods. The game and map files must already be installed. The dump runs in `iw3xo.exe`; Radiant is the editor used to open the output, and does not need to run for capture.

If IW3xo is missing, install the **full package** from the [official releases](https://github.com/xoxor4d/iw3xo-dev/releases) into the CoD4 folder first. The installed `iw3x.dll` must include the modified whole-map exporter with `mapexport_useFilters`. The capture checks this capability and records the DLL hash; it does not silently replace your installation. Build/deploy the exporter from the companion modified `iw3xo-dev` source checkout when this check fails. A release package alone may not contain those modifications.

The launcher uses `+set fs_game "mods/<mod>" +devmap <map> +exec <unique config>`. The generated config waits for map loading, sets `r_drawCollision 3`, waits again, enables all six geometry/entity/model write settings with `mapexport_useFilters 0`, and invokes `mapexport`. Each `wait` occupies one game frame, avoiding reliance on client-specific `wait N` behavior. The capture caps `com_maxfps` at 60 for predictable default waits; increase `-LoadFrames` or `-CollisionFrames` for a slow machine. Defaults are 600 and 180 frames. These are initialization delays rather than proof the map loaded; a fresh validated export is the success condition.

The exporter writes `<CoD4 folder>/iw3xo/map_export/<map>.map`. Capture preserves an existing export as `previous.map`, waits for a new write, then requires three seconds of stable size/time and exclusive read access before taking `source.map`. Balanced geometry and a worldspawn are checked before importing. An old file, an empty dump or an incomplete file is never accepted. `capture-result.json` records the source hash, object/entity counts, launch details and installed DLL hash. Preparation still reports any invalid individual brushes or unsupported gameplay.

Run capture alone with:

```powershell
.\pipeline\dump-map.ps1 -Cod4Root 'C:\Games\Call of Duty 4' -MapName mp_example
```

Captures use fresh directories under `artifacts/captures`. `-CaptureOutput` selects a new explicit directory; existing directories are refused. `-DumpTimeoutMinutes` defaults to ten. After a validated snapshot is saved, capture closes the game process it launched before continuing to Unreal. It requests a normal window close, then terminates that process if it has not exited within ten seconds. Pass `-LeaveGameOpen` to keep it running. Failed captures and timeouts leave the game open for inspection; an existing game client is never interrupted. Temporary configs are removed from the mod directory after the attempt; a copy remains in the capture directory for inspection. No console copy/paste is needed.

To import an existing `.map` instead:

```powershell
.\Import_Map.cmd -MapFile 'C:\Maps\my_map.map' `
  -Project 'C:\Projects\MyGame\MyGame.uproject' `
  -Editor 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe' `
  -Config 'C:\Maps\my_map.config.json' -Open
```

Config is optional. Start from `map_pipeline/examples/config.json`, replacing its demonstration material and teleport names. Config paths resolve relative to the config file. No map names or teleport destinations are embedded in the importer.

The output contains a source snapshot, one OBJ per source object, `manifest.json`, editor logs and `unreal-result.json`. The default output directory is under `artifacts/map-import`. Use a different `-Output` when changing configuration or input assets: existing outputs belong to their original input fingerprint. Rerunning identical inputs resumes incomplete work and verifies completed imports again.

Generated Unreal assets live under `/Game/CodMaps/<map_id>`, including `Map_<map_id>`. The importer refuses to replace an unowned level or asset. Set `map_id` explicitly to choose a stable namespace; use another ID/output when preserving an earlier conversion.

For preparation without Unreal:

```powershell
python -m map_pipeline prepare 'C:\Maps\my_map.map' --output artifacts/my-map --config 'C:\Maps\my_map.config.json'
python -m map_pipeline validate artifacts/my-map/manifest.json
python -m map_pipeline extract-assets 'C:\Maps\my_map.iwd' --output artifacts/my-assets
python -m map_pipeline extract-assets 'C:\Maps\my_map.ff' --output artifacts/my-assets
```

## Collision, materials and lighting

Axis-aligned box brushes receive box collision. Other solid brushes receive a single convex hull; patch surfaces default to triangle collision. `surface_collision: "dop26"` selects 26-DOP collision for patch surfaces. `object_overrides` can select `box`, `convex`, `triangles`, `dop26` or `none` per source object ID. Box collision around an irregular floor can make the player float; triangle collision preserves its surface, while simplified hulls require playtesting.

Tool surfaces retain their semantic purpose: caulk is hidden, playerclip blocks players, and trigger volumes are hidden without blocking players. A trigger receives a separate overlap component when configured as a teleport. Ladder and other unsupported gameplay semantics are reported for implementation.

Brush UVs are reconstructed from the map face texture definitions, and patch UVs are preserved. Missing exporter data cannot be recovered from geometry alone: some IW3XO exports contain zero patch UVs or caulk in place of original patch materials. Inspect those source limitations before judging a texture import.

Materials support an explicit `texture`, existing `unreal_asset`, or RGB `color`, plus `roughness`. `texture_roots` enables exact-basename matching, including decoded `.iwi_out` names; ambiguous matches fail. Missing matches are reported and use a neutral fallback. Lighting includes a movable sun, skylight, atmosphere and fixed exposure; `sun_intensity`, `skylight_intensity` and `ambient_emission` are configurable. Optional `sky.faces` accepts six images named `ft`, `bk`, `lf`, `rt`, `up`, `dn`, with `sky.orientation` for rotations/reflections.

## Teleports and other entities

Install and build the runtime once per destination project:

```powershell
.\pipeline\install-map-runtime.ps1 -Project 'C:\Projects\MyGame\MyGame.uproject' `
  -Engine 'C:\Program Files\Epic Games\UE_5.8'
# If Unreal selects an older compiler, add -CompilerVersion '<installed version>'.
```

Native `trigger_teleport` entities with unique targets can be linked automatically. Script-driven triggers use explicit config bindings:

```json
{"teleports": [{"trigger": "enter", "target": "exit", "delay": 0.1,
                "set_view": true, "cooldown": 0.5}]}
```

Omit `target` to use each matching trigger entity's own target property. An `entity_id` selector can disambiguate trigger names. Targets must resolve uniquely. Player destinations interpret source origins as feet by default, adding capsule half-height at runtime. Cooldowns prevent portal cycles; delayed teleports check that the pawn remains inside the trigger.

GSC files listed in `scripts` are audited for candidate teleport relationships. Candidates require explicit bindings and are never executed. Arbitrary GSC logic, moving platforms, checkpoints and custom movement mechanics need Unreal implementations. `models` maps a source model name to an existing Unreal Static Mesh asset. Unmapped models and unimplemented entities remain in the manifest/report; origin entities also receive metadata markers.

## Verification and limits

Preparation rejects malformed or unsupported geometry by default. `allow_fallback_hulls: true` explicitly permits conservative corner hulls for brushes whose original planes cannot form a closed solid; each is reported. `-AllowPartial` explicitly permits missing geometry and should be used only for diagnosis.

The fresh-editor verification checks source actor counts, unique mesh assets, bounds, material assignments, collision settings, teleport destinations and independent actor movement. It does not prove collision feel or actual gameplay. Playtest with your project's pawn and movement system before publishing.

Asset extraction supports IWD/ZIP image/script files, a restricted COD4 IWI v6 DXT1 format, and source GSC text in supported IWffu100 v5 fastfiles. Unsupported formats are reported. It is not a universal fastfile, texture or model decoder.

Run synthetic tests with `python -m unittest discover -s map_pipeline/tests -v`. The example map is synthetic; game assets and converted levels are not distributed.

Validation performed on UE5.8: the four-object synthetic fixture imported and reloaded with unique meshes, correct materials and independent actor movement. Separate imports exercised box, triangle, convex and 26-DOP collision. The native teleport automation test passed overlap activation, delay, capsule feet positioning and cooldown without warnings. Python has 24 passing tests. A Descent diagnostic import verified 144 valid brushes and explicitly reported six degenerate source brushes. An automated live IW3xo capture of Qube under `3xp_cj` produced 8,908 objects, 146 entities and no unsupported geometry blocks, with the same hash as the previously verified reconstruction. Qube preparation produced all 8,908 source objects (3,304 brushes and 5,604 patches), 14 configured teleport links and 22 flagged fallback hulls; this preparation result is not a full Unreal import or playtest of Qube through this new pipeline.
