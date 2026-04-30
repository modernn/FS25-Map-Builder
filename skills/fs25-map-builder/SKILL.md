---
name: fs25-map-builder
description: Build and QA Farming Simulator 25 real-world maps with reproducible slices, source provenance, packaging checks, and Codex/Claude command dispatch.
---

# FS25 Map Builder

Use this skill when a user wants to build, rebuild, QA, package, install, or manage a Farming Simulator 25 map from real-world data.

## Core Pattern

Run the map as small slices:

1. Recommend the next slice.
2. Run one deterministic generator or a tightly coupled generator pair.
3. Run the paired QA gate.
4. Stop on failure.
5. Record evidence before claiming anything is done.

## Expected Project Wrapper

Prefer a project-local command wrapper:

```powershell
.\scripts\fs25.ps1 recommend
.\scripts\fs25.ps1 status
.\scripts\fs25.ps1 start
.\scripts\fs25.ps1 start --all
.\scripts\fs25.ps1 run <slice-name>
.\scripts\fs25.ps1 install
```

If the wrapper is missing, inspect `templates/project-wrapper/` from the FS25-Map-Builder repo and add a project-specific wrapper before creating more command skills.

## Commands

Use the command skills when available:

- `$fs25-next` / `/fs25-next`
- `$fs25-progress` / `/fs25-progress`
- `$fs25-start` / `/fs25-start`
- `$fs25-autonomous` / `/fs25-autonomous`
- `$fs25-run <slice>` / `/fs25-run <slice>`
- `$fs25-install` / `/fs25-install`

## QA Expectations

Each map project should eventually gate:

- Source manifest and license/provenance.
- Heightmap dimensions and relief.
- Road masks, clutter budget, and road grading.
- Field geometry, farmland IDs, crop/density masks.
- Region-specific crops, foliage, economy, and seasonal assumptions.
- Landscape/foliage/tree density and hard-exclusion overlaps.
- Placeables, store/sell/animal gameplay anchors, and local references.
- Map boundary containment.
- Package contents and excluded raw/reference data.
- GIANTS Editor and in-game human verification.

If a failure is seen twice manually, add a script or wrapper gate for it.

