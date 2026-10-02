@echo off
if "%~1"=="" (
  echo Usage: Import_Map.cmd -MapFile map.map -Project project.uproject -Editor UnrealEditor.exe [-Config config.json] [-Open]
  echo Live dump: Import_Map.cmd -Cod4Root "CoD4 folder" -MapName mp_map -Project project.uproject -Editor UnrealEditor.exe [-Mod 3xp_cj]
  pause
  exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0pipeline\import-map.ps1" %*
if errorlevel 1 pause
