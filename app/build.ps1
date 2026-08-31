# WinBoost Build Script
# Run: powershell -ExecutionPolicy Bypass -File build.ps1

$version = (Select-String -Path WinBoostGUI.py -Pattern 'APP_TITLE\s*=\s*"WinBoost ([\d.]+)"').Matches[0].Groups[1].Value
Write-Host "=== WinBoost $version Build ===" -ForegroundColor Cyan

# Install deps
Write-Host "[1/3] Installing dependencies..." -ForegroundColor Yellow
pip install -q -r requirements.txt pyinstaller

# Clean old build
Write-Host "[2/3] Cleaning old build..." -ForegroundColor Yellow
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }

# Build exe
Write-Host "[3/3] Building WinBoost.exe ..." -ForegroundColor Yellow
pyinstaller --onefile --noconsole --name WinBoost `
    --add-data "modules;modules" `
    --collect-all dearpygui `
    --hidden-import psutil `
    --uac-admin `
    --icon NONE `
    WinBoostGUI.py

if (Test-Path "dist/WinBoost.exe") {
    $size = (Get-Item "dist/WinBoost.exe").Length / 1MB
    Write-Host ""
    Write-Host "=== BUILD SUCCESS ===" -ForegroundColor Green
    Write-Host "File: dist/WinBoost.exe" -ForegroundColor Green
    Write-Host ("Size: {0:N1} MB" -f $size) -ForegroundColor Green
} else {
    Write-Host "=== BUILD FAILED ===" -ForegroundColor Red
}
