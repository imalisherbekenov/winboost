$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    $appVersion = (Select-String -Path WinBoostGUI.py -Pattern 'APP_TITLE\s*=\s*"WinBoost ([\d.]+)"').Matches[0].Groups[1].Value
    if (-not $appVersion) { throw 'Cannot determine application version' }
    python -m PyInstaller --noconfirm --onefile --noconsole --name "WinBoost-$appVersion" `
        --distpath '..\dist' --workpath 'build\v4' --specpath 'build' `
        --add-data "$PSScriptRoot\assets;assets" --collect-all dearpygui --hidden-import psutil `
        --icon "$PSScriptRoot\..\docs\design\logo\WinBoost.ico" WinBoostGUI.py
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed: $LASTEXITCODE" }
    $builtFile = Get-Item "..\dist\WinBoost-$appVersion.exe"
    $downloadFolder = New-Item -ItemType Directory -Force '..\site\public\downloads'
    Copy-Item -LiteralPath $builtFile.FullName -Destination (Join-Path $downloadFolder.FullName $builtFile.Name) -Force
    $checksum = (Get-FileHash -Algorithm SHA256 -LiteralPath $builtFile.FullName).Hash.ToLowerInvariant()
    "$checksum  $($builtFile.Name)" | Set-Content -LiteralPath (Join-Path $downloadFolder.FullName "SHA256.txt") -Encoding ascii
    Get-FileHash -Algorithm SHA256 -LiteralPath $builtFile.FullName | Format-List
    Write-Host "Built $($builtFile.FullName)"
} finally {
    Pop-Location
}
