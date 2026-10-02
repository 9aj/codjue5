# codjue5 — Call of Duty 4 maps to Unreal Engine 5

A PowerShell pipeline for dumping COD4 maps through IW3xo and importing them into Unreal Engine 5.

```powershell
./codue5 mp_mymapname
```

On the first run, enter your CoD4 folder, Unreal `.uproject` and `UnrealEditor.exe` paths. Setup saves them locally, enables Unreal Python, builds the teleport runtime, and builds the modified IW3xo exporter if your DLL needs it. Subsequent maps need only their name.

The command launches `3xp_cj`, loads the map, exports all collision geometry/entities/model placements, saves and validates a fresh `.map`, closes the game, imports an independent mesh and actor for every brush and patch, verifies the saved Unreal level, then opens it.

## Get started

Install these once:

- CoD4 with the full [IW3xo package](https://github.com/xoxor4d/iw3xo-dev/releases), your maps and the `3xp_cj` mod.
- Unreal Engine and a **C++ project**. For an existing Blueprint project, add a C++ class in Unreal once.
- Python 3.10+ on PATH, Git and Visual Studio C++ Build Tools with a Windows SDK. Unreal may also require the .NET Framework Developer Pack.

Then:

```powershell
git clone https://github.com/9aj/codjue5.git
cd codjue5
./codue5 mp_mymapname
```

Save and close the destination Unreal project and CoD4 before running. If PowerShell blocks local scripts, enable scripts for this terminal session with `Set-ExecutionPolicy -Scope Process Bypass`.

Optional commands:

```powershell
./codue5 -SetupOnly                  # Configure/build without importing a map
./codue5 mp_mymapname -DryRun        # Show saved paths without launching anything
./codue5 mp_mymapname -NoOpen        # Import and verify, leave Unreal closed
./codue5 mp_mymapname -LeaveGameOpen # Keep CoD4 open after a successful dump
./codue5 -SetupOnly -Mod other_mod  # Change the installed mod folder
```

Settings live in ignored `local.codue5.json`. Override paths with `-Cod4Root`, `-Project` or `-Editor`; rerun `-SetupOnly` when changing projects. Optional map settings load automatically from ignored `local.maps/<mapname>.json`. Copy `map_pipeline/examples/config.json` there and replace its demonstration values to configure textures, sky, models and script-driven teleports. `-Config` selects another file.

Brush UVs and patch UVs use the data available in the reconstructed export. Missing original textures/UVs, render-only geometry and arbitrary GSC logic cannot be recovered by this command. Missing assets and unsupported gameplay are reported; configured teleports run through the included native plugin. Playtest the result with your own pawn and movement system.

See the [pipeline guide](docs/MAP_PIPELINE.md) for collision options, asset extraction, setup troubleshooting and lower-level `Import_Map.cmd` usage. The pinned modified exporter source is [published in the IW3xo fork](https://github.com/9aj/iw3xo-dev/tree/5b1b57e5e48764783a223e891ca1573d040690ea); setup clones/builds it into ignored `artifacts/` and preserves the previous DLL before installing it.

**Live COD4 export: [step-by-step conversion guide](docs/CONVERSION_GUIDE.md).**

The direct `.map` pipeline handles geometry, collision, lighting, configured materials/models and teleport bindings without map-specific importer code. Arbitrary GSC gameplay and missing source asset data still require configuration or implementation and playtesting. The older live-game exporter remains available separately.

No game, map, texture, captured model, Unreal project or compiled tool binary is included. Use your own installation and maps you have permission to convert. Map permission and third-party model/texture permissions are separate from this tool's license.

## What is included

| Component | Status |
|---|---|
| Direct Radiant .map pipeline | Independent brush/patch actors, per-object collision, materials, lighting, six-face sky, configured model/teleport bindings, resumable import and saved-level verification |
| CodMapRuntime Unreal plugin | Native per-pawn teleport delay, capsule feet offset and shared cooldown; C++ source included |
| C2M/Husky-derived COD4 world exporter | Buildable C# source; reads supported `iw3mp` layouts and rejects unrecognised layouts |
| Inventory, hashes, OBJ validation and neutral material preparation | Runnable PowerShell / C# commands |
| Static-model buffer capture | Separate command; LOD0 decoding demonstrated on Tunnel |
| UE5 import and validation instructions | Manual workflow, with scale/orientation/collision checks |
| Tunnel collision, model, gameplay and art scripts | Map-specific reference implementations requiring configuration and, for gameplay, local project assets |
| Render partition / surface grouping algorithms | Python source and synthetic tests; historical Descent CLI defaults |
| Finished map / Project Jump movement system | Not distributed |

## Older live-game exporter

Prerequisites: Windows x64, Windows PowerShell, .NET Framework 4.7.2 or later, a modern Visual Studio Roslyn C# compiler, and COD4 with your map loaded locally. Python 3.10+ is used for the optional geometry tests/reference scripts; Unreal's Python scripts run inside Unreal.

```powershell
git clone https://github.com/9aj/codjue5.git
Set-Location codjue5
& .\pipeline\build.ps1
& .\pipeline\bin\JumpConvert.exe self-test
& .\pipeline\bin\JumpConvert.exe list

# Replace these three values with your local paths, map and PID.
$mapName = 'mp_tunnel'
$usermaps = 'C:\Games\Call of Duty 4\usermaps'
$gameProcessId = 1234
& .\pipeline\convert.ps1 -Stage inventory -Map $mapName -Usermaps $usermaps
& .\pipeline\convert.ps1 -Stage export -Map $mapName -Usermaps $usermaps -GameProcessId $gameProcessId
```

The build defaults to Visual Studio 2022 Community's compiler path. Use `-Compiler '...\Roslyn\csc.exe'` for another installed edition. The compiler must support the source's modern C# syntax; the legacy Windows Framework compiler is not a substitute. There is no NuGet restore or bundled native DLL dependency.

Only import a run whose `status.json` says `validated_export`. A successful export is not a collision or gameplay validation. Continue with the [full guide](docs/CONVERSION_GUIDE.md), including the UE5 import settings and verification gates.

## Documentation

- [Build, capture and import into UE5](docs/CONVERSION_GUIDE.md)
- [Advanced conversion: collision, props, gameplay and materials](docs/ADVANCED_WORKFLOW.md)
- [Tunnel case study: what we actually built and checked](docs/TUNNEL_CASE_STUDY.md)
- [Troubleshooting and known limitations](docs/TROUBLESHOOTING.md)
- [Reference scripts and their dependencies](reference/README.md)
- [Credits and third-party notices](CREDITS.md)
- [Contributing and running tests](CONTRIBUTING.md)

## Credits and license

This work builds on **[C2M by SHEILAN](https://github.com/sheilan102/C2M)**, **[Husky by Philip/Scobalula](https://github.com/Scobalula/Husky)** and **[PhilLibX by Philip/Scobalula](https://github.com/Scobalula/PhilLibX)**. C2M's upstream credits also acknowledge **DTZxPorter's Wraith normal-unpacking and half-float research**. Those contributions are foundational, not incidental.

We also used OpenAssetTools, CoD4x and iw3xo source as layout/research references, and Poly Haven CC0 scans for the example map's material pass. See [CREDITS.md](CREDITS.md) for the precise distinction between included code, consulted references and optional art sources.

Code and documentation are provided under **GPL-3.0-or-later**, except the separately identified MIT-covered PhilLibX code. Original notices are retained; [LICENSE](LICENSE) contains the GPL text. The license does not cover game assets or grant permission to redistribute a converted map. Unreal Engine is a separately licensed dependency, not part of this source distribution.
