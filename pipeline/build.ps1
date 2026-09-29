param([string]$Compiler = 'C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\Roslyn\csc.exe')
$ErrorActionPreference = 'Stop'
if (!(Test-Path -LiteralPath $Compiler)) { throw 'Supply -Compiler with an installed Roslyn csc.exe path. No downloads are performed.' }
$files = @(Get-ChildItem "$PSScriptRoot/src","$PSScriptRoot/vendor" -Filter *.cs | Sort-Object FullName | ForEach-Object FullName)
New-Item -ItemType Directory -Force "$PSScriptRoot/bin" | Out-Null
& $Compiler /nologo /target:exe /platform:x64 /unsafe /checked+ /optimize+ /deterministic+ /r:System.Web.Extensions.dll "/out:$PSScriptRoot/bin/JumpConvert.exe" $files
if ($LASTEXITCODE -ne 0) { throw 'Compilation failed' }
Get-FileHash "$PSScriptRoot/bin/JumpConvert.exe" -Algorithm SHA256
