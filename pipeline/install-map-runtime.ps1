param([Parameter(Mandatory=$true)][string]$Project, [Parameter(Mandatory=$true)][string]$Engine, [string]$Target, [string]$CompilerVersion)
$ErrorActionPreference='Stop'
$projectPath=(Resolve-Path -LiteralPath $Project).Path
$enginePath=(Resolve-Path -LiteralPath $Engine).Path
$repoRoot=Split-Path $PSScriptRoot -Parent
$source=Join-Path $repoRoot 'unreal/CodMapRuntime'
$destination=Join-Path (Split-Path $projectPath -Parent) 'Plugins/CodMapRuntime'
if (Test-Path -LiteralPath $destination) {
    foreach ($file in Get-ChildItem -LiteralPath $source -File -Recurse) {
        $relative=$file.FullName.Substring($source.Length).TrimStart('\','/')
        $installed=Join-Path $destination $relative
        if ((Test-Path -LiteralPath $installed) -and (Get-FileHash -LiteralPath $installed).Hash -ne (Get-FileHash -LiteralPath $file.FullName).Hash) { throw ('Existing runtime differs: '+$installed+'. Review it before updating.') }
    }
}
New-Item -ItemType Directory -Force -Path (Split-Path $destination -Parent) | Out-Null
Copy-Item -LiteralPath $source -Destination (Split-Path $destination -Parent) -Recurse -Force
$projectData=Get-Content -LiteralPath $projectPath -Raw | ConvertFrom-Json
if (-not $projectData.Plugins) { $projectData | Add-Member -NotePropertyName Plugins -NotePropertyValue @() -Force }
$entry=$projectData.Plugins | Where-Object Name -eq 'CodMapRuntime'
if ($entry) { $entry.Enabled=$true } else { $projectData.Plugins+=@{Name='CodMapRuntime';Enabled=$true} }
$projectData | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $projectPath -Encoding utf8
if (-not $Target) {
    $modules=@($projectData.Modules)
    if (-not $modules.Count) { throw 'Plugin installed. Blueprint-only projects need a C++ editor target to build this runtime.' }
    $Target=$modules[0].Name+'Editor'
}
$buildArguments=@($Target,'Win64','Development',('-Project='+$projectPath),'-WaitMutex','-NoHotReloadFromIDE')
if ($CompilerVersion) { $buildArguments+=('-CompilerVersion='+$CompilerVersion) }
& (Join-Path $enginePath 'Engine/Build/BatchFiles/Build.bat') @buildArguments
if ($LASTEXITCODE -ne 0) { throw 'Runtime build failed. See UnrealBuildTool diagnostics.' }
