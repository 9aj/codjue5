# codjue5 — Call of Duty 4 maps to Unreal Engine 5

A source-built COD4 geometry exporter and a documented workflow for bringing authorised custom maps into UE5. Developed during the Project Jump conversions of `mp_descent` and `mp_tunnel`.

**Start here: [step-by-step conversion guide](docs/CONVERSION_GUIDE.md).**

The reusable exporter produces geometry, neutral material slots and entity metadata. A finished playable port also needs collision reconstruction, models, gameplay logic, materials and playtesting. Those later stages were validated for specific maps; this is **not a universal one-click map converter**.

No game, map, texture, captured model, Unreal project or compiled tool binary is included. Use your own installation and maps you have permission to convert. Map permission and third-party model/texture permissions are separate from this tool's license.

## What is included

| Component | Status |
|---|---|
| C2M/Husky-derived COD4 world exporter | Buildable C# source; reads supported `iw3mp` layouts and rejects unrecognised layouts |
| Inventory, hashes, OBJ validation and neutral material preparation | Runnable PowerShell / C# commands |
| Static-model buffer capture | Separate command; LOD0 decoding demonstrated on Tunnel |
| UE5 import and validation instructions | Manual workflow, with scale/orientation/collision checks |
| Tunnel collision, model, gameplay and art scripts | Map-specific reference implementations requiring configuration and, for gameplay, local project assets |
| Render partition / surface grouping algorithms | Python source and synthetic tests; historical Descent CLI defaults |
| Finished map / Project Jump movement system | Not distributed |

## Quick start: export only

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
