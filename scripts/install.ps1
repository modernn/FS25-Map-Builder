param(
    [ValidateSet("codex", "claude", "both")]
    [string]$Target = "both",

    [ValidateSet("user", "project")]
    [string]$Scope = "user",

    [string]$ProjectPath = (Get-Location).Path
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$SkillsSource = Join-Path $RepoRoot "skills"
$CommandsSource = Join-Path $RepoRoot "claude-commands"

function Copy-SkillSet {
    param(
        [string]$Destination
    )

    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    Get-ChildItem -Path $SkillsSource -Directory | ForEach-Object {
        $targetPath = Join-Path $Destination $_.Name
        if (Test-Path -LiteralPath $targetPath) {
            Remove-Item -LiteralPath $targetPath -Recurse -Force
        }
        Copy-Item -LiteralPath $_.FullName -Destination $targetPath -Recurse
        Write-Host "Installed skill: $targetPath"
    }
}

function Copy-ClaudeCommands {
    param(
        [string]$Destination
    )

    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    Get-ChildItem -Path $CommandsSource -File -Filter "*.md" | ForEach-Object {
        $targetPath = Join-Path $Destination $_.Name
        Copy-Item -LiteralPath $_.FullName -Destination $targetPath -Force
        Write-Host "Installed Claude command: $targetPath"
    }
}

if ($Scope -eq "user") {
    $CodexSkills = Join-Path $HOME ".codex\skills"
    $ClaudeSkills = Join-Path $HOME ".claude\skills"
    $ClaudeCommands = Join-Path $HOME ".claude\commands"
} else {
    $ProjectRoot = Resolve-Path $ProjectPath
    $CodexSkills = Join-Path $ProjectRoot ".codex\skills"
    $ClaudeSkills = Join-Path $ProjectRoot ".claude\skills"
    $ClaudeCommands = Join-Path $ProjectRoot ".claude\commands"
}

if ($Target -in @("codex", "both")) {
    Copy-SkillSet -Destination $CodexSkills
}

if ($Target -in @("claude", "both")) {
    Copy-SkillSet -Destination $ClaudeSkills
    Copy-ClaudeCommands -Destination $ClaudeCommands
}

Write-Host ""
Write-Host "Install complete. Start a new Codex or Claude Code session for command discovery to refresh."

