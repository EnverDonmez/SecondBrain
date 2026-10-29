param([ValidateRange(1,65535)][int]$Port = 8765, [switch]$Background)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) { throw 'Önce .\scripts\Setup.ps1 çalıştırın.' }
if ($Background) {
    $dataPath = Join-Path $projectRoot 'data'
    & $venvPython -m second_brain --data $dataPath start --port $Port
    if ($LASTEXITCODE -ne 0) { throw 'Sunucu başlatılamadı; yukarıdaki tanılamayı inceleyin.' }
    Write-Host "Second Brain v0.1 beta hazır: http://127.0.0.1:$Port"
    Write-Host "Giriş anahtarı: $(Join-Path $dataPath 'owner.token')"
} else {
    Set-Location -LiteralPath $projectRoot
    & $venvPython -m second_brain serve --port $Port
    if ($LASTEXITCODE -ne 0) { throw 'Sunucu kapandı; yukarıdaki tanılamayı inceleyin.' }
}
