$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
Set-Location -LiteralPath $projectRoot
& (Join-Path $PSScriptRoot 'Verify.ps1')
& $venvPython -m pip wheel --no-deps --no-build-isolation --wheel-dir dist .
if ($LASTEXITCODE -ne 0) { throw 'Wheel oluşturulamadı.' }
$version = (& $venvPython -c 'from second_brain import __version__; print(__version__)').Trim()
$wheel = Join-Path $projectRoot "dist\second_brain_os-$version-py3-none-any.whl"
$wheelTarget = Join-Path $projectRoot ".test-tmp\wheel-install-$version"
& $venvPython -m pip install --no-deps --no-index --upgrade --target $wheelTarget $wheel
if ($LASTEXITCODE -ne 0) { throw 'Wheel test hedefine kurulamadı.' }
& $venvPython (Join-Path $PSScriptRoot 'check_wheel.py')
if ($LASTEXITCODE -ne 0) { throw 'Wheel kaynak/migration denetimi başarısız.' }
$runDirectory = Join-Path $projectRoot '.test-tmp\wheel-run'
New-Item -ItemType Directory -Path $runDirectory -Force | Out-Null
$previousPythonPath = $env:PYTHONPATH
$previousVerifyInstalled = $env:SB_VERIFY_INSTALLED
$previousPackageRoot = $env:SB_VERIFY_PACKAGE_ROOT
try {
    $env:PYTHONPATH = $wheelTarget
    $env:SB_VERIFY_INSTALLED = '1'
    $env:SB_VERIFY_PACKAGE_ROOT = $wheelTarget
    Push-Location -LiteralPath $runDirectory
    try { & $venvPython (Join-Path $PSScriptRoot 'verify_beta.py') }
    finally { Pop-Location }
    if ($LASTEXITCODE -ne 0) { throw 'Kurulu wheel beta kabul testi başarısız.' }
} finally {
    $env:PYTHONPATH = $previousPythonPath
    $env:SB_VERIFY_INSTALLED = $previousVerifyInstalled
    $env:SB_VERIFY_PACKAGE_ROOT = $previousPackageRoot
}
$evidenceDirectory = Join-Path $projectRoot 'reports\beta-0.1'
New-Item -ItemType Directory -Path $evidenceDirectory -Force | Out-Null
foreach ($evidenceName in @('tests.xml', 'secret-scan.json', 'wheel-check.json')) {
    Copy-Item -LiteralPath (Join-Path $projectRoot "reports\$evidenceName") -Destination (Join-Path $evidenceDirectory $evidenceName)
}
& $venvPython (Join-Path $PSScriptRoot 'build_release.py')
if ($LASTEXITCODE -ne 0) { throw 'Kaynak dağıtımı oluşturulamadı.' }
Write-Host 'v0.1 beta paketleri dist/ altında hazır; doğrulama kanıtları reports/ altında.'
