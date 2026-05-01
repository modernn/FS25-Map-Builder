# FS25 Map Builder

Reusable Codex and Claude Code skills for building Farming Simulator 25 maps from real-world locations.

This repo started from the Focused Butte Alaska map workflow and is meant to stay updated as that map build reveals better automation, QA gates, and project-management patterns.

## What It Installs

- Codex skills:
  - `fs25-map-builder`
  - `fs25`
  - `fs25-init`
  - `fs25-adopt`
  - `fs25-next`
  - `fs25-progress`
  - `fs25-start`
  - `fs25-autonomous`
  - `fs25-run`
  - `fs25-dry`
  - `fs25-list`
  - `fs25-install`
  - `fs25-help`
- Claude Code skills with the same names.
- Claude Code slash-command shims under `.claude/commands`, for `/fs25-next`, `/fs25-start`, etc.

## Install

From a clone of this repo:

```powershell
.\scripts\install.ps1 -Target both -Scope user
```

Use user scope for normal Codex and Claude Code command discovery. Do not also install the same `fs25*` command skills into a project unless you are intentionally testing a local skill copy; user-scope plus project-scope installs can show duplicate command entries.

Install into a specific project instead:

```powershell
.\scripts\install.ps1 -Target both -Scope project -ProjectPath C:\Claude\FarmSimulatorAlaskaMap
```

## Codex Commands

After opening a new Codex session in a project with the skills installed:

```text
$fs25-init
$fs25-adopt
$fs25-next
$fs25-progress
$fs25-start
$fs25-autonomous
$fs25-run landscape-foliage
$fs25-install
```

## Claude Code Commands

After opening a new Claude Code session:

```text
/fs25-init
/fs25-adopt
/fs25-next
/fs25-progress
/fs25-start
/fs25-autonomous
/fs25-run landscape-foliage
/fs25-install
```

Claude can also load the matching skills by name.

## Project Wrapper Requirement

The command skills expect the target FS25 map project to provide:

```text
scripts/fs25.ps1
scripts/fs25.py
```

Use `templates/project-wrapper/` as a starter, or keep using the wrapper from the Focused Butte map repo.

For a new project, use `$fs25-init` or `/fs25-init`; it asks the setup questions, then the agent runs the helper to create a brief/profile/bootstrap wrapper plus a milestone, roadmap, requirements, tasks, phase plans, map state, fix queue, and human verification checklist.

For an existing project, use `$fs25-adopt` or `/fs25-adopt`; it inspects the repo, keeps existing wrappers/profiles when present, and writes adoption notes plus the same planning bundle. The intent is that Codex or Claude runs the helper for you and reports the result.

## Updating From A Map Project

When the active map project improves the workflow, sync the skills back into this repo:

```powershell
.\scripts\update-from-project.ps1 -ProjectPath C:\Claude\FarmSimulatorAlaskaMap
```

Review the diff, then commit and push.
