param([Parameter(Mandatory=$true)][string]$Cod4Root)
$ErrorActionPreference='Stop'
$gameRoot=(Resolve-Path -LiteralPath $Cod4Root).Path
if (@(Get-CimInstance Win32_Process -Filter "Name='iw3xo.exe' OR Name='iw3mp.exe'").Count) { throw 'Close CoD4 before installing its exporter DLL.' }
$repoRoot=Split-Path $PSScriptRoot -Parent
$source=Join-Path $repoRoot 'artifacts/iw3xo-source'
# This published commit includes whole-map filtering, submodels and wedge fixes.
$revision='5b1b57e5e48764783a223e891ca1573d040690ea'
if (-not (Test-Path -LiteralPath $source)) {
    & git clone https://github.com/9aj/iw3xo-dev.git $source
    if ($LASTEXITCODE -ne 0) { throw 'Could not clone the IW3xo exporter source.' }
}
Push-Location $source
try {
    if (& git status --porcelain) { throw 'Exporter build checkout has local modifications. Preserve it and choose a clean checkout before setup.' }
    & git checkout --detach $revision
    if ($LASTEXITCODE -ne 0) { throw 'Pinned exporter revision is unavailable.' }
    & git submodule update --init --recursive
    if ($LASTEXITCODE -ne 0) { throw 'Exporter dependency checkout failed.' }
    $vswhere=Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
    $msbuild=& $vswhere -latest -version '[17,18)' -products '*' -requires Microsoft.Component.MSBuild -find 'MSBuild\**\Bin\MSBuild.exe' | Select-Object -First 1
    if (-not $msbuild) { $msbuild=& $vswhere -latest -products '*' -requires Microsoft.Component.MSBuild -find 'MSBuild\**\Bin\MSBuild.exe' | Select-Object -First 1 }
    if (-not $msbuild) { throw 'Install Visual Studio C++ Build Tools, including x86 tools and a Windows SDK.' }
    $previousCod4Root=$env:COD4_ROOT
    try {
        $env:COD4_ROOT=$null
        & ./tools/premake5.exe vs2022
        if ($LASTEXITCODE -ne 0) { throw 'IW3xo build generation failed.' }
        & $msbuild ./build/iw3xo-dev.sln /p:Configuration=Release /p:Platform=Win32 /m /verbosity:minimal
        if ($LASTEXITCODE -ne 0) { throw 'IW3xo build failed. Check the installed C++ and Windows SDK dependencies.' }
    } finally { $env:COD4_ROOT=$previousCod4Root }
} finally { Pop-Location }
$builtDll=Join-Path $source 'build/bin/Release/iw3x.dll'
if (-not (Test-Path -LiteralPath $builtDll)) { throw 'Exporter build did not produce iw3x.dll.' }
$installedDll=Join-Path $gameRoot 'iw3x.dll'
if (Test-Path -LiteralPath $installedDll) {
    $backup=Join-Path $repoRoot ('artifacts/iw3xo-dll-backup-'+[Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $backup | Out-Null
    Copy-Item -LiteralPath $installedDll -Destination (Join-Path $backup 'iw3x.dll')
}
Copy-Item -LiteralPath $builtDll -Destination $installedDll
Write-Host ('Installed whole-map exporter from https://github.com/9aj/iw3xo-dev/tree/'+$revision)
