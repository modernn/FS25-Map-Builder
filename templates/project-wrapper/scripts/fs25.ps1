param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CommandArgs
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $RepoRoot
try {
    $VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
    if (Test-Path $VenvPython) {
        & $VenvPython "scripts\fs25.py" @CommandArgs
    } else {
        & python "scripts\fs25.py" @CommandArgs
    }
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
