---
name: fs25-autonomous
description: Run FS25 automated slices until failure or human verification.
---

# FS25 Autonomous

Run `.\scripts\fs25.ps1 start --all`. Stop at the first failed gate or human test gate, then run `.\scripts\fs25.ps1 status` and summarize the result.

This is the same automation loop used by `$fs25-start`; keep this skill as an explicit "overnight/autonomous" alias.
