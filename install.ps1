# Terrain Toolkit - manual installation into the Allplan 2026 USR folder.
# Usage: right-click > "Run with PowerShell"  (or: powershell -ExecutionPolicy Bypass -File install.ps1 [UsrPath])
param([string]$UsrPath = "")

$ErrorActionPreference = "Stop"
$src = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not $UsrPath) {
    $default = Join-Path $env:USERPROFILE "Documents\Nemetschek\Allplan\2026\Usr\Local"
    Write-Host "Allplan USR folder (Allplan: Allmenu > Service > File Explorer > 'My own CAD documents')"
    $answer = Read-Host "Press Enter for [$default] or type another path"
    $UsrPath = if ($answer) { $answer } else { $default }
}
if (-not (Test-Path $UsrPath)) { throw "USR folder not found: $UsrPath" }

foreach ($folder in "Library", "PythonPartsScripts", "PythonPartsActionbar") {
    $from = Join-Path $src $folder
    $to = Join-Path $UsrPath $folder
    Write-Host "Copying $folder -> $to"
    New-Item -ItemType Directory -Force -Path $to | Out-Null
    Copy-Item -Path (Join-Path $from "*") -Destination $to -Recurse -Force
}
# remove stale byte code so that Allplan loads the new scripts
Get-ChildItem -Path (Join-Path $UsrPath "PythonPartsScripts\terrain_toolkit") -Recurse -Directory -Filter "__pycache__" |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "Installed. Restart Allplan, then open: Library > Private > Terrain Toolkit"
Write-Host "Log file: $env:USERPROFILE\Documents\AllplanTerrainToolkit\terrain_toolkit.log"
Read-Host "Press Enter to close"
