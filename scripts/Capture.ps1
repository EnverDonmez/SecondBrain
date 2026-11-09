param(
    [string]$File,
    [string]$Note = '',
    [string]$Scope,
    [ValidateRange(0, 3)][int]$Sensitivity = 1
)

$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent $PSScriptRoot
$python = Join-Path $workspace '.venv\Scripts\python.exe'
$tokenFile = Join-Path $workspace 'data\connections\codex\client.token'
$previousTokenFile = $env:SB_TOKEN_FILE

Push-Location -LiteralPath $workspace
try {
    if (-not $env:SB_TOKEN -and -not $env:SB_TOKEN_FILE -and (Test-Path -LiteralPath $tokenFile)) {
        $env:SB_TOKEN_FILE = $tokenFile
    }
    $options = @('-m', 'second_brain', 'clip', '--sensitivity', $Sensitivity)
    if ($Scope) { $options += @('--scope', $Scope) }
    if ($Note) { $options += "--note=$Note" }

    if ($File) {
        $path = (Resolve-Path -LiteralPath $File).ProviderPath
        & $python @options --file $path
    } else {
        $OutputEncoding = [System.Text.UTF8Encoding]::new($false)
        Get-Clipboard -Raw | & $python @options --stdin
    }
    if ($LASTEXITCODE -ne 0) { throw 'Beyne at işlemi tamamlanamadı.' }
} finally {
    $env:SB_TOKEN_FILE = $previousTokenFile
    Pop-Location
}
