---
name: fs25-init
description: Initialize a new Farming Simulator 25 real-world map project from Codex or Claude Code. Use when the user wants a GSD-like guided setup interview, project brief, profile JSON, starter wrapper, or new FS25 map repo scaffold.
---

# FS25 Init

Create a new FS25 map project by asking a short setup interview, then running the bundled setup helper. The user invokes the command; the agent runs the helper and reports what it created.

## Workflow

1. Ask only for missing essentials:
   - project folder/repo path
   - project/map name
   - real-world location
   - center latitude and longitude, or an exact bbox if known
   - map size in meters
   - required landmarks, shops, farmyards, fields, and public anchors
   - FS25 mods folder if install automation should be enabled
2. Resolve the helper script:
   - preferred: sibling installed skill `../fs25-map-builder/scripts/project_setup.py`
   - fallback: repo clone `skill-repos/FS25-Map-Builder/skills/fs25-map-builder/scripts/project_setup.py`
3. Run the helper yourself:

```powershell
python <project_setup.py> init --project <path> --project-name "<name>" --location "<location>" --map-size-m <meters> --center-lat <lat> --center-lon <lon> --landmark "<a; b; c>"
```

Use `--bbox-wgs84-wsen=<west,south,east,north>` when the user gives an exact bounding box; the helper derives the center from the bbox if center lat/lon are absent.

Do not stop by telling the user to run the command. Run it, inspect the output, then summarize the created scaffold and next agent action. Do not present PowerShell wrapper commands as user tasks unless the user explicitly asks for them or the project has reached human verification.

## Result

The helper creates:

- `.fs25-map-builder.json`
- `profiles/<profile-id>.json`
- `docs/fs25_project_brief.md`
- `docs/fs25_map_state.md`
- `docs/fs25_fix_queue.md`
- `docs/fs25_gsd_chain.md`
- `docs/morning_human_verification.md`
- `.planning/PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md`, `STATE.md`, `TASKS.md`
- `.planning/milestones/fs25-map-ready.md`
- `.planning/phases/*/PLAN.md`
- `scripts/fs25.ps1`
- `scripts/fs25.py`

The generated wrapper is a bootstrap. It should recommend planning/source work until project-specific deterministic slices and QA gates are implemented.
