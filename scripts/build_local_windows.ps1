# Local Windows build (Python 3.12 from python.org). Run from the repo root:
#   powershell -ExecutionPolicy Bypass -File scripts\build_local_windows.ps1
$ErrorActionPreference = "Stop"
py -3.12 -m venv .venv-build
.\.venv-build\Scripts\python -m pip install --upgrade pip
.\.venv-build\Scripts\python -m pip install -r requirements-build.txt
.\.venv-build\Scripts\pyinstaller --noconfirm --clean recursa.spec
$p = Start-Process .\dist\Recursa\Recursa.exe -ArgumentList "--selfcheck","--report=selfcheck.txt" -Wait -PassThru
if ($p.ExitCode -ne 0) { throw "self-check failed" }
$p = Start-Process .\dist\Recursa\Recursa.exe -ArgumentList "--smoke-test","--report=smoke.txt" -Wait -PassThru
if ($p.ExitCode -ne 0) { throw "smoke test failed" }
New-Item -ItemType Directory -Force release | Out-Null
Compress-Archive -Path dist\Recursa -DestinationPath release\Recursa-windows-x64-portable.zip -Force
Write-Host "release\Recursa-windows-x64-portable.zip"
Write-Host "For the installer: install Inno Setup 6, then run: iscc packaging\windows\recursa.iss"
