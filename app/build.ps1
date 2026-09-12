# Compatibility entry point. Dependencies: requirements.txt and pyinstaller.
& (Join-Path $PSScriptRoot 'build-v4.ps1')
if (-not $?) { exit 1 }
