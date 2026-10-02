param(
    [Parameter(Mandatory=$true)][string]$Cod4Root,
    [Parameter(Mandatory=$true)][ValidatePattern('^[A-Za-z0-9_]+$')][string]$MapName,
    [ValidatePattern('^[A-Za-z0-9_-]+$')][string]$Mod = '3xp_cj',
    [string]$CaptureOutput,
    [string]$Python = 'python',
    [switch]$LeaveGameOpen,
    [ValidateRange(1,36000)][int]$LoadFrames = 600,
    [ValidateRange(1,36000)][int]$CollisionFrames = 180,
    [ValidateRange(1,120)][int]$DumpTimeoutMinutes = 10
)
$ErrorActionPreference='Stop'
$repoRoot=Split-Path $PSScriptRoot -Parent
$gameRoot=(Resolve-Path -LiteralPath $Cod4Root).Path
$gameExe=Join-Path $gameRoot 'iw3xo.exe'
$dllPath=Join-Path $gameRoot 'iw3x.dll'
if (-not (Test-Path -LiteralPath $gameExe) -or -not (Test-Path -LiteralPath $dllPath)) { throw 'IW3xo is missing. Install the full package from https://github.com/xoxor4d/iw3xo-dev/releases into your CoD4 directory first.' }
if (-not [Text.Encoding]::ASCII.GetString([IO.File]::ReadAllBytes($dllPath)).Contains('mapexport_useFilters')) { throw 'Installed iw3x.dll lacks the whole-map exporter. Build/deploy the modified iw3xo-dev exporter before capture.' }
$modPath=Join-Path $gameRoot ('Mods/'+$Mod)
if (-not (Test-Path -LiteralPath $modPath -PathType Container)) { throw ('Mod directory missing: '+$modPath+'. Pass the installed folder name with -Mod.') }
$active=@(Get-CimInstance Win32_Process -Filter "Name='iw3xo.exe' OR Name='iw3mp.exe'")
if ($active.Count) { throw 'A CoD4 client is already running. Close it before starting a standalone map capture.' }
if (-not $CaptureOutput) { $CaptureOutput=Join-Path $repoRoot ('artifacts/captures/'+$MapName+'-'+[DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss')+'-'+[Guid]::NewGuid().ToString('N').Substring(0,8)) }
$capturePath=$ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($CaptureOutput)
if (Test-Path -LiteralPath $capturePath) { throw 'CaptureOutput already exists. Choose a fresh directory to preserve the earlier capture.' }
New-Item -ItemType Directory -Path $capturePath | Out-Null
$cfgName='codjue_export_'+[Guid]::NewGuid().ToString('N')+'.cfg'
$localCfg=Join-Path $capturePath $cfgName
Push-Location $repoRoot
try {
    & $Python -m map_pipeline.capture config $localCfg --load-frames $LoadFrames --collision-frames $CollisionFrames
    if ($LASTEXITCODE -ne 0) { throw 'Could not generate export config.' }
} finally { Pop-Location }
$installedCfg=Join-Path $modPath $cfgName
$exportPath=Join-Path $gameRoot ('iw3xo/map_export/'+$MapName+'.map')
if (Test-Path -LiteralPath $exportPath) { Copy-Item -LiteralPath $exportPath -Destination (Join-Path $capturePath 'previous.map') }
$report=@{status='starting';map=$MapName;mod=$Mod;game_root=$gameRoot;export=$exportPath;dll_sha256=(Get-FileHash -LiteralPath $dllPath).Hash.ToLower();load_frames=$LoadFrames;collision_frames=$CollisionFrames}
$reportPath=Join-Path $capturePath 'capture-result.json'
function Save-CaptureReport { $report | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $reportPath -Encoding utf8 }
Save-CaptureReport
try {
    Copy-Item -LiteralPath $localCfg -Destination $installedCfg
    $start=[DateTime]::UtcNow
    $arguments=@('+set','fs_game',('"mods/'+$Mod+'"'),'+set','com_maxfps','60','+set','logfile','2','+devmap',$MapName,'+exec',$cfgName)
    $report.started_utc=$start.ToString('o');$report.arguments=$arguments;$report.config_sha256=(Get-FileHash -LiteralPath $localCfg).Hash.ToLower()
    $process=Start-Process -FilePath $gameExe -WorkingDirectory $gameRoot -ArgumentList $arguments -WindowStyle Hidden -PassThru
    $report.status='waiting_for_export';$report.process_id=$process.Id;Save-CaptureReport
    $deadline=$start.AddMinutes($DumpTimeoutMinutes);$signature='';$stableSince=$null
    while ([DateTime]::UtcNow -lt $deadline) {
        if (Test-Path -LiteralPath $exportPath) {
            $file=Get-Item -LiteralPath $exportPath
            if ($file.LastWriteTimeUtc -ge $start -and $file.Length -gt 32) {
                $current=[string]$file.Length+':'+$file.LastWriteTimeUtc.Ticks
                if ($current -ne $signature) { $signature=$current;$stableSince=[DateTime]::UtcNow }
                if ($stableSince -and ([DateTime]::UtcNow-$stableSince).TotalSeconds -ge 3) {
                    $handle=$null
                    try {
                        $handle=[IO.File]::Open($exportPath,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::None)
                    } catch [IO.IOException] { }
                    if ($handle) {
                        try { $snapshot=Join-Path $capturePath 'source.map';$destination=[IO.File]::Create($snapshot);try { $handle.CopyTo($destination) } finally { $destination.Dispose() } } finally { $handle.Dispose() }
                        Push-Location $repoRoot
                        try {
                            $validationText=& $Python -m map_pipeline.capture validate $snapshot
                            if ($LASTEXITCODE -ne 0) { throw 'Fresh export failed structural validation. Inspect source.map and the game console.' }
                        } finally { Pop-Location }
                        $report.validation=($validationText | ConvertFrom-Json);$report.status='validated_capture';$report.snapshot=$snapshot;$report.completed_utc=[DateTime]::UtcNow.ToString('o');Save-CaptureReport
                        if (-not $LeaveGameOpen) {
                            $process.Refresh()
                            if (-not $process.HasExited) {
                                $null=$process.CloseMainWindow()
                                if (-not $process.WaitForExit(10000)) { $process.Kill();$null=$process.WaitForExit(10000) }
                            }
                            $report.game_closed=$process.HasExited;Save-CaptureReport
                            if (-not $report.game_closed) { Write-Warning ('Capture succeeded, but game process '+$process.Id+' could not be closed.') }
                        } else { $report.game_closed=$process.HasExited;Save-CaptureReport }
                        Write-Host ('Captured '+$MapName+': '+$report.validation.source_objects+' source objects. Game closed: '+$report.game_closed)
                        return $snapshot
                    }
                }
            }
        }
        if ($process.HasExited) { throw ('IW3xo exited before a fresh export was completed (exit '+$process.ExitCode+').') }
        Start-Sleep -Milliseconds 500
    }
    throw ('Timed out waiting for a fresh export. Inspect the game console. IW3xo process '+$process.Id+' remains open; no old map was accepted.')
} catch {
    $report.status='failed';$report.error=$_.Exception.Message;Save-CaptureReport;throw
} finally {
    if (Test-Path -LiteralPath $installedCfg) { Remove-Item -LiteralPath $installedCfg }
}
