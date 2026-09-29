param(
    [ValidateSet('inventory','export')][string]$Stage = 'inventory',
    [string]$Map = 'mp_descent',
    [Parameter(Mandatory=$true)][string]$Usermaps,
    [int]$GameProcessId = 0,
    [switch]$IncludeModelPlacements,
    [string]$OutputRoot = (Join-Path $PSScriptRoot '..\artifacts')
)
$ErrorActionPreference = 'Stop'
if ($Map -cnotmatch '\Amp_[A-Za-z0-9_]{1,80}\z') { throw 'Invalid map identifier' }
$inputDir = Join-Path $Usermaps $Map
if (!(Test-Path -LiteralPath (Join-Path $inputDir "$Map.ff"))) { throw 'Map fastfile missing' }
$resolvedInput = [IO.Path]::GetFullPath($inputDir).TrimEnd('\')
$resolvedOutput = [IO.Path]::GetFullPath($OutputRoot).TrimEnd('\')
if ($resolvedOutput.Equals($resolvedInput,[StringComparison]::OrdinalIgnoreCase) -or $resolvedOutput.StartsWith($resolvedInput+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Output cannot be inside source map directory' }
if ($Stage -eq 'export') {
    if ($GameProcessId -le 0) { throw 'Supply -GameProcessId from JumpConvert.exe list after loading the map locally' }
    $extraArguments = @()
    if ($IncludeModelPlacements) { $extraArguments += '--include-model-placements' }
    & "$PSScriptRoot/bin/JumpConvert.exe" export $GameProcessId $Map $inputDir $resolvedOutput @extraArguments
    if ($LASTEXITCODE -ne 0) { throw 'Export failed; see the run status.json' }
    return
}
Add-Type -AssemblyName System.IO.Compression.FileSystem
$files = @(Get-ChildItem -LiteralPath $inputDir -File | Sort-Object Name | ForEach-Object {
    [ordered]@{ name=$_.Name; bytes=$_.Length; sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant() }
})
$entries = @()
$iwd = Join-Path $inputDir "$Map.iwd"
if (Test-Path -LiteralPath $iwd) {
    $zip = [IO.Compression.ZipFile]::OpenRead($iwd)
    try { $entries = @($zip.Entries | ForEach-Object { [ordered]@{ name=$_.FullName; bytes=$_.Length } }) }
    finally { $zip.Dispose() }
}
$report = [ordered]@{schema_version=1; map=$Map; source_directory=$resolvedInput; files=$files; iwd_entries=$entries; stage='inventory'; converted=$false}
$destination = Join-Path $resolvedOutput "$Map/intake"
New-Item -ItemType Directory -Force $destination | Out-Null
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $destination 'inventory.json') -Encoding utf8
Write-Output "Inventory: $destination\inventory.json"
