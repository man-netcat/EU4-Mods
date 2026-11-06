---
name: cl-new-religion
description: Task - add a religion (a CK3 faith) or a rite to Charlemagne's Legacy. Says what a cloud session can do and what needs the user's CK3 install.
---

# A new religion or rite

A religion IS a CK3 faith under CK3's own key; a tag's religion is the faith its ruler's rite belongs to. Nobody maps by
hand: `tools/religions.py` writes `common/religions/00_religion.txt` from the faiths `tags.db` names
(`religions.TEMPLATE` says which base-game block a faith copies; `EDITS`), `tools/faiths.py` sets names and colours.

## Faith

```bash
python3 tools/faiths.py                      # rewrite the religions file, its loc and sprites
python3 tools/addreligion.py KEY [--faith NAME] [--clone SRC] [--into GROUP] [--after SIBLING] \
        [--name STR] [--desc STR] [--color R G B] [--icon N] [--holy-sites PID ...] [--heretics X ...] [--icon-only]
```

`addreligion.py` clones a block, writes the loc (`localisation/replace/karolingian_religion_l_english.yml`), the registry
row and extends the four icon strips from the CK3 icon. It is idempotent after a failed step. Religion groups follow CK3's
religion family (`faiths.CK3_RELIGION_GROUP`); validate fails misplaced groups, a used religion that is not a lifted faith,
wrong colours or names, shared icon frames.

## Rite (religious school)

Rites are rows in `tools/rites.py` (`RITES`: group, key, CK3 rite, name, desc, one modifier, placeholder colour;
`RITE_RELIGIONS`: which EU4 religion follows each rite). The build rewrites the `religious_schools` blocks between
`BEGIN/END RITES` markers, `karolingian_rites.txt` (static modifiers and scripted effects), the rites gfx and loc: edit the
tables only. Validate fails a used religion without rites, a ruler with no rite or a rite without a school.

## What the cloud cannot do

The reference copy is text only: CK3's faith and rite icons are missing, so `python3 tools/faiths.py icons` and the real
icon strips need the user's CK3 install (validate warns "religion icons not checked against CK3"). Placeholder rite icons
are generated when missing; say which icons are placeholders.

Then `tagloc.py write`, `build.py`, `validate.py`, `selfcontained.py`, `AGENTS.md`, commit, CI.
