$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$venvPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
& $venvPython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Bağımlılık kontrolü başarısız.' }
$parseErrors = @()
Get-ChildItem -LiteralPath $PSScriptRoot -Filter *.ps1 | ForEach-Object {
    $tokens = $null
    $errors = $null
    [void][System.Management.Automation.Language.Parser]::ParseFile($_.FullName, [ref]$tokens, [ref]$errors)
    $parseErrors += $errors
}
if ($parseErrors.Count) { throw ($parseErrors | Out-String) }
& $venvPython -m ruff check second_brain tests scripts
if ($LASTEXITCODE -ne 0) { throw 'Lint başarısız.' }
& $venvPython -m ruff format --check second_brain tests scripts
if ($LASTEXITCODE -ne 0) { throw 'Biçim kontrolü başarısız.' }
& $venvPython -m mypy second_brain --ignore-missing-imports --check-untyped-defs
if ($LASTEXITCODE -ne 0) { throw 'Tip kontrolü başarısız.' }
& $venvPython -m pytest -q --basetemp=.test-tmp/verify --junitxml=reports/tests.xml
if ($LASTEXITCODE -ne 0) { throw 'Testler başarısız.' }
node --check second_brain/static/app.js
if ($LASTEXITCODE -ne 0) { throw 'Arayüz sözdizimi kontrolü başarısız.' }
node --check second_brain/static/observer.js
if ($LASTEXITCODE -ne 0) { throw 'Gözlem arayüzü sözdizimi kontrolü başarısız.' }
& $venvPython scripts/scan_secrets.py
if ($LASTEXITCODE -ne 0) { throw 'Kaynak secret taraması bulgu üretti.' }
