param(
    [string]$ProjectPath = (Get-Location).Path
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$ProjectRoot = Resolve-Path $ProjectPath

$CommandSkills = @(
    "fs25",
    "fs25-map-builder",
    "fs25-init",
    "fs25-adopt",
    "fs25-next",
    "fs25-progress",
    "fs25-start",
    "fs25-autonomous",
    "fs25-run",
    "fs25-dry",
    "fs25-list",
    "fs25-install",
    "fs25-help"
)

foreach ($name in $CommandSkills) {
    $source = Join-Path $ProjectRoot ".codex\skills\$name"
    if (-not (Test-Path -LiteralPath $source)) {
        $source = Join-Path $ProjectRoot "skills\$name"
    }
    if (Test-Path -LiteralPath $source) {
        $dest = Join-Path $RepoRoot "skills\$name"
        if (Test-Path -LiteralPath $dest) {
            Remove-Item -LiteralPath $dest -Recurse -Force
        }
        Copy-Item -LiteralPath $source -Destination $dest -Recurse
        Write-Host "Synced skill: $name"
    }
}

$templateScripts = Join-Path $RepoRoot "templates\project-wrapper\scripts"
New-Item -ItemType Directory -Force -Path $templateScripts | Out-Null

foreach ($scriptName in @("fs25.ps1", "fs25.py")) {
    $source = Join-Path $ProjectRoot "scripts\$scriptName"
    if (Test-Path -LiteralPath $source) {
        Copy-Item -LiteralPath $source -Destination (Join-Path $templateScripts $scriptName) -Force
        Write-Host "Synced wrapper: $scriptName"
    }
}

Write-Host ""
Write-Host "Sync complete. Review git diff before committing."
