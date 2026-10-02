<#
.SYNOPSIS
Dump a COD4 map and import it into Unreal: ./codue5 mp_mymapname
#>
[CmdletBinding()]
param(
    [Parameter(Position=0)][ValidatePattern('^[A-Za-z0-9_]+$')][string]$MapName,
    [switch]$Setup,
    [switch]$SetupOnly,
    [switch]$DryRun,
    [switch]$LeaveGameOpen,
    [switch]$NoOpen,
    [string]$Cod4Root,
    [string]$Project,
    [string]$Editor,
    [string]$Mod,
    [string]$Config,
    [string]$CompilerVersion,
    [string]$Settings
)
$ErrorActionPreference='Stop'
if ($Cod4Root) { $Cod4Root=(Resolve-Path -LiteralPath $Cod4Root).Path }
if ($Project) { $Project=(Resolve-Path -LiteralPath $Project).Path }
if ($Editor) { $Editor=(Resolve-Path -LiteralPath $Editor).Path }
if (-not $Settings) { $Settings=Join-Path $PSScriptRoot 'local.codue5.json' }
$settingsPath=$ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Settings)
function Resolve-SettingPath([string]$value) {
    if (-not [IO.Path]::IsPathRooted($value)) { $value=Join-Path (Split-Path $settingsPath -Parent) $value }
    return (Resolve-Path -LiteralPath $value).Path
}
function Read-RequiredPath([string]$label,[string]$value) {
    if (-not $value) { $value=(Read-Host $label).Trim().Trim('"') }
    if (-not $value) { throw ($label+' is required.') }
    return Resolve-SettingPath $value
}
$saved=@{}
if (Test-Path -LiteralPath $settingsPath) {
    $json=Get-Content -LiteralPath $settingsPath -Raw | ConvertFrom-Json
    foreach ($property in $json.PSObject.Properties) { $saved[$property.Name]=$property.Value }
}
$firstRun=-not $saved.RuntimeReady
if (-not $Cod4Root) { $Cod4Root=$saved.Cod4Root }
if (-not $Project) { $Project=$saved.Project }
if (-not $Editor) { $Editor=$saved.Editor }
if (-not $Mod) { $Mod=if ($saved.Mod) { $saved.Mod } else { '3xp_cj' } }
if (-not $CompilerVersion) { $CompilerVersion=$saved.CompilerVersion }
if (-not $MapName -and -not $SetupOnly -and -not $Setup) { throw 'Usage: ./codue5 mp_mymapname (or ./codue5 -SetupOnly)' }
if ($DryRun -and (-not $Cod4Root -or -not $Project -or -not $Editor)) { throw 'DryRun needs saved settings or explicit Cod4Root, Project and Editor paths.' }
if ($firstRun -and -not $DryRun) { Write-Host 'First run: choose your game and Unreal project. These paths stay in local.codue5.json.' }
$Cod4Root=Read-RequiredPath 'CoD4 folder containing iw3xo.exe' $Cod4Root
$Project=Read-RequiredPath 'Destination Unreal .uproject file (C++ project)' $Project
$Editor=Read-RequiredPath 'UnrealEditor.exe path' $Editor
$firstRun=$firstRun -or $Project -ne $saved.Project -or $Editor -ne $saved.Editor -or $Cod4Root -ne $saved.Cod4Root
if ([IO.Path]::GetExtension($Project) -ne '.uproject') { throw 'Project must be a .uproject file.' }
if ([IO.Path]::GetFileName($Editor) -ne 'UnrealEditor.exe') { throw 'Editor must be UnrealEditor.exe.' }
$engineRoot=[IO.Path]::GetFullPath((Join-Path (Split-Path $Editor -Parent) '../../..'))
if (-not $CompilerVersion) {
    $sdkFile=Join-Path $engineRoot 'Engine/Config/Windows/Windows_SDK.json'
    $vswhere=Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
    if ((Test-Path -LiteralPath $sdkFile) -and (Test-Path -LiteralPath $vswhere)) {
        $sdk=Get-Content -LiteralPath $sdkFile -Raw | ConvertFrom-Json
        $installed=@(& $vswhere -all -products '*' -property installationPath)
        $families=@(foreach ($installation in $installed) { Get-ChildItem -LiteralPath (Join-Path $installation 'VC/Tools/MSVC') -Directory -ErrorAction SilentlyContinue })
        foreach ($range in $sdk.PreferredVisualCppVersions) {
            $limits=$range.Split('-')
            $preferred=$families | Where-Object { [version]$_.Name -ge [version]$limits[0] -and [version]$_.Name -le [version]$limits[1] } | Sort-Object { [version]$_.Name } -Descending | Select-Object -First 1
            if ($preferred) { $CompilerVersion=$preferred.Name;break }
        }
    }
}
if (-not (Test-Path -LiteralPath (Join-Path $Cod4Root 'iw3xo.exe'))) { throw 'Install the full IW3xo package into your CoD4 folder first: https://github.com/xoxor4d/iw3xo-dev/releases' }
if (-not (Test-Path -LiteralPath (Join-Path $Cod4Root ('Mods/'+$Mod)))) { throw ('Mod not installed: '+$Mod+'. Use -Mod with the actual folder name under Mods.') }
$python=if ($saved.Python) { $saved.Python } else { 'python' }
& $python -c 'import sys; assert sys.version_info >= (3,10), "Python 3.10+ is required"'
if ($LASTEXITCODE -ne 0) { throw 'Python 3.10+ is required. Install Python and enable its PATH option.' }
if (-not $Config) {
    $candidate=Join-Path $PSScriptRoot ('local.maps/'+$MapName+'.json')
    if ($MapName -and (Test-Path -LiteralPath $candidate)) { $Config=$candidate }
}
if ($Config) { $Config=(Resolve-Path -LiteralPath $Config).Path }
$settingsData=@{Cod4Root=$Cod4Root;Project=$Project;Editor=$Editor;Mod=$Mod;Python=$python;CompilerVersion=$CompilerVersion;RuntimeReady=[bool]$saved.RuntimeReady}
if ($DryRun) {
    Write-Host 'Dry run: no game launch, build, project edits or import.'
    $settingsData | ConvertTo-Json
    Write-Host ('Map: '+$MapName+'; config: '+$Config)
    return
}
if ($firstRun -or $Setup -or $SetupOnly) {
    $active=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe' OR Name='iw3xo.exe' OR Name='iw3mp.exe'" | Where-Object { $_.Name -in @('iw3xo.exe','iw3mp.exe') -or ($_.CommandLine -and $_.CommandLine.IndexOf($Project,[StringComparison]::OrdinalIgnoreCase) -ge 0) })
    if ($active.Count) { throw 'Save and close the destination Unreal project and CoD4 before setup.' }
    $descriptor=Get-Content -LiteralPath $Project -Raw | ConvertFrom-Json
    if (-not @($descriptor.Modules).Count -or -not $descriptor.Modules) { throw 'Use a C++ Unreal project, or add a C++ class in Unreal once, then close the editor and rerun.' }
    $dllPath=Join-Path $Cod4Root 'iw3x.dll'
    if (-not (Test-Path -LiteralPath $dllPath) -or -not [Text.Encoding]::ASCII.GetString([IO.File]::ReadAllBytes($dllPath)).Contains('mapexport_useFilters')) {
        & (Join-Path $PSScriptRoot 'pipeline/setup-iw3xo.ps1') -Cod4Root $Cod4Root
    }
    if (-not $descriptor.Plugins) { $descriptor | Add-Member -NotePropertyName Plugins -NotePropertyValue @() -Force }
    $pythonPlugin=$descriptor.Plugins | Where-Object Name -eq 'PythonScriptPlugin'
    if ($pythonPlugin) { $pythonPlugin.Enabled=$true } else { $descriptor.Plugins+=@{Name='PythonScriptPlugin';Enabled=$true} }
    $descriptor | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $Project -Encoding utf8
    Write-Host 'Installing and building the Unreal teleport runtime...'
    & (Join-Path $PSScriptRoot 'pipeline/install-map-runtime.ps1') -Project $Project -Engine $engineRoot -CompilerVersion $CompilerVersion
    $settingsData.RuntimeReady=$true
    $settingsData | ConvertTo-Json | Set-Content -LiteralPath $settingsPath -Encoding utf8
    Write-Host ('Setup saved: '+$settingsPath)
}
if ($SetupOnly -or -not $MapName) { Write-Host 'Ready. Run ./codue5 mp_mymapname';return }
$run=@{Cod4Root=$Cod4Root;MapName=$MapName;Mod=$Mod;Project=$Project;Editor=$Editor;Python=$python;Open=(-not $NoOpen);LeaveGameOpen=$LeaveGameOpen}
if ($Config) { $run.Config=$Config }
Write-Host ('Dumping '+$MapName+', then importing and verifying in Unreal...')
& (Join-Path $PSScriptRoot 'pipeline/import-map.ps1') @run
