Run one named FS25 map slice.

Agent uses the user's argument as the slice name:

```powershell
.\scripts\fs25.ps1 run $ARGUMENTS
```

If no argument is provided, run:

```powershell
.\scripts\fs25.ps1 list
```

Do not present the wrapper command as a user next step. Report what the agent ran and whether the gate passed.
