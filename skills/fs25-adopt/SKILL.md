---
name: fs25-adopt
description: Adopt an existing Farming Simulator 25 map repo into FS25 Map Builder. Use when the user wants to go into an existing project, inspect current profiles/build outputs, add the FS25 wrapper if missing, create adoption notes, or make existing FS25 work manageable with the $fs25 command loop.
---

# FS25 Adopt

Attach FS25 Map Builder to an existing project without overwriting useful local work. The user runs the Codex/Claude command; the agent runs the helper and reports the result.

## Workflow

1. Inspect the project first:
   - `profiles/*.json`
   - `scripts/fs25.ps1`
   - `scripts/fs25.py`
   - `build/*`
   - existing docs and QA artifacts
2. If a profile exists, let the helper infer map size, center, bbox, profile id, and preview zip.
3. If no profile exists, ask the same essentials as `$fs25-init`: location, center lat/lon, map size, and required landmarks.
4. Resolve the helper script:
   - preferred: sibling installed skill `../fs25-map-builder/scripts/project_setup.py`
   - fallback: repo clone `skill-repos/FS25-Map-Builder/skills/fs25-map-builder/scripts/project_setup.py`
5. Run the helper yourself from anywhere:

```powershell
python <project_setup.py> adopt --project <existing-project-path>
```

If no profile exists, include:

```powershell
--project-name "<name>" --location "<location>" --map-size-m <meters> --center-lat <lat> --center-lon <lon> --landmark "<a; b; c>"
```

Use `--force` only when the user explicitly wants regenerated files overwritten.

Do not stop by telling the user to run the command. Run it, inspect the output, then summarize the written/kept files and the next agent action.

## Result

The helper writes or preserves:

- `.fs25-map-builder.json`
- `docs/fs25_adoption.md`
- `docs/fs25_project_brief.md`
- `docs/fs25_map_state.md`
- `docs/fs25_fix_queue.md`
- `docs/fs25_gsd_chain.md`
- `docs/morning_human_verification.md`
- `.planning/PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md`, `STATE.md`, `TASKS.md`
- `.planning/milestones/fs25-map-ready.md`
- `.planning/phases/*/PLAN.md`
- missing bootstrap wrapper files under `scripts/`

After adoption, inspect status/recommendation yourself. Do not present PowerShell wrapper commands as user tasks unless the user explicitly asks for them or the project has reached human verification.
