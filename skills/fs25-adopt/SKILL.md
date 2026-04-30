---
name: fs25-adopt
description: Adopt an existing Farming Simulator 25 map repo into FS25 Map Builder. Use when the user wants to go into an existing project, inspect current profiles/build outputs, add the FS25 wrapper if missing, create adoption notes, or make existing FS25 work manageable with the $fs25 command loop.
---

# FS25 Adopt

Attach FS25 Map Builder to an existing project without overwriting useful local work.

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
5. Run from anywhere:

```powershell
python <project_setup.py> adopt --project <existing-project-path>
```

If no profile exists, include:

```powershell
--project-name "<name>" --location "<location>" --map-size-m <meters> --center-lat <lat> --center-lon <lon> --landmark "<a; b; c>"
```

Use `--force` only when the user explicitly wants regenerated files overwritten.

## Result

The helper writes `docs/fs25_adoption.md`, creates missing bootstrap files, and leaves existing wrappers/profiles in place unless `--force` is used.

After adoption, run:

```powershell
.\scripts\fs25.ps1 status
.\scripts\fs25.ps1 recommend
```
