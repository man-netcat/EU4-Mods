---
name: eu4-new-mod
description: Scaffold a new EU4 mod in the EU4-Mods repository with new_mod.py and what the generated files contain.
---

# New mod

```bash
cd /home/user/EU4-Mods
python3 new_mod.py "<mod name>"
```

Creates `<mod name>/descriptor.mod` and `<mod name>.mod` beside it (name, `supported_version="v1.37.5.0"`, empty tags, and a
`path=` line in the outer file that points at the folder on the machine that ran the script). The game version for the
repository is EU4 v1.37.5.0. Then add the mod's own files; each mod is one folder plus its `.mod`. If the mod is generated, put its
tools in `<mod>/tools/`, say in its own README/AGENTS what is generated, and add a workflow under `.github/workflows/`
modelled on the existing two. Commit to the session's branch; open no PR unless asked.
