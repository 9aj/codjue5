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
    [ValidateSet('generic','project_jump')][string]$Profile='generic',
    [string]$Output,
    [string]$Python = 'python',
    [switch]$AllowPartial,
    [switch]$Open,
    [int]$TimeoutMinutes = 120
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
$projectPath = (Resolve-Path -LiteralPath $Project).Path
$originalProjectHash=(Get-FileHash -LiteralPath $projectPath).Hash
$editorPath = (Resolve-Path -LiteralPath $Editor).Path
if ($Profile -eq 'project_jump') {
    $engineRoot=Split-Path (Split-Path (Split-Path (Split-Path $editorPath -Parent) -Parent) -Parent) -Parent
    $version=Get-Content -LiteralPath (Join-Path $engineRoot 'Engine/Build/Build.version') -Raw | ConvertFrom-Json
    if ($version.MajorVersion -ne 5 -or $version.MinorVersion -ne 8) { throw 'Project Jump requires Unreal Engine 5.8.x.' }
}
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
    $sourceName=if ($MapName) { $MapName } else { [IO.Path]::GetFileNameWithoutExtension($mapPath) }
    $Output = Join-Path $repoRoot ('artifacts/map-import/' + $sourceName + '-' + $Profile + '-' + $inputHash)
}
$outputPath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Output)
$prepareArgs = @('-m','map_pipeline','prepare',$mapPath,'--output',$outputPath)
$prepareArgs+=@('--profile',$Profile)
if ($MapName) { $prepareArgs+=@('--map-id',$MapName) }
if ($Config) { $prepareArgs += @('--config',(Resolve-Path -LiteralPath $Config).Path) }
if ($AllowPartial) { $prepareArgs += '--allow-partial' }
Push-Location $repoRoot
try { & $Python @prepareArgs; if ($LASTEXITCODE -ne 0) { throw 'Map preparation failed; inspect manifest.json issues.' } }
finally { Pop-Location }
$manifestPath = Join-Path $outputPath 'manifest.json'
if ($Profile -eq 'project_jump') {
    Push-Location $repoRoot
    try { $pluginText=& $Python -m map_pipeline.project_jump $projectPath $manifestPath; if ($LASTEXITCODE -ne 0) { throw 'Content-plugin preflight failed.' }; $plugin=$pluginText | ConvertFrom-Json }
    finally { Pop-Location }
}
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
    $arguments+='-EnablePlugins=PythonScriptPlugin'
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
if ($Profile -eq 'project_jump') {
    if ((Get-FileHash -LiteralPath $projectPath).Hash -ne $originalProjectHash) { throw 'Kit project descriptor changed during import.' }
    $kitTools=Join-Path (Split-Path $projectPath -Parent) 'Tools/PackageMod.ps1'
    if ((Test-Path -LiteralPath $kitTools) -or (Test-Path -LiteralPath (Join-Path (Split-Path $projectPath -Parent) 'Tools/PackageMod.cmd'))) {
        $validatorExe=Join-Path (Split-Path $editorPath -Parent) 'UnrealEditor-Cmd.exe'
        $validator=Start-Process -FilePath $validatorExe -ArgumentList @(('"'+$projectPath+'"'),'-run=JumperModValidate',('-mod='+$plugin.plugin),'-nullrhi','-nosteam','-unattended','-nosplash',('-abslog="'+(Join-Path $outputPath 'project-jump-modcheck.log')+'"')) -WindowStyle Hidden -PassThru
        if (-not $validator.WaitForExit($TimeoutMinutes*60000)) { throw 'Project Jump Blueprint validation timed out.' }
        if ($validator.ExitCode -ne 0) { throw 'Project Jump rejected the Blueprint content. Inspect project-jump-modcheck.log.' }
        $report | Add-Member -NotePropertyName kit_blueprint_validation -NotePropertyValue 'passed' -Force
    } else { $report | Add-Member -NotePropertyName kit_blueprint_validation -NotePropertyValue 'not_available_in_this_project' -Force }
    $report | Add-Member -NotePropertyName kit_project_unchanged -NotePropertyValue $true -Force
    $report | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $reportPath -Encoding utf8
}
Write-Host ('Ready: ' + $report.verified_source_actors + ' independent source actors at ' + $report.level)
if ($Open) { Start-Process -FilePath $editorPath -ArgumentList @(('"'+$projectPath+'"'),$report.level) }
