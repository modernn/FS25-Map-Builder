---
name: fs25-start
description: Run automated FS25 map slices until failure or human verification.
---

# FS25 Start

Run:

```powershell
.\scripts\fs25.ps1 start --all
```

Keep the build moving through every currently available automated slice. Stop only when:

- a slice command fails,
- a slice command finishes but its gate still fails, or
- the next gate is human verification.

After it stops, run `.\scripts\fs25.ps1 status` and summarize the gate state. Do not hand package/install commands back to the user when they are automated gates; run them through `start --all`. Report only what you ran, what passed/failed, and any required human action.
