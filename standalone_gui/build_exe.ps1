$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Repo = Split-Path -Parent $Root
Set-Location $Root

python -m pip install --quiet pyinstaller
python -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --name AperiodicGenerator `
  --distpath "$Root\dist" `
  --workpath "$Root\build" `
  --specpath "$Root\build" `
  "$Root\untiling_generator.py"

$Exe = Join-Path $Root "dist\AperiodicGenerator.exe"
if (-not (Test-Path $Exe)) { throw "Build failed: missing $Exe" }

$Downloads = Join-Path $Repo "site\assets\downloads"
if (Test-Path $Downloads) {
  Copy-Item -Force $Exe (Join-Path $Downloads "AperiodicGenerator.exe")
  Write-Host "Copied to site/assets/downloads/AperiodicGenerator.exe"
}

Write-Host "Built $Exe"
