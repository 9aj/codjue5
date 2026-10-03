# Import a Radiant .map into Unreal

The `map_pipeline` path reads the source map directly. Each brush and patch gets its own Static Mesh asset and actor. Moving a wall moves only that source object, including its attached teleport trigger. This path does not use a previously imported full-map mesh.

The everyday entry point is `./codue5 mp_mymapname`. On first use, it asks for local paths, prepares content-only Project Jump map plugins and saves ignored local settings. Use `./codue5 -SetupOnly` to configure without importing, or `-DryRun` to inspect settings. The detailed commands below expose individual stages for diagnostics and custom workflows.

## Requirements

Windows, Python 3.10+, Unreal Engine 5.8.x and the supplied compiled Project Jump Map Kit. The importer enables Python transiently; it does not edit the kit project or install native map modules. Follow the [official mapping guide](https://project-jump.github.io/). The optional generic profile requires a C++ project and CodMapRuntime for teleports and is not a Project Jump mod.

Save and close the destination Unreal project before importing. The command launches an isolated editor process, checkpoints the import, then launches another editor process to verify the saved level. It refuses an already open destination project.

## One command per map

To dump directly from an installed IW3xo client, then prepare and import that fresh snapshot:

```powershell
.\Import_Map.cmd -Profile project_jump -Cod4Root 'C:\Games\Call of Duty 4' -MapName mp_example `
  -Mod 3xp_cj -Project 'C:\ProjectJump\MapKit\project_jump.uproject' `
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
.\Import_Map.cmd -Profile project_jump -MapFile 'C:\Maps\my_map.map' `
  -Project 'C:\ProjectJump\MapKit\project_jump.uproject' `
  -Editor 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe' `
  -Config 'C:\Maps\my_map.config.json' -Open
```

Config is optional. Start from `map_pipeline/examples/config.json`, replacing its demonstration material and teleport names. Config paths resolve relative to the config file. No map names or teleport destinations are embedded in the importer.

The output contains a source snapshot, one OBJ per source object, `manifest.json`, editor logs and `unreal-result.json`. The default output directory is under `artifacts/map-import`. Use a different `-Output` when changing configuration or input assets: existing outputs belong to their original input fingerprint. Rerunning identical inputs resumes incomplete work and verifies completed imports again.

Project Jump assets live in `Plugins/<PluginName>/Content`, with the level at `Content/Maps/<PluginName>.umap` and generated assets under `Content/Generated`. Plugin names contain letters/digits only and must remain stable after publication; `mp_example` becomes `mpexample`. Configure `plugin_name` before the first import to choose another identity. Ownership receipts refuse changed input fingerprints or unowned content, protecting manual edits. A changed-source reimport requires review rather than silently overwriting the plugin. The low-level importer defaults to `generic` for compatibility: select `-Profile project_jump` explicitly. Generic output uses `/Game/CodMaps/<map_id>`.

For preparation without Unreal:

```powershell
python -m map_pipeline prepare 'C:\Maps\my_map.map' --profile project_jump --map-id mp_example --output artifacts/my-map --config 'C:\Maps\my_map.config.json'
python -m map_pipeline validate artifacts/my-map/manifest.json
python -m map_pipeline extract-assets 'C:\Maps\my_map.iwd' --output artifacts/my-assets
python -m map_pipeline extract-assets 'C:\Maps\my_map.ff' --output artifacts/my-assets
```

## Collision, materials and lighting

Axis-aligned box brushes receive box collision. Other solid brushes receive a convex hull; Project Jump patches default to 26-DOP collision. Project Jump rejects triangle collision and scales other than 2.54 cm per source unit. Its movement requires boxes/convex shapes; inspect curved or concave surfaces because one hull can bridge empty space. `object_overrides` selects `box`, `convex`, `dop26` or `none` by source object ID, and `"slick": true` adds the Slick actor tag. Generic mode also permits triangle collision. Default Kill Z is preserved in Project Jump mode.

Tool surfaces retain their semantic purpose: caulk is hidden, playerclip blocks players, and trigger volumes are hidden without blocking players. A trigger receives a separate overlap component when configured as a teleport. Ladder and other unsupported gameplay semantics are reported for implementation.

Brush UVs are reconstructed from the map face texture definitions, and patch UVs are preserved. Missing exporter data cannot be recovered from geometry alone: some IW3XO exports contain zero patch UVs or caulk in place of original patch materials. Inspect those source limitations before judging a texture import.

Materials support an explicit `texture`, existing `unreal_asset`, or RGB `color`, plus `roughness`. `texture_roots` enables exact-basename matching, including decoded `.iwi_out` names; ambiguous matches fail. Missing matches are reported and use a neutral fallback. Lighting includes a movable sun, skylight, atmosphere and fixed exposure; `sun_intensity`, `skylight_intensity` and `ambient_emission` are configurable. Optional `sky.faces` accepts six images named `ft`, `bk`, `lf`, `rt`, `up`, `dn`, with `sky.orientation` for rotations/reflections.

## Teleports and other entities

Project Jump teleports are generated as content-only Blueprints derived from the engine TriggerBox. They use engine Actor/component calls, Pawn overlap, delays, shared cooldown tags and an overlap recheck. No game controller classes or native map modules are used. Trigger shapes use bounding boxes; verify irregular triggers and multiplayer behavior in playtests.

Only for `-Profile generic`, install and build the native runtime once per destination project:

```powershell
.\pipeline\install-map-runtime.ps1 -Project 'C:\Projects\MyGame\MyGame.uproject' `
  -Engine 'C:\Program Files\Epic Games\UE_5.8'
# If Unreal selects an older compiler, add -CompilerVersion '<installed version>'.
```

Native `trigger_teleport` entities with unique targets can be linked automatically. Script-driven triggers use explicit config bindings:

```json
{"teleports": [{"trigger": "enter", "target": "exit", "delay": 0.1,
                "set_view": false, "cooldown": 0.5}]}
```

For script teleports to fixed coordinates, use `"destination": [x, y, z]` and optional `"angles": [pitch, yaw, roll]` instead of `target`. Values use COD4 source units and axes; the importer applies scale and coordinate conversion.

Omit `target` to use each matching trigger entity's own target property. An `entity_id` selector can disambiguate trigger names. Targets must resolve uniquely. Player destinations interpret source origins as feet by default. Project Jump Blueprints add colliding actor bounds half-height at runtime; generic native teleports use capsule half-height. Forced controller/view rotation is reported as unported in Project Jump mode; no game controller calls are emitted. Cooldowns prevent portal cycles; delayed teleports check that the pawn remains inside the trigger.

GSC files listed in `scripts` are audited for candidate teleport relationships. Candidates require explicit bindings and are never executed. Arbitrary GSC logic, moving platforms, checkpoints and custom movement mechanics need Unreal implementations. `models` maps a source model name to an existing Unreal Static Mesh asset. Unmapped models and unimplemented entities remain in the manifest/report; origin entities also receive metadata markers.

## Verification and limits

Preparation rejects malformed or unsupported geometry by default. `allow_fallback_hulls: true` explicitly permits conservative corner hulls for brushes whose original planes cannot form a closed solid; each is reported. `-AllowPartial` explicitly permits missing geometry and should be used only for diagnosis.

The fresh-editor verification checks source actor counts, unique mesh assets, bounds, material assignments, collision settings, teleport actors and independent actor movement. Project Jump also verifies plugin layout and default Kill Z, checks the kit project descriptor stayed unchanged, and runs the kit Blueprint validator when available. Playtest with the kit movement system before publishing.

Place Start/Finish TimerZones for each route and optional `<LevelName>_Info` metadata in the kit; routes and difficulty cannot be inferred safely from geometry. Run `./codue5 mp_example -Package` for the official PackageMod validator and DLC cook (CMD when available, otherwise the supplied PowerShell tool). Validation is never bypassed. Review dependency migration and the packaged result. Workshop publication is a separate in-game step.

Asset extraction supports IWD/ZIP image/script files, a restricted COD4 IWI v6 DXT1 format, and source GSC text in supported IWffu100 v5 fastfiles. Unsupported formats are reported. It is not a universal fastfile, texture or model decoder.

Run synthetic tests with `python -m unittest discover -s map_pipeline/tests -v`. The example map is synthetic; game assets and converted levels are not distributed.

Validation performed on UE5.8: the four-object synthetic fixture imported and reloaded with unique meshes, correct materials and independent actor movement. Separate imports exercised box, triangle, convex and 26-DOP collision. The native teleport automation test passed overlap activation, delay, capsule feet positioning and cooldown without warnings. Python has 29 passing tests. A content-only fixture in the actual Project Jump Map Kit passed its validator with 8 assets, 1 Blueprint and 0 violations, and completed the official DLC cook. CmWorld extracted both solid collision brushes with 0 elements skipped. An isolated runtime automation test of the generated Blueprint passed overlap, delay, feet positioning and shared cooldown checks. These fixture checks do not certify every converted map. A Descent diagnostic import verified 144 valid brushes and explicitly reported six degenerate source brushes. An automated live IW3xo capture of Qube under `3xp_cj` produced 8,908 objects, 146 entities and no unsupported geometry blocks, with the same hash as the previously verified reconstruction. Qube preparation produced all 8,908 source objects (3,304 brushes and 5,604 patches), 14 configured teleport links and 22 flagged fallback hulls; this preparation result is not a full Unreal import or playtest of Qube through this new pipeline.
