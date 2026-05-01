---
name: fs25
description: "Dispatch FS25 map commands from Codex or Claude Code: init, adopt, next, progress, start, autonomous, run, dry, list, install, and help."
---

# FS25 Command Dispatcher

If the user gives no subcommand, recommend the next action.

Policy: wrapper commands are agent-internal. Run them yourself and tell the user what you ran and what happened. Do not present PowerShell commands as user next steps unless the user explicitly asks or a human FS25 test gate is reached.

| User command | Agent action |
|---|---|
| `$fs25-init`, `/fs25-init` | use the `fs25-init` guided project setup workflow |
| `$fs25-adopt`, `/fs25-adopt` | use the `fs25-adopt` existing-project adoption workflow |
| `$fs25`, `/fs25` | `.\scripts\fs25.ps1 recommend` |
| `$fs25-next`, `/fs25-next` | `.\scripts\fs25.ps1 recommend` |
| `$fs25-progress`, `/fs25-progress` | `.\scripts\fs25.ps1 status` |
| `$fs25-start`, `/fs25-start` | `.\scripts\fs25.ps1 start --all` |
| `$fs25-autonomous`, `/fs25-autonomous` | `.\scripts\fs25.ps1 start --all` |
| `$fs25-run <slice>`, `/fs25-run <slice>` | `.\scripts\fs25.ps1 run <slice>` |
| `$fs25-dry <slice>`, `/fs25-dry <slice>` | `.\scripts\fs25.ps1 run <slice> --dry-run` |
| `$fs25-list`, `/fs25-list` | `.\scripts\fs25.ps1 list` |
| `$fs25-install`, `/fs25-install` | `.\scripts\fs25.ps1 install` |
| `$fs25-help`, `/fs25-help` | summarize the installed commands |

Keep responses short: what the agent ran, result, next agent action or required human action.
