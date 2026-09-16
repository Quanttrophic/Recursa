# Sign Recursa.exe and the installer with an Authenticode certificate.
# Runs only when WINDOWS_CERT_PFX_BASE64 and WINDOWS_CERT_PASSWORD secrets exist.
#   powershell -File packaging\windows\sign.ps1 <file> [<file> ...]
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Files)
$ErrorActionPreference = "Stop"
$pfx = Join-Path $env:RUNNER_TEMP "recursa-cert.pfx"
[IO.File]::WriteAllBytes($pfx, [Convert]::FromBase64String($env:WINDOWS_CERT_PFX_BASE64))
$signtool = Get-ChildItem "C:\Program Files (x86)\Windows Kits\10\bin" -Recurse -Filter signtool.exe |
  Where-Object { $_.FullName -match "x64" } | Sort-Object FullName -Descending | Select-Object -First 1
foreach ($f in $Files) {
  & $signtool.FullName sign /f $pfx /p $env:WINDOWS_CERT_PASSWORD /fd SHA256 `
    /tr http://timestamp.digicert.com /td SHA256 $f
  if ($LASTEXITCODE -ne 0) { throw "signing failed: $f" }
}
Remove-Item $pfx
