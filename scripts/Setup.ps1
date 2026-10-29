param([switch]$Full, [switch]$Dev, [switch]$SkipModels, [switch]$SkipSpeech)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$bundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if (Test-Path -LiteralPath $bundledPython) {
    $projectPython = $bundledPython
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $projectPython = (& py -3 -c 'import sys; print(sys.executable)').Trim()
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $projectPython = (Get-Command python).Source
} else {
    throw 'Python 3.12+ gerekli. python.org üzerinden kurup Setup.ps1 komutunu tekrar çalıştırın.'
}
& $projectPython -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)'
if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 veya üstü gerekli.' }
$venvPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    & $projectPython -m venv --without-pip .venv
    if ($LASTEXITCODE -ne 0) { throw 'Sanal ortam oluşturulamadı.' }
}
& $venvPython -m pip --version *> $null
if ($LASTEXITCODE -ne 0) {
    & $projectPython -m pip --python .venv install pip
    if ($LASTEXITCODE -ne 0) { throw 'pip kurulamadı. Python kurulumunda pip etkin olmalı.' }
}
$extras = @()
if ($Full) { $extras += 'engines'; $extras += 'media' }
if ($Dev) { $extras += 'dev' }
$installTarget = '.'
if ($extras.Count -gt 0) { $installTarget = '.[' + ($extras -join ',') + ']' }
& $venvPython -m pip install -c requirements.lock -e $installTarget
if ($LASTEXITCODE -ne 0) { throw 'Yerel paket kurulamadı.' }
& $venvPython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Bağımlılıklar tutarsız; yukarıdaki pip check çıktısını inceleyin.' }
if ($Full -and -not $SkipModels) {
    $env:HF_HOME = Join-Path $projectRoot 'data\models\hf'
    $env:HF_HUB_DISABLE_TELEMETRY = '1'
    if (-not (Test-Path -LiteralPath 'data\models\ready.json')) {
        & $venvPython -m second_brain model-install
        if ($LASTEXITCODE -ne 0) { Write-Warning 'Semantik model kurulamadı; FTS5/BM25 ve çekirdek çevrimdışı çalışır.' }
    }
    if (-not $SkipSpeech -and -not (Test-Path -LiteralPath 'data\models\speech\ready.json')) {
        & $venvPython -m second_brain speech-model-install
        if ($LASTEXITCODE -ne 0) { Write-Warning 'Yerel ses modeli kurulamadı; orijinaller ve manuel dökümler korunur.' }
    }
}
if (-not $Full) { Write-Host 'Çekirdek beta kuruldu. Yerel medya/semantik motorları eklemek için: .\scripts\Setup.ps1 -Full' }
Write-Host 'Kurulum tamamlandı. Başlatmak için: .\scripts\Start.ps1'
