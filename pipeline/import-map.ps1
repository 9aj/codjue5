param(
    [string]$MapFile,
    [string]$Cod4Root,
    [string]$MapName,
    [string]$Mod = '3xp_cj',
    [string]$CaptureOutput,
    [switch]$LeaveGameOpen,
    [int]$LoadFrames = 600,
    [int]$CollisionFrames = 180,
    [int]$DumpTimeoutMinutes = 10,
    [Parameter(Mandatory=$true)][string]$Project,
    [Parameter(Mandatory=$true)][string]$Editor,
    [string]$Config,
    [string]$Output,
    [string]$Python = 'python',
    [switch]$AllowPartial,
    [switch]$Open,
    [int]$TimeoutMinutes = 120
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
$projectPath = (Resolve-Path -LiteralPath $Project).Path
$editorPath = (Resolve-Path -LiteralPath $Editor).Path
if ($Config) { $Config=(Resolve-Path -LiteralPath $Config).Path }
$activeEditors = @(Get-CimInstance Win32_Process -Filter "Name = 'UnrealEditor.exe' OR Name = 'UnrealEditor-Cmd.exe'" | Where-Object { $_.CommandLine -and $_.CommandLine.IndexOf($projectPath,[StringComparison]::OrdinalIgnoreCase) -ge 0 })
if ($activeEditors.Count) { throw 'This Unreal project is already open. Save and close it before running the standalone importer.' }
if ($MapFile -and ($Cod4Root -or $MapName)) { throw 'Choose MapFile or live capture using Cod4Root and MapName.' }
if (-not $MapFile) {
    if (-not $Cod4Root -or -not $MapName) { throw 'Provide MapFile, or both Cod4Root and MapName for a live IW3xo dump.' }
    $MapFile=& (Join-Path $PSScriptRoot 'dump-map.ps1') -Cod4Root $Cod4Root -MapName $MapName -Mod $Mod -CaptureOutput $CaptureOutput -Python $Python -LoadFrames $LoadFrames -CollisionFrames $CollisionFrames -DumpTimeoutMinutes $DumpTimeoutMinutes -LeaveGameOpen:$LeaveGameOpen
}
$mapPath = (Resolve-Path -LiteralPath $MapFile).Path
if (-not $Output) {
    $inputHash = (Get-FileHash -LiteralPath $mapPath -Algorithm SHA256).Hash.Substring(0,12).ToLower()
    $Output = Join-Path $repoRoot ('artifacts/map-import/' + [IO.Path]::GetFileNameWithoutExtension($mapPath) + '-' + $inputHash)
}
$outputPath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Output)
$prepareArgs = @('-m','map_pipeline','prepare',$mapPath,'--output',$outputPath)
if ($Config) { $prepareArgs += @('--config',(Resolve-Path -LiteralPath $Config).Path) }
if ($AllowPartial) { $prepareArgs += '--allow-partial' }
Push-Location $repoRoot
try { & $Python @prepareArgs; if ($LASTEXITCODE -ne 0) { throw 'Map preparation failed; inspect manifest.json issues.' } }
finally { Pop-Location }
$manifestPath = Join-Path $outputPath 'manifest.json'
$reportPath = Join-Path $outputPath 'unreal-result.json'
$env:CODJUE_MANIFEST = $manifestPath
$env:CODJUE_ALLOW_PARTIAL = if ($AllowPartial) { '1' } else { '0' }
$env:CODJUE_QUIT = '1'
# Never run two writers against the same Unreal project.
$activeEditors = @(Get-CimInstance Win32_Process -Filter "Name = 'UnrealEditor.exe' OR Name = 'UnrealEditor-Cmd.exe'" | Where-Object { $_.CommandLine -and $_.CommandLine.IndexOf($projectPath,[StringComparison]::OrdinalIgnoreCase) -ge 0 })
if ($activeEditors.Count) { throw 'This Unreal project is already open. Save and close it before running the standalone importer.' }
function Invoke-EditorScript([string]$scriptName) {
    $scriptPath = Join-Path $repoRoot ('map_pipeline/' + $scriptName)
    $logPath = Join-Path $outputPath ($scriptName + '.log')
    $arguments = @(('"' + $projectPath + '"'),('-ExecutePythonScript="' + $scriptPath + '"'),'-unattended','-nosplash','-nullrhi','-nosound','-nop4',('-abslog="' + $logPath + '"'))
    $process = Start-Process -FilePath $editorPath -ArgumentList $arguments -WindowStyle Hidden -PassThru
    if (-not $process.WaitForExit($TimeoutMinutes * 60000)) { throw ('Unreal import exceeded timeout; process ' + $process.Id + ' is still running. Inspect ' + $logPath) }
    if (-not (Test-Path -LiteralPath $reportPath)) { throw ('Editor produced no report. See ' + $logPath) }
    $report = Get-Content -LiteralPath $reportPath -Raw | ConvertFrom-Json
    if ($process.ExitCode -ne 0 -or $report.status -in @('failed','verification_failed')) { throw ('Unreal failed: ' + $report.error + '. See ' + $logPath) }
}
$report = if (Test-Path -LiteralPath $reportPath) { Get-Content -LiteralPath $reportPath -Raw | ConvertFrom-Json } else { $null }
if ($report -and $report.project -and $report.project -ne $projectPath.ToLower()) { throw 'Checkpoint belongs to another Unreal project. Select a separate output directory.' }
if (-not $report -or $report.status -notin @('built','complete')) { Invoke-EditorScript 'unreal_import.py' }
$report = Get-Content -LiteralPath $reportPath -Raw | ConvertFrom-Json
Invoke-EditorScript 'unreal_verify.py'
$report = Get-Content -LiteralPath $reportPath -Raw | ConvertFrom-Json
if ($report.status -ne 'complete') { throw 'Verification did not complete.' }
Write-Host ('Ready: ' + $report.verified_source_actors + ' independent source actors at ' + $report.level)
if ($Open) { Start-Process -FilePath $editorPath -ArgumentList @(('"'+$projectPath+'"'),$report.level) }
