Run automated FS25 map slices until failure or human verification.

Run:

```powershell
.\scripts\fs25.ps1 start --all
```

Stop only if a gate fails or the next gate is human-only. Then run `.\scripts\fs25.ps1 status` and summarize the result.
