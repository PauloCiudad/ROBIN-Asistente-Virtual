# Construye el ejecutable y el instalador de ROBIN.
#   powershell -ExecutionPolicy Bypass -File packaging\build.ps1
# Requisitos: uv, Inno Setup 6 (winget install JRSoftware.InnoSetup).
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$version = (Select-String -Path "src\robin\__init__.py" -Pattern '__version__ = "(.+)"').Matches[0].Groups[1].Value
Write-Host "== ROBIN $version"

Write-Host "== Tests"
uv run pytest -q
if ($LASTEXITCODE -ne 0) { throw "Los tests fallaron" }

Write-Host "== Icono"
uv run python packaging\make_icon.py

Write-Host "== PyInstaller"
uv run pyinstaller packaging\robin.spec --noconfirm --distpath build\dist --workpath build\work --log-level WARN
if (-not (Test-Path "build\dist\ROBIN\ROBIN.exe")) { throw "PyInstaller no generó ROBIN.exe" }

Write-Host "== Instalador"
$iscc = @(
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw "No encuentro Inno Setup 6 (ISCC.exe). Instálalo: winget install JRSoftware.InnoSetup" }
& $iscc "/DAppVersion=$version" "packaging\robin.iss"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup falló" }

Get-ChildItem "build\installer\*.exe" | ForEach-Object {
    $hash = (Get-FileHash $_.FullName -Algorithm SHA256).Hash
    "{0}  ({1:N0} MB)  SHA256 {2}" -f $_.Name, ($_.Length / 1MB), $hash
}
