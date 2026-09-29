# Step-by-step: from COD4 to a UE5 greybox

This guide gets you to an inspectable render mesh. Follow the advanced guide before treating it as a playable conversion. Commands below run from the repository root in PowerShell unless labelled **Unreal Python**.

## 1. Prepare your inputs

1. Obtain the map author's permission for your intended use and check separately supplied models, textures and sounds.
2. Keep the original map folder intact. The exporter expects `<usermaps>/<map>/<map>.ff`; an accompanying `.iwd` is inventoried if present.
3. Install/use Windows x64, .NET Framework 4.7.2 or later, and an installed Visual Studio Roslyn compiler. Python 3.10+ is optional for core export but needed for the supplied geometry tests and offline reference stages.
4. Create a separate UE5 project or backup your existing project. Our local reference work used UE5.8. Other versions/importer backends require their own orientation checks.
5. Load the map in a local COD4 multiplayer session. Keep it loaded and stationary throughout capture. The exporter targets `iw3mp`, not a dedicated server or single-player process. An unsupported executable layout must fail; do not change offsets at random.

## 2. Build and check the exporter

```powershell
& .\pipeline\build.ps1
& .\pipeline\bin\JumpConvert.exe self-test
```

For a different Visual Studio installation:

```powershell
& .\pipeline\build.ps1 -Compiler 'C:\Your\VisualStudio\MSBuild\Current\Bin\Roslyn\csc.exe'
```

`pipeline/bin/JumpConvert.exe` is generated locally and ignored by Git. The build requires no NuGet packages. Stop if compilation or the self-test fails.

## 3. Inventory the map and select the correct process

```powershell
$mapName = 'mp_tunnel'
$usermaps = 'C:\Games\Call of Duty 4\usermaps'
& .\pipeline\convert.ps1 -Stage inventory -Map $mapName -Usermaps $usermaps
& .\pipeline\bin\JumpConvert.exe list
```

The inventory records source file sizes/hashes and IWD entry names. The process list prints PID and executable path. Choose the PID for the local game in which you loaded this map; do not assume a PID from an earlier session is still correct.

## 4. Capture the world

```powershell
$gameProcessId = 1234 # Replace with the PID just listed.
& .\pipeline\convert.ps1 -Stage export -Map $mapName -Usermaps $usermaps -GameProcessId $gameProcessId
```

The selected process is opened for reading. This build does not launch the game, inject code, write game memory or fetch game assets. It probes two known upstream asset-pool addresses, checks map identity and bounds reads. Those checks do not make arbitrary builds compatible.

Leave `-IncludeModelPlacements` off: it enables an older placement path that failed on our Descent capture. The separate model capture command is described in the advanced guide.

The command prints a new run directory beneath `artifacts/<map>/`. Copy the exact printed directory into `$run`:

```powershell
$run = 'C:\Path\To\codjue5\artifacts\mp_tunnel\YOUR-RUN-DIRECTORY'
$status = Get-Content -LiteralPath (Join-Path $run 'status.json') -Raw | ConvertFrom-Json
if ($status.status -ne 'validated_export') { throw 'Do not import this capture; inspect its diagnostics.' }
Get-Content -LiteralPath (Join-Path $run 'validation.json')
& .\pipeline\bin\JumpConvert.exe validate (Join-Path $run "ue5\${mapName}_greybox.obj")
```

Each capture gets a unique directory. Failed captures are retained for diagnosis; do not import their partial OBJ files. Keep the manifest beside any local derivative so you can trace it back to its input.

## 5. Understand the outputs

| Path inside a run | What it contains |
|---|---|
| `status.json` | Completion/failure state; UE import is a separate stage |
| `manifest.json` | Tool/game/input/output hashes, coordinate conventions and limitations |
| `validation.json` | Geometry structure checks and bounds |
| `probe-diagnostics.json` | Known-layout probe outcomes |
| `raw/` | Source-style OBJ/MTL, material references and entity data |
| `ue5/<map>_greybox.obj` and `.mtl` | Neutral handoff mesh and stable material slots |
| `ue5/material-replacements.json` | Material mapping/provenance worksheet |
| `ue5/gameplay-entities.json` | Entity properties and categories, not functional UE actors |

Raw metadata can contain game texture/material/model names. No original texture pixels are exported by this core path. Captured geometry is still map content; keep it out of public source commits.

## 6. Import into Unreal Engine

1. Create an empty test level and a new content folder, for example `/Game/Converted/mp_tunnel`. Work on a copy, not your only playable map.
2. Import the **prepared greybox OBJ**, not the raw OBJ. Keep its MTL beside it.
3. Use import scale **1.0**: exported world vertex positions are already in centimetres. Do **not** multiply the world mesh by 2.54 again.
4. Disable texture import. Use neutral materials or independently sourced replacements. Preserve material slot order for later mapping.
5. For the first render inspection, disable automatic collision generation. One convex hull around a complete map will block tunnels and openings. Configure collision separately in step 8.
6. Place the mesh at location `(0,0,0)`, rotation `(0,0,0)`, scale `(1,1,1)` before doing calibration.
7. If sky surfaces form an enclosing shell, identify their material slots from the replacement manifest and remove/filter those faces on a duplicate or in an offline preparation stage. Do not delete all high-numbered material slots: the earlier upstream material filter omitted useful surfaces too.

Our reference scripts explicitly used the legacy OBJ importer (`FbxFactory`) with `convert_scene=False`, `convert_scene_unit=False`, scale 1 and no generated collision. Under that tested route, source positions map to Unreal as `(x, -y, z)`. Interchange and other file formats may behave differently; verify instead of blindly applying a second Y flip.

## 7. Check scale and orientation before continuing

Use an asymmetric landmark and at least three known points, including a vertical difference.

- A source distance of 100 CoD units should measure **254 cm**.
- A source placement `(100, 200, 300)` becomes `(254, -508, 762)` under our tested legacy coordinate convention.
- Check a doorway, landing width, tunnel height and a known jump gap against COD4.
- Check face direction/visibility. Fix winding on a duplicate if required; a two-sided material can hide a winding problem without fixing it.
- Model metadata remains in CoD units and must be converted once, unlike the exported world OBJ.

Save this verified baseline before adding detail. If orientation or scale is wrong, stop here and correct the import convention consistently across world, models, collision and entities.

## 8. Add collision, models and gameplay

Continue with [ADVANCED_WORKFLOW.md](ADVANCED_WORKFLOW.md). A render mesh is not the original COD4 collision world. For a provisional visual test you can use explicitly configured complex collision on a test copy, but that is not a faithful collision conversion or proof a jump route works.

The tested Tunnel collision path uses source-hash-pinned profiles. An unknown map needs its own validated parser/profile. Teleport entity metadata must be turned into your project's actors or Blueprints; this repository does not include the Project Jump pawn, movement code or gameplay templates.

## 9. Validate the playable port

Check spawn grounding, ceilings, wall clipping, terrain, model collision, teleport exits and every jump route using the intended movement implementation. Record the source hash, import settings and test results. A structurally valid OBJ or successful collision trace is not a complete playthrough.

Only after this baseline passes should you replace materials, add lights and supports, or make deliberate gameplay edits. Backup before each pass. Package/cook and test the packaged map separately before a Workshop release.
