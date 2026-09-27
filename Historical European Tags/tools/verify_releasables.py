#!/usr/bin/env python3
"""Verification for the HRE Releasables mod.

Checks every releasable tag for strictly correct wiring:

  * tag definition (mod file, no base-game collision)
  * common/countries/<ref> file (color, graphical_culture)
  * flag file gfx/flags/<TAG>.tga            (missing -> WARN, flags deferred)
  * history/countries/<TAG> - *.txt stub     (required keys, fixed_capital == capital)
  * capital province in mod                  (add_core, culture match, HRE, owner check)
  * release viability at 1444                (owner must not hold our province as its capital)
  * localisation                             (name + adjective)
  * national ideas                           (structure: 2 traditions, 7 ideas, ambition,
                                              trigger lock, free = yes) + idea localisation
  * idea shape against the base game         (tools/idea_inventory.py measures all 446
                                              vanilla country idea sets; a count vanilla
                                              itself uses is a WARN, one it never uses is
                                              a FAIL) + no effect repeated inside a group,
                                              no idea that grants nothing, no idea heavier
                                              than the vanilla norm
  * idea-key uniqueness vs vanilla and within the mod
  * orphan detection                         (stubs/cores without a tag, vice versa)
  * HRE coverage                             (non-capital provinces with no releasable
                                              tag yet - one WARN with the full list)
  * SQLite report database                  (tables meta, tags, checks, ideas,
                                              orphans - one row per tag with all
                                              collected data)

Usage:
    python3 verify_releasables.py [--game PATH] [--mod PATH] [--db PATH] [-q]
    python3 verify_releasables.py [--game PATH] [--mod PATH] remove TAG [TAG ...]
                                  [--dry-run]

Exit code 0 when no FAIL remains, 1 otherwise.

`remove` deletes every trace of a tag from the mod: the country_tags line,
the countries definition, the history stub, its add_core lines in province
files, the ideas block and its localisation - then re-verifies. Flags are
NEVER removed. `--dry-run` prints exactly what would be removed and changes
nothing.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# The base-game idea inventory lives next to this script and supplies the
# norms every idea group is measured against. Running this file directly
# already puts its own directory on sys.path; the fallback covers being
# imported from elsewhere.
try:
    import idea_inventory
except ImportError:  # pragma: no cover
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import idea_inventory

DEFAULT_GAME = Path("/home/rick/Paradox/Games/Europa Universalis IV")
DEFAULT_MOD = Path(
    "/home/rick/.local/share/Paradox Interactive/"
    "Europa Universalis IV/mod/Historical European Tags"
)

TAG_LINE_RE = re.compile(r'^\s*([A-Z0-9]{3})\s*=\s*"([^"]+)"')

# Known-intentional deviations: {tag: {check-key: reason}}.
# Checks listed here downgrade FAIL to WARN so the exit code stays clean
# while the deviation stays visible in the report.
#
# check-keys: ideas, add_core, culture, religion, not_releasable,
#             landed_vassal
KNOWN_EXCEPTIONS: dict[str, dict[str, str]] = {
    "FRB": {"ideas": "Freiburg has no national ideas yet (known pre-existing gap)"},
    "PST": {"ideas": "inherits vanilla POM_ideas via primary_culture = pommeranian"},
    "PSG": {"ideas": "inherits vanilla POM_ideas via primary_culture = pommeranian"},
    "NMB": {"ideas": "inherits vanilla BAV_ideas via primary_culture = bavarian"},
    "ATN": {
        "culture": "crusader principality: Frankish ruling caste over an Arabic-speaking province by design",
        "religion": "crusader Catholic state over a Sunni Levant by design",
    },
    "TPL": {
        "culture": "crusader county: Frankish ruling caste over an Arabic-speaking province by design",
        "religion": "crusader Catholic state over a Shiite Levant by design",
    },
    "CIL": {
        "culture": "Cilician Armenian kingdom: Armenian ruling caste over Turkified provinces by design",
        "religion": "the Armenian Apostolic Church is represented by the coptic faith, over Sunni-majority lands by design",
        "not_releasable": "no Cilician province is releasable-safe (Adana is the Ramadanid capital, Marash the Dulkadirid) - the Armenian rump state keeps its historic seat regardless",
    },
    "ORA": {
        "not_releasable": "Orange has no province of its own; it is tied to the Avignon enclave (202), which the Papal city holds as its capital. The claim surfaces via the Orange-Nassau decision instead.",
    },
    "WEI": {
        "add_core": "dormant by design: THU holds 4743 until the 1547 partition",
        "not_releasable": "dormant by design: Saxe-Weimar only arises from the 1572 Erfurt division; its ancestral seat Weimar stays THU's capital in 1444",
    },
    "GZR": {
        "landed_vassal": "Genoese Gazaria: the colony is on the map from day one, holding its ports directly as a vassal of Genoa",
    },
    "LGN": {
        "ideas": "inherits the shared mod SILESIAN_ideas group via primary_culture = schlesian",
        "landed_vassal": "Silesian duchy of Liegnitz: present in 1444, holding its seat directly as a vassal of the Crown of Bohemia",
    },
    "RCB": {
        "ideas": "inherits the shared mod SILESIAN_ideas group via primary_culture = schlesian",
        "landed_vassal": "Silesian duchy of Ratibor: present in 1444, holding its seat directly as a vassal of the Crown of Bohemia",
    },
    "WRC": {
        "ideas": "inherits the shared mod SILESIAN_ideas group via primary_culture = schlesian",
        "landed_vassal": "Silesian duchy of Wroclaw: present in 1444, holding its seat directly as a vassal of the Crown of Bohemia",
    },
    "PBH": {"ideas": "inherits vanilla POM_ideas via primary_culture = pommeranian"},
    "URG": {
        "landed_vassal": "Catalan county of Urgell: present in 1444, holding its seat directly under the Central Counties appanage of John II of Aragon, whose rule over it the Catalan revolt of 1442 was aimed at",
    },
    "ALV": {
        "landed_vassal": "ALV holds its own provinces at 1444 rather than being released from a liege, so the landed_vassal rules do not apply. It is a separate crown in personal union with POR, declared in history/diplomacy",
        "ideas": "no national ideas yet - the Algarve is a duplicate Portuguese crown in personal union, the same gap CIL and ATN carry",
    },
    "CGR": {
        "province_file": "dormant by design: the crown holds no land in 1444 and overrides no province, so 222, 223, 226 and 4546 stay pure vanilla until decisions/FormCatholicGranada.txt grants the cores and releases them",
        "add_core": "dormant by design: the crown carries no core in 1444 so it only ever enters the game through decisions/FormCatholicGranada.txt, which grants the cores on 222, 223, 226 and 4546 just before releasing them",
        "culture": "the stub's castillian is only a placeholder: capital province 223 is andalucian in vanilla, and decisions/FormCatholicGranada.txt overwrites the crown's culture with the senior's own via change_primary_culture = ROOT (portuguese / catalan / castillian, depending on which of the four releases it), while accepting andalucian so the moriscos are assimilated rather than exiled, the same arrangement as CIL over Turkified provinces",
        "religion": "the crown is catholic by design and is not gated on the provinces converting: whichever Iberian power releases it supplies the Catholic faith for the junior crown, the same arrangement as KOJ and ATN (a Catholic crown over still-Muslim land)",
        "color": "deliberately identical to vanilla Granada's sage: CGR is dormant and holds no land in 1444, so this value is not on the map at all until decisions/FormCatholicGranada.txt releases it, and that decision recolours the new crown to its senior's colour in the same effect (change_country_color = { country = ROOT }, the eyalet mechanism vanilla uses for released eyalets). The shared value is a fallback for a country that does not yet exist, and is never seen in play",
        "not_releasable": "GRA holds 223 as its 1444 capital and the Nasrid kingdom keeps all three provinces, so CGR cannot exist at the start date; decisions/FormCatholicGranada.txt releases it as soon as Portugal, Aragon, Castile or Spain holds 222, 223, 226 and 4546 with cores",
    },
}

# Tags defined purely as formable titles (Form*.txt decisions grant their cores).
# They have no start-era home province, so the releasable wiring checks do not
# apply; the tag is still checked for definition, flag, localisation and ideas.
FORMABLE_TAGS: set[str] = {
    "ARS", "BRL", "GTY", "LUD", "LXM", "NVO", "OCC", "SXN",
}
EFFECT_RE = re.compile(r"^\s*[A-Za-z_][A-Za-z0-9_]*\s*=\s*-?[0-9.]+\s*$")
# modifier name followed by a value, tolerating a trailing `#` comment on the line.
# Group 1 = name, group 2 = value. The value must be a real decimal: a looser
# `-?[0-9.]+` also matches vanilla's `date = 1534.11.3` and `historical_start_date`
# keys, which are not modifiers. Compiled with MULTILINE up front because
# Pattern.finditer/findall take `pos` as their second argument, not flags.
MODIFIER_NAME_RE = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(-?[0-9]+(?:\.[0-9]+)?)\s*(?:#.*)?$",
    re.MULTILINE,
)
LOC_RE = re.compile(r'^\s*([A-Za-z0-9_.]+):\d+\s*"(.*)"\s*$')
DATE_RE = re.compile(r"^\d{3,4}\.\d+\.\d+")
_TRIPLET_RE = re.compile(r"^\s*([0-9]{1,3})\s+([0-9]{1,3})\s+([0-9]{1,3})\s*$")
_FLAG_COLOR_RE = re.compile(
    r"^[ \t]*flag_color\s*=\s*\{\s*(\d{1,3})\s+(\d{1,3})\s+(\d{1,3})\s*\}", re.M)


def read_text(path: Path) -> str:
    data = path.read_bytes()
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("latin-1")


def strip_comment(line: str) -> str:
    return line.split("#", 1)[0].rstrip()


def parse_tag_file(path: Path) -> dict[str, str]:
    """Return {TAG: relative countries ref}."""
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for raw in read_text(path).splitlines():
        m = TAG_LINE_RE.match(strip_comment(raw))
        if m:
            out[m.group(1)] = m.group(2)
    return out


def mod_tags_file(mod: Path) -> Path:
    """Return the country_tags registry file of a mod.

    Prefers the legacy zzz_hre_releasables.txt name, falls back to the
    live zzz_historical_european_tags.txt, then to the first zzz_*.txt.
    """
    base = mod / "common" / "country_tags"
    for name in ("zzz_hre_releasables.txt", "zzz_historical_european_tags.txt"):
        p = base / name
        if p.exists():
            return p
    files = sorted(base.glob("zzz_*.txt"))
    if files:
        return files[0]
    return base / "zzz_hre_releasables.txt"


def mod_ideas_file(mod: Path) -> Path:
    """Return the country-ideas file of a mod (legacy name first, live name fallback)."""
    base = mod / "common" / "ideas"
    for name in ("hre_releasables_country_ideas.txt",
                 "historical_european_tags_country_ideas.txt"):
        p = base / name
        if p.exists():
            return p
    files = sorted(base.glob("*.txt")) if base.is_dir() else []
    if files:
        return files[0]
    return base / "hre_releasables_country_ideas.txt"


def parse_kv_block(text: str) -> dict[str, str]:
    """Top-level `key = value` pairs (single-line values only)."""
    kv: dict[str, str] = {}
    depth = 0
    for raw in text.splitlines():
        line = strip_comment(raw)
        if not line.strip():
            continue
        if depth == 0:
            m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+?)\s*$", line)
            if m:
                kv[m.group(1)] = m.group(2).strip().strip('"')
        depth += line.count("{") - line.count("}")
    return kv


def extract_block(text: str, block_name: str) -> tuple[str | None, int]:
    """Extract `<block_name> = { ... }` with brace matching.

    Returns (body, start_line_index); body excludes the outer braces.
    """
    anchor = re.search(
        rf"^[ \t]*{re.escape(block_name)}\s*=\s*\{{", text, re.MULTILINE
    )
    if not anchor:
        return None, -1
    i = anchor.end()  # just past the opening brace
    depth = 1
    while i < len(text) and depth > 0:
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        i += 1
    return text[anchor.end(): i - 1], text[: anchor.start()].count("\n")


def sub_blocks(body: str) -> dict[str, str]:
    """Direct-child named sub-blocks inside a group body (depth-aware).

    Grandchildren (e.g. a `trigger` nested inside one idea, or `limit` inside
    an `if`) are consumed into their parent and never surface here.
    """
    out: dict[str, str] = {}
    lines = body.splitlines()
    i, n = 0, len(lines)
    while i < n:
        m = re.match(r"^[ \t]*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)$", lines[i])
        if m and "{" in m.group(2):
            name = m.group(1)
            rest = m.group(2)
            depth = rest.count("{") - rest.count("}")
            inner_parts = [rest.split("{", 1)[1]]
            j = i
            while depth > 0 and j + 1 < n:
                j += 1
                depth += lines[j].count("{") - lines[j].count("}")
                inner_parts.append(lines[j])
            inner = "\n".join(inner_parts)
            if "}" in inner:
                inner = inner[: inner.rindex("}")]
            out[name] = inner
            i = j + 1
        else:
            i += 1
    return out


def load_loc(mod: Path) -> dict[str, str]:
    loc: dict[str, str] = {}
    loc_dir = mod / "localisation"
    if not loc_dir.is_dir():
        return loc
    for yml in sorted(loc_dir.rglob("*.yml")):
        for raw in read_text(yml).splitlines():
            m = LOC_RE.match(raw.rstrip())
            if m:
                loc.setdefault(m.group(1), m.group(2))
    return loc


def load_game_loc(game: Path) -> dict[str, str]:
    """Game English localisation (province names PROV<id>, country names <TAG>)."""
    loc: dict[str, str] = {}
    loc_dir = game / "localisation"
    if not loc_dir.is_dir():
        return loc
    for yml in sorted(loc_dir.glob("*_l_english.yml")):
        for raw in read_text(yml).splitlines():
            m = LOC_RE.match(raw.rstrip())
            if m:
                loc.setdefault(m.group(1), m.group(2))
    return loc


def vanilla_idea_keys(game: Path) -> set[str]:
    src = game / "common" / "ideas" / "00_country_ideas.txt"
    if not src.exists():
        return set()
    text = read_text(src)
    keys: set[str] = set()
    for m in re.finditer(r"^([a-z][a-z0-9_]*)\s*=\s*\{", text, re.MULTILINE):
        if m.group(1) not in {"start", "bonus", "trigger", "free"}:
            keys.add(m.group(1))
    return keys


# Folders in which every `name = value` is a modifier on the country itself, so
# their names are exactly the names a national idea may use.
COUNTRY_MODIFIER_FOLDERS = (
    "ideas", "policies", "government_reforms", "religions", "ages",
    "static_modifiers", "event_modifiers", "triggered_modifiers",
    "institutions", "church_aspects", "ruler_personalities",
    "imperial_reforms", "state_edicts",
)
# Folders that reuse modifier-shaped names for a different purpose. `base_production`
# in a building, `monthly_income` in a hegemon demand and `trade_power` in a ship
# are all real keys, just not country modifiers. Harvesting these would make a dead
# idea look legal; harvesting nothing makes `trade_goods_size_modifier` (156 genuine
# country-scope uses) look broken. Both mistakes have already been made here once.
NON_COUNTRY_MODIFIER_FOLDERS = (
    "units", "tradegoods", "technologies", "buildings", "hegemons",
    "estate_agendas", "parliament_issues", "missions",
    "province_triggered_modifiers", "estates", "estate_privileges",
    "opinion_modifiers",
)
# Below this many vanilla samples, a modifier's value style is guesswork, so the
# value checks stay quiet rather than guess.
MIN_SAMPLES_FOR_VALUE_STYLE = 8


def _modifier_values_in(game: Path, folder: str) -> dict[str, list[float]]:
    out: dict[str, list[float]] = {}
    directory = game / "common" / folder
    if not directory.is_dir():
        return out
    for src in sorted(directory.rglob("*.txt")):
        for m in MODIFIER_NAME_RE.finditer(read_text(src)):
            out.setdefault(m.group(1), []).append(float(m.group(2)))
    return out


def country_modifier_profile(game: Path) -> tuple[dict[str, dict], dict[str, list[str]]]:
    """Profile every country modifier the base game actually uses.

    Returns (profile, non_country) where profile maps a legal modifier name to
    its observed value style (`flat` / `fraction` / `mixed`), sample count and
    value range, and non_country maps a rejected name to the folders it was seen
    in, so errors can say *why* a name is wrong instead of shrugging.
    """
    per_scope = {f: _modifier_values_in(game, f) for f in COUNTRY_MODIFIER_FOLDERS}
    other = {f: _modifier_values_in(game, f) for f in NON_COUNTRY_MODIFIER_FOLDERS}

    profile: dict[str, dict] = {}
    for scope, data in per_scope.items():
        for name, vals in data.items():
            entry = profile.setdefault(name, {"vals": [], "scopes": set()})
            entry["vals"].extend(vals)
            entry["scopes"].add(scope)

    for name, entry in profile.items():
        vals = entry.pop("vals")
        nonzero = [v for v in vals if v != 0]
        all_int = all(v.is_integer() for v in vals)
        all_frac = all(abs(v) < 1.0 for v in nonzero) if nonzero else True
        entry["style"] = "flat" if all_int else ("fraction" if all_frac else "mixed")
        entry["n"] = len(vals)
        entry["min"] = min(vals)
        entry["max"] = max(vals)
        entry["max_abs"] = max(abs(v) for v in vals)
        entry["scopes"] = sorted(entry["scopes"])

    non_country = {name: sorted(f for f, d in other.items() if name in d)
                   for name in {n for d in other.values() for n in d}}
    return profile, non_country


def _graded_count(rep, label: str, got: int, modal: int, seen: dict, noun: str) -> None:
    """A count checked against the base game rather than against a constant.

    A value vanilla itself ships is a warning, not a failure: the mod should
    not silently drift from the norm, but the norm is not a law. Anything
    vanilla never uses is a failure, because there is no precedent for it.
    """
    if got == modal:
        rep.ok(label, f"{got} (vanilla norm)")
    elif got in seen:
        rep.warn(label, f"{got}, vanilla norm is {modal} but {seen[got]} of {noun} use {got}")
    else:
        rep.fail(label, f"{got}, vanilla norm is {modal} and no vanilla {noun} use {got}")


def check_idea_shape(rep, tag: str, subs: dict, idea_names: list[str],
                     norms: dict) -> None:
    """Shape and internal balance of an idea group, measured against vanilla.

    The "2 traditions, 1 ambition, 7 ideas" rule is not a guess. idea_inventory
    measures every base-game country idea set: 416 of 446 use 2 traditions,
    432 use 1 ambition and 385 use 7 ideas. A count that vanilla also uses is
    therefore reported as a warning with the precedent, not a failure.

    On top of the counts this catches the failures that a count cannot:

      * an effect repeated across the traditions, the ambition or two ideas.
        The values add silently, so the player gets more than the file reads
        and the file no longer describes the country. Only 13 of 555 vanilla
        groups repeat an effect at all, and those are government and advisor
        sets, not national ones.
      * an idea the player can see that grants nothing.
      * an idea so heavy it stops being an idea. 78% of vanilla ideas carry a
        single modifier and 95% carry at most two.
    """
    n_start = len([l for l in subs.get("start", "").splitlines() if EFFECT_RE.match(l.strip())])
    n_bonus = len([l for l in subs.get("bonus", "").splitlines() if EFFECT_RE.match(l.strip())])
    n_ideas = len(idea_names)

    modal_start = norms.get("modal_start", 2)
    modal_bonus = norms.get("modal_bonus", 1)
    modal_ideas = norms.get("modal_idea_count", 7)
    _graded_count(rep, "traditions count", n_start, modal_start,
                  {int(k): c for k, c in (norms.get("start") or {}).items()}, "country idea sets")
    _graded_count(rep, "ambition count", n_bonus, modal_bonus,
                  {int(k): c for k, c in (norms.get("bonus") or {}).items()}, "country idea sets")
    _graded_count(rep, "idea count", n_ideas, modal_ideas,
                  {int(k): c for k, c in (norms.get("idea_count") or {}).items()}, "country idea sets")

    if not idea_names:
        return

    # an effect that appears more than once inside the same group
    where: dict[str, list[str]] = {}
    for owner, body in (("start", subs.get("start", "")),
                        ("bonus", subs.get("bonus", "")),
                        *[(k, subs[k]) for k in idea_names]):
        for m in MODIFIER_NAME_RE.finditer(body or ""):
            where.setdefault(m.group(1), []).append(owner)
    repeated = {k: v for k, v in where.items() if len(v) > 1}
    if repeated:
        rep.fail(
            "effect repeated in group",
            "; ".join(f"{k} in {', '.join(v)}" for k, v in sorted(repeated.items()))
            + " - the values add silently",
        )

    # an idea that grants nothing at all
    empty = [k for k in idea_names if not idea_inventory._content_lines(subs.get(k, ""))]
    if empty:
        rep.fail("idea grants no effect", ", ".join(empty))

    # an idea carrying more modifiers than the base game ever does
    cap = norms.get("idea_weight_cap", 2)
    heavy = {k: len(MODIFIER_NAME_RE.findall(subs[k])) for k in idea_names
             if len(MODIFIER_NAME_RE.findall(subs[k])) > cap}
    if heavy:
        rep.warn(
            "idea heavier than the vanilla norm",
            f"{', '.join(f'{k} ({n})' for k, n in sorted(heavy.items()))} - "
            f"95% of vanilla ideas carry at most {cap}",
        )


def vanilla_culture_names(game: Path) -> set[str]:
    """Every culture the base game defines.

    A culture is one tab deep inside a group block, so group-level keys
    (`graphical_culture`, `country`, `province`) are excluded. Names are
    matched exactly: `andalucian` is a real culture and `andalusian` is not,
    and the difference is invisible in game because the bad name is simply
    dropped on load.
    """
    names: set[str] = set()
    for f in sorted((game / "common" / "cultures").glob("*.txt")):
        text = f.read_bytes().decode("utf-8", errors="replace")
        for gm in re.finditer(r"^\t([a-z_0-9]+) = \{", text, re.MULTILINE):
            names.add(gm.group(1))
    return names


def vanilla_culture_keys(game: Path) -> set[str]:
    """Keys the engine reads inside a culture definition.

    Only these are meaningful there. `accepted_cultures` is NOT one of them:
    it is a country modifier that exists elsewhere in the base game, so
    putting it inside a culture block parses without complaint and does
    nothing at all.
    """
    keys: set[str] = set()
    for f in sorted((game / "common" / "cultures").glob("*.txt")):
        text = f.read_bytes().decode("utf-8", errors="replace")
        for gm in re.finditer(r"^\t([a-z_0-9]+) = \{", text, re.MULTILINE):
            i = gm.end()
            depth = 1
            for j in range(i, len(text)):
                if text[j] == "{":
                    depth += 1
                elif text[j] == "}":
                    depth -= 1
                    if depth == 0:
                        break
            keys.update(re.findall(r"^\t\t([a-z_0-9]+) =", text[i:j], re.MULTILINE))
    return keys


def mod_culture_problems(mod: Path, game: Path) -> list[tuple[str, str]]:
    """(culture, detail) rows for mod culture files that misuse the format."""
    legal = vanilla_culture_keys(game)
    rows: list[tuple[str, str]] = []
    for f in sorted((mod / "common" / "cultures").glob("*.txt")):
        text = f.read_bytes().decode("utf-8", errors="replace")
        for gm in re.finditer(r"^\t([a-z_0-9]+) = \{", text, re.MULTILINE):
            name = gm.group(1)
            i = gm.end()
            depth = 1
            for j in range(i, len(text)):
                if text[j] == "{":
                    depth += 1
                elif text[j] == "}":
                    depth -= 1
                    if depth == 0:
                        break
            used = re.findall(r"^\t\t([a-z_0-9]+) =", text[i:j], re.MULTILINE)
            bad = sorted({k for k in used if k not in legal})
            if bad:
                rows.append((
                    name,
                    f"{f.name}: {', '.join(bad)} - not a key the engine reads inside a "
                    f"culture (vanilla uses: {', '.join(sorted(legal))})",
                ))
    return rows


def check_culture_references(rep, mod: Path, game: Path, tags: dict, records: list[dict]) -> None:
    """Every culture the mod names must be a culture the game actually has.

    This is the check that was missing: an invented or misspelled culture name
    is not an error the game reports, it is a country that loads with no
    culture at all. `andalucian` is real, `andalusian` is not, and only
    checking against the real set tells the two apart.
    """
    known = vanilla_culture_names(game)
    # a mod may legitimately add cultures of its own
    for f in sorted((mod / "common" / "cultures").glob("*.txt")):
        text = f.read_bytes().decode("utf-8", errors="replace")
        known.update(re.findall(r"^\t([a-z_0-9]+) = \{", text, re.MULTILINE))

    bad_stub: list[str] = []
    for rec in records:
        pc = (rec.get("primary_culture") or "").strip()
        if pc and pc not in known:
            bad_stub.append(f"{rec['tag']}={pc}")
    rep.check(not bad_stub, "stub cultures exist", ", ".join(bad_stub) or
              f"all {len([r for r in records if (r.get('primary_culture') or '').strip()])} "
              f"stubs name a real culture ({len(known)} known)")

    # cultures named by decisions: change_primary_culture / add_accepted_culture
    #
    # The value is not always a literal culture name. `= ROOT` asks the engine
    # to COPY the calling country's culture in, which vanilla does for released
    # eyalets (01_scripted_effects_for_diplomacy.txt) and pirate republics
    # (events/FlavorPirates.txt). A scope is not a misspelling, so it has to be
    # recognised rather than skipped: the pattern here used to be lowercase-only,
    # which meant `change_primary_culture = ROOT` was never inspected at all and
    # this check passed on it by accident rather than by judgement. Every culture
    # and religion tag in vanilla is lowercase, so casing separates the two cases.
    # The `\{?` is load-bearing: the engine's canonical form is `= { KEY }` (braced),
    # and the pattern used to require the key to sit immediately after `=`, so every
    # braced usage - including the `andalusian`/`andalucian` typo this check exists to
    # catch - was silently skipped. Both `= KEY` and `= { KEY }` are matched now.
    bad_dec: list[str] = []
    scoped: list[str] = []
    for f in sorted((mod / "decisions").glob("*.txt")):
        text = read_text(f)
        for m in re.finditer(r"\b(change_primary_culture|add_accepted_culture)\s*=\s*\{?\s*([A-Za-z_0-9]+)", text):
            val = m.group(2)
            if not re.fullmatch(r"[a-z_0-9]+", val):
                if val in ("ROOT", "FROM", "ROOT.senior_partner"):
                    scoped.append(f"{f.name}:{m.group(1)}={val}")
                else:
                    ln = text[: m.start()].count("\n") + 1
                    bad_dec.append(f"{f.name}:{ln} {val} is neither a culture nor a scope")
            elif val not in known:
                ln = text[: m.start()].count("\n") + 1
                bad_dec.append(f"{f.name}:{ln} {val}")
    rep.check(not bad_dec, "decision cultures exist", ", ".join(bad_dec) or
              (f"all literal targets name a real culture; {len(scoped)} scoped copy: "
               + ", ".join(scoped) if scoped else "all literal targets name a real culture"))

    rows = mod_culture_problems(mod, game)
    rep.check(not rows, "culture files use only real keys",
              "; ".join(f"{n}: {d}" for n, d in rows))


def check_area_references(rep, mod: Path, game: Path) -> None:
    """Every area a decision acts on must be an area the base game defines.

    `<area> = { add_permanent_claim = TAG }` is a silent no-op if the area name
    is wrong: EU4 does not error on an unknown area, it just grants nothing, so
    a typo quietly strips the claim out of the decision and leaves the mod
    looking finished. This is the same failure mode as the `andalusian` culture
    typo, so it gets the same treatment.

    Province lists are irrelevant here; only the area NAME has to resolve.
    `add_permanent_claim` is also legal on a bare province scope - the mod's
    own RestoreJerusalem does `378 = { add_permanent_claim = KOJ }` - so only
    NAMED scopes are checked, identified by vanilla's `_area` suffix. A province
    id is numeric and is left alone. The cost of that rule is that an area
    misspelled badly enough to lose its `_area` suffix would slip through.
    """
    area_file = game / "map" / "area.txt"
    if not area_file.exists():
        rep.warn("vanilla areas readable", f"{area_file} not found")
        return
    known = set(re.findall(r"^([a-z_0-9]+)\s*=\s*\{", read_text(area_file), re.M))
    bad: list[str] = []
    seen: list[str] = []
    for f in sorted((mod / "decisions").glob("*.txt")):
        text = read_text(f)
        for m in re.finditer(
                r"^[ \t]*([a-z_0-9]+_area)\s*=\s*\{(?=[^}]*?add_permanent_claim)",
                text, re.M | re.S):
            name = m.group(1)
            ln = text[: m.start()].count("\n") + 1
            (seen if name in known else bad).append(f"{f.name}:{ln} {name}")
    rep.check(not bad, "decision areas exist", ", ".join(bad) or
              f"all {len(seen)} named area scopes are real vanilla areas ({len(known)} known)")


def check_idea_modifiers(rep, tag: str, subs: dict, idea_names: list[str],
                         profile: dict, non_country: dict) -> None:
    """Names must exist, and the value must be the kind vanilla uses for them.

    A name check alone passes `unrest = -0.10`: `unrest` is a real modifier, but
    vanilla only ever gives it whole numbers of unrest (and never a fraction
    anywhere), so that line is silently rounded away. The value style and range
    checks exist to catch exactly that class of no-op idea.
    """
    if not profile:
        return
    bad_names: list[str] = []
    bad_values: list[str] = []
    for owner, sub in (("start", subs.get("start", "")),
                       ("bonus", subs.get("bonus", "")),
                       *[(k, subs[k]) for k in idea_names]):
        for m in MODIFIER_NAME_RE.finditer(sub):
            name, value = m.group(1), float(m.group(2))
            entry = profile.get(name)
            if entry is None:
                hint = ""
                if f"global_{name}" in profile:
                    hint = f" (did you mean global_{name}?)"
                elif name in non_country:
                    hint = f" (only a {'/'.join(non_country[name])} key, not a country modifier)"
                bad_names.append(f"{owner}: {name}{hint}")
                continue
            if entry["n"] >= MIN_SAMPLES_FOR_VALUE_STYLE:
                if entry["style"] == "flat" and not value.is_integer():
                    bad_values.append(
                        f"{owner}: {name} = {value:g} (vanilla only uses whole numbers here, "
                        f"e.g. {entry['min']:g}..{entry['max']:g})")
                    continue
                if entry["style"] == "fraction" and abs(value) >= 1.0:
                    bad_values.append(
                        f"{owner}: {name} = {value:g} (vanilla always uses fractions below 1)")
                    continue
            if entry["max_abs"] and abs(value) > entry["max_abs"] * 1.5:
                bad_values.append(
                    f"{owner}: {name} = {value:g} (vanilla range {entry['min']:g}..{entry['max']:g})")
    rep.check(not bad_names, "idea modifiers valid", ", ".join(sorted(set(bad_names))))
    rep.check(not bad_values, "idea modifier values sane", ", ".join(sorted(set(bad_values))))


def parse_brace_color(text: str, key: str) -> tuple[int, int, int] | None:
    """Return the first `key = { R G B }` triplet found (brace-aware)."""
    body, _ln = extract_block(text, key)
    if body is None:
        return None
    for raw in body.splitlines():
        m = _TRIPLET_RE.match(raw)
        if m:
            return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def country_colors(root: Path) -> dict[str, tuple[tuple[int, int, int] | None, tuple[int, int, int] | None]]:
    """Map country-file stem -> (color, revolutionary_colors)."""
    out: dict[str, tuple[tuple[int, int, int] | None, tuple[int, int, int] | None]] = {}
    for f in sorted((root / "common" / "countries").glob("*.txt")):
        if f.name.startswith("zzz_"):  # registry files live elsewhere; be safe
            continue
        text = read_text(f)
        c = parse_brace_color(text, "color")
        r = parse_brace_color(text, "revolutionary_colors") or parse_brace_color(text, "revolutionary_color")
        out[f.stem] = (c, r)
    return out


def flag_palette(game: Path) -> list[tuple[int, int, int]]:
    """The vanilla `flag_color` list, in file order.

    A country file's `revolutionary_colors = { 15 0 16 }` does not hold three
    RGB channels: each number is a 0-based index into this list, i.e. one of
    the 17 heraldic inks defined in
    common/custom_country_colors/00_custom_country_colors.txt (Argent, Sable,
    Murrey, Azure, Gules, ...). So the palette, not the triplet, is the
    authoritative set of legal values.
    """
    path = game / "common" / "custom_country_colors" / "00_custom_country_colors.txt"
    if not path.exists():
        return []
    return [(int(a), int(b), int(c))
            for a, b, c in _FLAG_COLOR_RE.findall(read_text(path))]


def check_revolutionary_colors(rep, mod: Path, game: Path) -> None:
    """Every `revolutionary_colors` triple must be three palette indices.

    An index past the end of the vanilla `flag_color` list resolves to nothing,
    so the country silently falls back to a random revolutionary flag. That is
    the same silent no-op as a misspelled culture or a wrong area name, and it
    is easy to hit: the key reads like an RGB triple, so the natural thing to
    type is `{ 40 40 120 }`, which is not three inks but three out-of-range
    indices. Vanilla keeps all 798 of its own triples inside the palette, so
    any mod value above the last index is a bug rather than a style choice.
    """
    palette = flag_palette(game)
    if not palette:
        rep.warn("vanilla flag palette readable",
                 "00_custom_country_colors.txt not found or empty")
        return
    top = len(palette) - 1
    bad: list[str] = []
    seen = 0
    for f in sorted((mod / "common" / "countries").glob("*.txt")):
        if f.name.startswith("zzz_"):
            continue
        text = read_text(f)
        r = (parse_brace_color(text, "revolutionary_colors")
             or parse_brace_color(text, "revolutionary_color"))
        if r is None:
            continue
        seen += 1
        if any(v > top for v in r):
            bad.append(f"{f.stem}: {{{r[0]} {r[1]} {r[2]}}} (max {top})")
    rep.check(not bad, "revolutionary colours are palette indices",
              ", ".join(bad) or
              f"all {seen} triples index the {len(palette)}-ink flag_color palette (0..{top})")


def audit_colors(mod: Path, game: Path, tags: dict[str, str]) -> list[tuple[str, str, str]]:
    """Return (level, label, detail) rows for primary-colour conflicts.

    Only the primary `color` is audited here, because that is the only value
    that is an actual RGB triplet. `revolutionary_colors` is a triple of
    palette INDICES (see `check_revolutionary_colors`), so comparing it against
    an RGB `color` compares two unrelated domains, and holding it to the
    mod-wide uniqueness rule below is wrong on its face: the base game reuses
    index triples across many tags. Those values are validated as indices by
    their own check and deliberately take no part in these comparisons.

    Rules (see MOD_DESIGN.md / verifier colors section):
      * A mod tag's primary `color` must not equal any other mod tag's `color`
        (all N primaries unique across the mod).
      * A mod tag's `color` must not equal any base-game tag's `color`.
    """
    mod_map = country_colors(mod)
    game_map = country_colors(game)
    base_prim: dict[tuple[int, int, int], list[str]] = {}
    for stem, (c, _r) in game_map.items():
        if c:
            base_prim.setdefault(c, []).append(stem)

    mod_prim: list[tuple[tuple[int, int, int], str]] = []
    for tag in tags:
        # .stem, not .name: country_colors() keys its results by file stem
        # ("CatholicGranada"), while the tag registry stores a path
        # ("countries/CatholicGranada.txt"). Using .name here looked up
        # "CatholicGranada.txt", matched nothing on any of the 74 tags, and
        # left the primary list permanently empty - so this whole function had
        # been reporting "no color shared" without ever comparing a colour.
        c, _r = mod_map.get(Path(tags[tag]).stem, (None, None))
        if c:
            mod_prim.append((c, tag))

    rows: list[tuple[str, str, str]] = []
    by_value: dict[tuple[int, int, int], list[str]] = {}
    for v, t in mod_prim:
        by_value.setdefault(v, []).append(t)
    for v, lst in by_value.items():
        if len(lst) > 1:
            rows.append((
                "FAIL", "color shared between mod tags",
                f"{v} -> " + ", ".join(lst),
            ))
    for v, t in mod_prim:
        if v in base_prim:
            rows.append((
                "FAIL", "color collides with a base-game tag",
                f"{t} = {v} == base {base_prim[v][0]}",
            ))
    return rows


def province_header(path: Path) -> dict[str, object]:
    """Start-state keys plus every add_core with start-date awareness."""
    info: dict[str, object] = {"cores": [], "cores_at_start": [], "keys": {}}
    if not path.exists():
        return info
    keys: dict[str, str] = {}
    cores: list[str] = []
    at_start: list[str] = []
    current_date: str | None = None
    dated_depth = 0

    def date_le_start(date: str | None) -> bool:
        if not date:
            return False
        y, mo, d = (int(x) for x in date.split("."))
        return (y, mo, d) <= (1444, 11, 11)

    for raw in read_text(path).splitlines():
        stripped = strip_comment(raw).strip()
        dm = DATE_RE.match(stripped)
        if dm and dated_depth == 0:
            current_date = dm.group(0)
            dated_depth = stripped.count("{") - stripped.count("}")
            if dated_depth == 0 and "{" in stripped and "}" in stripped:
                inner = stripped[stripped.index("{") + 1: stripped.rindex("}")]
                for cm in re.finditer(r"add_core\s*=\s*([A-Z0-9]{3})", inner):
                    cores.append(cm.group(1))
                    if date_le_start(current_date):
                        at_start.append(cm.group(1))
                current_date = None
            continue
        if dated_depth > 0:
            dated_depth += stripped.count("{") - stripped.count("}")
            for cm in re.finditer(r"add_core\s*=\s*([A-Z0-9]{3})", stripped):
                cores.append(cm.group(1))
                if date_le_start(current_date):
                    at_start.append(cm.group(1))
            if dated_depth == 0:
                current_date = None
            continue
        km = re.match(
            r"^(owner|controller|culture|religion|hre|capital)\s*=\s*(.+?)\s*$", stripped
        )
        if km:
            keys[km.group(1)] = (
                km.group(2).strip().strip('"').split("#", 1)[0].strip()
            )
            continue
        cm = re.match(r"^add_core\s*=\s*([A-Z0-9]{3})", stripped)
        if cm:
            cores.append(cm.group(1))
            at_start.append(cm.group(1))

    info["cores"] = cores
    info["cores_at_start"] = at_start
    info["keys"] = keys
    return info


def hre_releasable_gaps(
    game: Path, mod_capitals: set[int], game_loc: dict[str, str]
) -> list[tuple[int, str, str]]:
    """Non-capital HRE provinces with no releasable tag: (id, name, owner).

    A province counts as covered when any tag - vanilla or mod - has it as
    its capital. Start-state capital/owner keys come from the game files;
    a dated capital move (e.g. 1633.1.1 = { capital = ... }) must not count,
    so only the first capital line of each country history file is read.
    """
    capitals = set(mod_capitals)
    for cf in (game / "history" / "countries").glob("*.txt"):
        for raw in read_text(cf).splitlines():
            m = re.match(r"^\s*capital\s*=\s*(\d+)", strip_comment(raw).strip())
            if m:
                capitals.add(int(m.group(1)))
                break
    gaps: list[tuple[int, str, str]] = []
    for pf in (game / "history" / "provinces").glob("*.txt"):
        text = read_text(pf)
        if not re.search(r"^\s*hre\s*=\s*yes\s*(?:#.*)?$", text, re.MULTILINE):
            continue
        keys = province_header(pf)["keys"]  # type: ignore[union-attr]
        owner = keys.get("owner", "0")
        if not re.fullmatch(r"[A-Z0-9]{3}", owner):
            continue
        pid = int(re.match(r"^(\d+)", pf.name).group(1))
        if pid not in capitals:
            gaps.append((pid, game_loc.get(f"PROV{pid}", ""), owner))
    return sorted(gaps)


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE meta (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE tags (
            tag                     TEXT PRIMARY KEY,
            country_ref             TEXT,
            name                    TEXT,
            adj                     TEXT,
            color                   TEXT,
            graphical_culture       TEXT,
            flag_status             TEXT,
            stub_file               TEXT,
            province_file           TEXT,
            government              TEXT,
            government_rank         TEXT,
            primary_culture         TEXT,
            religion                TEXT,
            technology_group        TEXT,
            capital                 INTEGER,
            fixed_capital           INTEGER,
            capital_name            TEXT,
            owner                   TEXT,
            owner_capital           INTEGER,
            owner_name              TEXT,
            province_culture        TEXT,
            province_religion       TEXT,
            province_hre            INTEGER,
            cores                   TEXT,
            cores_at_start          TEXT,
            releasable_at_start     INTEGER,
            owns_provinces_at_start INTEGER,
            ideas_block             INTEGER,
            traditions              INTEGER,
            ambition                INTEGER,
            idea_count              INTEGER,
            idea_names              TEXT,
            ideas_trigger_lock      INTEGER,
            ideas_free              INTEGER,
            n_fail                  INTEGER,
            n_warn                  INTEGER
        );
        CREATE TABLE checks (
            tag        TEXT NOT NULL,
            check_name TEXT NOT NULL,
            status     TEXT NOT NULL,
            detail     TEXT
        );
        CREATE INDEX checks_tag ON checks (tag);
        CREATE TABLE ideas (
            tag     TEXT NOT NULL,
            key     TEXT NOT NULL,
            kind    TEXT NOT NULL,
            loc     TEXT,
            desc    TEXT,
            effects TEXT,
            PRIMARY KEY (tag, key)
        );
        CREATE TABLE orphans (
            kind   TEXT NOT NULL,
            value  TEXT NOT NULL,
            detail TEXT
        );
        """
    )


EFFECT_PAIR_RE = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([-+]?[0-9.]+)\s*$", re.MULTILINE
)


def effect_pairs(text: str) -> dict[str, str]:
    """Top-level `key = number` modifiers in an idea/tradition/ambition body."""
    return {m.group(1): m.group(2) for m in EFFECT_PAIR_RE.finditer(text)}


def fill_ideas(
    conn: sqlite3.Connection,
    tag: str,
    subs: dict[str, str],
    idea_names: list[str],
    loc: dict[str, str],
) -> None:
    rows = []
    for kind, key, block in (
        ("tradition", f"{tag}_ideas_start", subs.get("start", "")),
        ("ambition", f"{tag}_ideas_bonus", subs.get("bonus", "")),
    ):
        rows.append((tag, key, kind, loc.get(key, ""), "", json.dumps(effect_pairs(block))))
    for k in idea_names:
        rows.append(
            (
                tag, k, "idea", loc.get(k, ""), loc.get(f"{k}_desc", ""),
                json.dumps(effect_pairs(subs.get(k, ""))),
            )
        )
    conn.executemany(
        "INSERT OR REPLACE INTO ideas (tag, key, kind, loc, desc, effects) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )


def decode_text(data: bytes) -> tuple[str, str]:
    """Decode mod text bytes. Returns (text, codec) that round-trips the BOM."""
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig"), "utf-8-sig"
    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return data.decode("latin-1"), "latin-1"


def write_text(path: Path, text: str, codec: str) -> None:
    path.write_bytes(text.encode(codec))


def drop_lines(text: str, keep) -> tuple[str, list[int]]:
    """Return (text, [1-based line numbers]) with lines keep() rejects removed."""
    out: list[str] = []
    dropped: list[int] = []
    for i, raw in enumerate(text.splitlines(keepends=True), start=1):
        if keep(raw):
            out.append(raw)
        else:
            dropped.append(i)
    return "".join(out), dropped


def rm_tag_lines(text: str, tag: str) -> tuple[str, list[int], str]:
    """Remove `TAG = "countries/ref"` lines. Returns (text, [lines], ref)."""
    ref = ""

    def keep(line: str) -> bool:
        nonlocal ref
        m = TAG_LINE_RE.match(strip_comment(line))
        if m and m.group(1) == tag:
            ref = m.group(2)
            return False
        return True

    new_text, nums = drop_lines(text, keep)
    return new_text, nums, ref


def rm_loc_keys(text: str, keys: set[str]) -> tuple[str, list[int]]:
    """Remove localisation lines whose key (or its _desc twin) is in keys."""
    alt = "|".join(sorted((re.escape(k) for k in keys), key=len, reverse=True))
    pat = re.compile(rf'^\s*(?:{alt})(?:_desc)?:\d+\s*"')
    return drop_lines(text, lambda line: not pat.match(line))


def rm_ideas_block(text: str, tag: str) -> tuple[str, list[int], list[str]]:
    """Remove `<TAG>_ideas = { ... }` together with its header comment.

    Returns (new_text, [1-based removed line numbers], [idea keys found]).
    """
    block = f"{tag}_ideas"
    m = re.search(rf"^[ \t]*{re.escape(block)}\s*=\s*\{{", text, re.MULTILINE)
    if not m:
        return text, [], []
    i = m.end()
    depth = 1
    while i < len(text) and depth > 0:
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
        i += 1
    body = text[m.end(): i - 1]
    subs = sub_blocks(body)
    idea_keys = [
        k for k in subs if k not in {"start", "bonus", "trigger", "if", "else", "limit"}
    ]
    start = m.start()
    while start > 0:
        nl = text.rfind("\n", 0, start)
        if nl == -1:
            start = 0
            break
        prev = text[nl + 1:start]
        if prev.strip() == "" or prev.lstrip().startswith("#"):
            # Step left one newline. A blank line is two adjacent \n's, so
            # prev is '' and nl == start - 1: start = nl guarantees progress.
            start = nl
        else:
            break
    first = text[:start].count("\n") + 1
    last = text[:i].count("\n") + 1
    return text[:start] + text[i:], list(range(first, last + 1)), idea_keys


def rm_province_cores(st: "ModState", game: Path, tag: str):
    """Strip `add_core = TAG` from mod province overrides.

    A file that equals its vanilla twin after stripping is deleted, otherwise
    it is rewritten. Yields (path, action, [lines], new_text, codec).
    """
    pat = re.compile(
        rf"^\s*add_core\s*=\s*{re.escape(tag)}\s*(?:#.*)?$",
        re.MULTILINE | re.IGNORECASE,
    )
    for pf in sorted((st.mod / "history" / "provinces").glob("*.txt")):
        text, codec = st.read(pf)
        new_text, nums = drop_lines(text, lambda line: not pat.match(line))
        if not nums:
            continue
        vanilla = game / "history" / "provinces" / pf.name
        if vanilla.is_file() and decode_text(vanilla.read_bytes())[0] == new_text:
            yield pf, "delete", nums, new_text, codec
        else:
            yield pf, "rewrite", nums, new_text, codec


class ModState:
    """In-memory view of mod files; dry-run and real removal share one path."""

    def __init__(self, mod: Path, dry: bool = False) -> None:
        self.mod = Path(mod)
        self.dry = dry
        self._texts: dict[Path, tuple[str, str]] = {}
        self._deleted: set[Path] = set()

    def read(self, path: Path) -> tuple[str, str]:
        key = path.resolve()
        if key in self._deleted:
            raise FileNotFoundError(path)
        if key not in self._texts:
            self._texts[key] = decode_text(path.read_bytes())
        return self._texts[key]

    def write(self, path: Path, text: str, codec: str | None = None) -> None:
        key = path.resolve()
        if key not in self._texts:
            self._texts[key] = (text, codec or "utf-8")
        else:
            self._texts[key] = (text, codec or self._texts[key][1])
        if not self.dry:
            path.write_bytes(text.encode(self._texts[key][1]))

    def delete(self, path: Path) -> None:
        key = path.resolve()
        self._deleted.add(key)
        if not self.dry:
            path.unlink(missing_ok=True)


def residual_scan(
    st: "ModState", tag: str, suffixes=frozenset({".txt", ".yml", ".json", ".mod"})
) -> list[tuple[str, list[int]]]:
    """Find remaining `TAG` references in mod text files (tools/ excluded)."""
    pat = re.compile(rf"\b{re.escape(tag)}\b")
    hits: list[tuple[str, list[int]]] = []
    for f in sorted(st.mod.rglob("*")):
        if not f.is_file() or f.suffix.lower() not in suffixes:
            continue
        rel = f.relative_to(st.mod)
        if any(part in {"tools", "__pycache__", ".git"} for part in rel.parts):
            continue
        if f.resolve() in st._deleted:
            continue
        text, _codec = st.read(f)
        nums = [i for i, line in enumerate(text.splitlines(), start=1) if pat.search(line)]
        if nums:
            hits.append((str(rel), nums))
    return hits


def _remove_tag(st: "ModState", game: Path, tag: str) -> list[str]:
    plan: list[str] = []
    verb_del, verb_rm, verb_rew = (
        ("would delete", "would remove", "would rewrite")
        if st.dry
        else ("deleted", "removed", "rewrote")
    )

    # --- country_tags definition ---
    ct = mod_tags_file(st.mod)
    text, codec = st.read(ct)
    new_ct, nums, ref = rm_tag_lines(text, tag)
    if not nums:
        plan.append(f"ERROR: {tag} not found in {ct.name}")
        return plan
    plan.append(f"{verb_rm} line {nums[0]} from {ct.relative_to(st.mod)} ({tag} = \"{ref}\")")
    st.write(ct, new_ct, codec)

    # --- countries definition ---
    if ref:
        def_path = st.mod / "common" / "countries" / Path(ref).name
        if def_path.is_file():
            plan.append(f"{verb_del} {def_path.relative_to(st.mod)}")
            st.delete(def_path)
        else:
            plan.append(f"note: {def_path.name} not found (already missing)")

    # --- history stub ---
    for s in sorted((st.mod / "history" / "countries").glob(f"{tag} -*.txt")):
        plan.append(f"{verb_del} {s.relative_to(st.mod)}")
        st.delete(s)

    # --- province overrides (add_core) ---
    for pf, action, nums, pnew, pcodec in rm_province_cores(st, game, tag):
        if action == "delete":
            plan.append(
                f"{verb_del} {pf.relative_to(st.mod)} "
                f"(add_core = {tag} line {nums[0]}; equals vanilla after strip)"
            )
            st.delete(pf)
        else:
            plan.append(
                f"{verb_rm} add_core = {tag} (line {nums[0]}) from "
                f"{pf.relative_to(st.mod)}"
            )
            st.write(pf, pnew, pcodec)

    # --- ideas block ---
    ideas = mod_ideas_file(st.mod)
    itext, icodec = st.read(ideas)
    inew, inums, idea_keys = rm_ideas_block(itext, tag)
    if inums:
        span = f"lines {inums[0]}-{inums[-1]}" if len(inums) > 1 else f"line {inums[0]}"
        plan.append(f"{verb_rew} {ideas.relative_to(st.mod)}: {tag}_ideas block ({span})")
        st.write(ideas, inew, icodec)
    else:
        plan.append(f"note: {tag}_ideas block not found in {ideas.name}")

    # --- localisation ---
    loc_keys = {tag, f"{tag}_ADJ", f"{tag}_ideas", f"{tag}_ideas_start", f"{tag}_ideas_bonus"}
    loc_keys.update(idea_keys)
    for yml in sorted((st.mod / "localisation").glob("*.yml")):
        ytext, ycodec = st.read(yml)
        ynew, ynums = rm_loc_keys(ytext, loc_keys)
        if ynums:
            span = ", ".join(str(n) for n in ynums)
            plan.append(
                f"{verb_rew} {yml.relative_to(st.mod)}: {len(ynums)} key line(s) ({span})"
            )
            st.write(yml, ynew, ycodec)

    # --- flag (never removed) ---
    flag = st.mod / "gfx" / "flags" / f"{tag}.tga"
    if flag.is_file():
        plan.append(f"keep {flag.relative_to(st.mod)} (flags are never removed)")
    else:
        plan.append(f"note: no flag file gfx/flags/{tag}.tga")

    # --- residual references ---
    for rel, rnums in residual_scan(st, tag):
        span = ", ".join(str(n) for n in rnums)
        plan.append(f"RESIDUAL {rel}: {tag} on line(s) {span}")
    return plan


class Report:
    _COUNTERS = {"FAIL": "fails", "WARN": "warns"}

    def __init__(self, conn: sqlite3.Connection | None = None) -> None:
        self.fails = 0
        self.warns = 0
        self.conn = conn
        self.tag: str | None = None

    def _row(self, label: str, status: str, detail: str) -> None:
        if self.conn is None or self.tag is None:
            return
        self.conn.execute(
            "INSERT INTO checks (tag, check_name, status, detail) VALUES (?, ?, ?, ?)",
            (self.tag, label, status, detail),
        )

    def log(self, level: str, label: str, detail: str = "") -> None:
        """Record one check result at the given level."""
        counter = self._COUNTERS.get(level)
        if counter:
            setattr(self, counter, getattr(self, counter) + 1)
        print(f"    {level:<5}{label}{(' - ' + detail) if detail else ''}")
        self._row(label, level, detail)

    def ok(self, label: str, detail: str = "") -> None:
        self.log("OK", label, detail)

    def warn(self, label: str, detail: str = "") -> None:
        self.log("WARN", label, detail)

    def info(self, label: str, detail: str = "") -> None:
        self.log("INFO", label, detail)

    def fail(self, label: str, detail: str = "") -> None:
        self.log("FAIL", label, detail)

    def check(self, cond: bool, label: str, detail: str = "") -> None:
        """Emit OK when cond is true, FAIL otherwise."""
        self.log("OK" if cond else "FAIL", label, detail)

    def exempt_or_fail(self, label: str, exc: str | None, what: str = "", fail_detail: str | None = None) -> bool:
        """Emit INFO when a KNOWN_EXCEPTIONS reason applies, FAIL otherwise.

        what prefixes the INFO detail when set. fail_detail overrides the
        FAIL detail (defaults to what). Returns True when exempt.
        """
        if exc:
            detail = f"{what} exempt ({exc})" if what else f"exempt ({exc})"
            self.log("INFO", label, detail)
            return True
        self.log("FAIL", label, fail_detail if fail_detail is not None else what)
        return False


def verify_tag(tag: str, rep: Report, ctx: dict) -> dict:
    mod: Path = ctx["mod"]
    game: Path = ctx["game"]
    loc: dict[str, str] = ctx["loc"]

    print(f"  {tag} ({ctx['tags'][tag]})")

    rec: dict = {
        "tag": tag,
        "country_ref": ctx["tags"][tag],
        "name": loc.get(tag, ""),
        "adj": loc.get(tag + "_ADJ", ""),
        "stub_file": "",
        "province_file": "",
    }

    # --- countries definition -------------------------------------------------
    ref = ctx["tags"][tag]
    def_path = mod / "common" / "countries" / Path(ref).name
    if not def_path.exists():
        rep.fail("countries definition", f"{def_path} missing")
        color_ok = graphical_ok = False
        defkv: dict[str, str] = {}
    else:
        defkv = parse_kv_block(read_text(def_path))
        color_ok = bool(re.match(r"^\{\s*\d{1,3}\s+\d{1,3}\s+\d{1,3}\s*\}$", defkv.get("color", "")))
        graphical_ok = "graphical_culture" in defkv
        rep.check(color_ok, "color", defkv.get("color", "<none>"))
        rep.check(graphical_ok, "graphical_culture", defkv.get("graphical_culture", "<none>"))
    rec["color"] = defkv.get("color", "")
    rec["graphical_culture"] = defkv.get("graphical_culture", "")

    # --- flag -----------------------------------------------------------------
    flag = mod / "gfx" / "flags" / f"{tag}.tga"
    if flag.exists():
        rep.ok("flag")
        rec["flag_status"] = "present"
    else:
        rep.warn("flag missing", "(deferred by design)" )
        rec["flag_status"] = "missing"

    # --- formable-only tags ----------------------------------------------------
    # Titles formed via Form*.txt decisions; cores come from the decision, not
    # from a 1444 home province. No releasable wiring checks apply.
    if tag in FORMABLE_TAGS:
        rep.info("formable-only", "no releasable wiring (Form*.txt decision grants cores)")
        return rec

    # --- history stub ---------------------------------------------------------
    stubs = sorted((mod / "history" / "countries").glob(f"{tag} -*.txt"))
    if len(stubs) != 1:
        rep.fail("history stub", f"expected exactly 1, found {len(stubs)}")
        return rec
    stub = stubs[0]
    rec["stub_file"] = stub.name
    kv = parse_kv_block(read_text(stub))
    required = ["government", "government_rank", "primary_culture",
                "religion", "technology_group", "capital", "fixed_capital"]
    missing = [k for k in required if k not in kv]
    if missing:
        rep.fail("stub keys missing", ", ".join(missing))
    else:
        rep.ok("stub keys")
    if kv.get("capital") and kv.get("fixed_capital"):
        if kv["capital"].split()[0] == kv["fixed_capital"]:
            rep.ok("fixed_capital == capital")
        else:
            rep.fail("fixed_capital mismatch",
                     f"{kv['fixed_capital']} != {kv['capital']}")

    rec["government"] = kv.get("government", "")
    rec["government_rank"] = kv.get("government_rank", "")
    rec["primary_culture"] = kv.get("primary_culture", "")
    rec["religion"] = kv.get("religion", "")
    rec["technology_group"] = kv.get("technology_group", "")

    cap_id = kv.get("capital", "").split()[0] if kv.get("capital") else ""
    if not cap_id.isdigit():
        rep.fail("capital not numeric", repr(kv.get("capital")))
        return rec
    rec["capital"] = int(cap_id)
    fix = kv.get("fixed_capital", "").split()[0] if kv.get("fixed_capital") else ""
    rec["fixed_capital"] = int(fix) if fix.isdigit() else None
    rec["capital_name"] = ctx["game_loc"].get(f"PROV{cap_id}", "")

    # --- capital province -----------------------------------------------------
    prov_dir = mod / "history" / "provinces"
    prov_files = sorted(
        set(prov_dir.glob(f"{cap_id} - *.txt")) | set(prov_dir.glob(f"{cap_id}-*.txt"))
    )
    if len(prov_files) != 1:
        rep.exempt_or_fail(
            "province file in mod",
            KNOWN_EXCEPTIONS.get(tag, {}).get("province_file"),
            f"{cap_id}: found {len(prov_files)}",
        )
        return rec
    prov = province_header(prov_files[0])
    rec["province_file"] = prov_files[0].name
    pkeys: dict[str, str] = prov["keys"]  # type: ignore[assignment]
    cores: list[str] = prov["cores"]  # type: ignore[assignment]
    at_start: list[str] = prov["cores_at_start"]  # type: ignore[assignment]

    rec["owner"] = pkeys.get("owner", "")
    rec["owner_name"] = ctx["game_loc"].get(pkeys.get("owner", ""), "")
    rec["province_culture"] = pkeys.get("culture", "")
    rec["province_religion"] = pkeys.get("religion", "")
    rec["province_hre"] = 1 if pkeys.get("hre") == "yes" else 0
    rec["cores"] = json.dumps(cores)
    rec["cores_at_start"] = json.dumps(at_start)

    if tag in at_start:
        rep.ok("add_core in province")
    elif tag in cores:
        rep.exempt_or_fail(
            "core only added after 1444 start",
            KNOWN_EXCEPTIONS.get(tag, {}).get("add_core"),
            fail_detail=prov_files[0].name,
        )
    else:
        rep.exempt_or_fail(
            "add_core missing in province",
            KNOWN_EXCEPTIONS.get(tag, {}).get("add_core"),
            fail_detail=prov_files[0].name,
        )

    owner = pkeys.get("owner", "")
    if owner == tag:
        rep.exempt_or_fail(
            "owns own capital at start",
            KNOWN_EXCEPTIONS.get(tag, {}).get("landed_vassal"),
        )
    else:
        rep.ok("does not own province", f"held by {owner or '?'}")

    pcult = pkeys.get("culture", "")
    if pcult and pcult == kv.get("primary_culture"):
        rep.ok("primary_culture matches province", pcult)
    else:
        rep.exempt_or_fail(
            "culture mismatch",
            KNOWN_EXCEPTIONS.get(tag, {}).get("culture"),
            fail_detail=f"stub={kv.get('primary_culture')} province={pcult}",
        )

    if pkeys.get("hre") == "yes":
        rep.ok("province in HRE")
    else:
        rep.warn("province not marked hre = yes")

    prel = pkeys.get("religion", "")
    srel = kv.get("religion", "")
    if prel and srel and prel != srel:
        rep.exempt_or_fail(
            "religion mismatch",
            KNOWN_EXCEPTIONS.get(tag, {}).get("religion"),
            fail_detail=f"stub={srel} province={prel}",
        )
    else:
        rep.ok("religion consistent", srel)

    # --- release viability (1444 capital constraint) ----------------------------
    # Design rule: a releasable tag capital must NOT be the capital of any
    # country that exists on 1444.11.11. See MOD_DESIGN.md.
    if not owner:
        rec["releasable_at_start"] = 1
        rep.ok("releasable at start", f"province {cap_id} has no 1444 owner (unowned)")
    else:
        owner_caps = list((game / "history" / "countries").glob(f"{owner} -*.txt"))
        if len(owner_caps) == 1:
            ocap = parse_kv_block(read_text(owner_caps[0])).get("capital", "").split()[0]
            rec["owner_capital"] = int(ocap) if ocap.isdigit() else None
            if ocap == cap_id:
                rec["releasable_at_start"] = 0
                rep.exempt_or_fail(
                    "NOT releasable at start",
                    KNOWN_EXCEPTIONS.get(tag, {}).get("not_releasable"),
                    fail_detail=(
                        f"{owner} holds {cap_id} as its 1444 capital "
                        "(violates design rule)"
                    ),
                )
            else:
                rec["releasable_at_start"] = 1
                rep.ok("releasable at start", f"{owner} capital is {ocap}, not {cap_id}")
        else:
            rec["releasable_at_start"] = None
            rep.warn("owner history file ambiguous", f"{owner}: {len(owner_caps)}")

    owns_any = False
    for pf in (mod / "history" / "provinces").glob("*.txt"):
        if province_header(pf)["keys"].get("owner") == tag:  # type: ignore[union-attr]
            owns_any = True
            break
    if owns_any:
        rep.exempt_or_fail(
            "owns provinces at start",
            KNOWN_EXCEPTIONS.get(tag, {}).get("landed_vassal"),
        )
    rec["owns_provinces_at_start"] = 1 if owns_any else 0

    # --- localisation ----------------------------------------------------------
    rep.check(tag in loc, "loc name", f'{tag}: "{loc.get(tag, "?")}"')
    rep.check(f"{tag}_ADJ" in loc, "loc adjective", f'{tag}_ADJ: "{loc.get(tag + "_ADJ", "?")}"')

    # --- ideas ------------------------------------------------------------------
    ideas_path = mod_ideas_file(mod)
    body, _ln = extract_block(read_text(ideas_path), f"{tag}_ideas")
    if body is None:
        rep.exempt_or_fail("ideas block missing", KNOWN_EXCEPTIONS.get(tag, {}).get("ideas"), f"{tag}_ideas")
        rec["ideas_block"] = 0
    else:
        rep.ok("ideas block present")
        rec["ideas_block"] = 1
        subs = sub_blocks(body)
        n_start = len([l for l in (subs.get("start", "").splitlines()) if EFFECT_RE.match(l.strip())])
        n_bonus = len([l for l in (subs.get("bonus", "").splitlines()) if EFFECT_RE.match(l.strip())])
        idea_names = [
            k for k in subs
            if k not in {"start", "bonus", "trigger", "if", "else", "limit"}
        ]
        rec["traditions"] = n_start
        rec["ambition"] = n_bonus
        rec["idea_count"] = len(idea_names)
        rec["idea_names"] = json.dumps(idea_names)
        check_idea_shape(rep, tag, subs, idea_names, ctx.get("idea_norms") or {})
        # every modifier the block applies must be one the game recognises and
        # must carry a value of the kind vanilla uses, or the game drops it
        check_idea_modifiers(rep, tag, subs, idea_names,
                             ctx.get("country_modifier_profile") or {},
                             ctx.get("non_country_modifier_scopes") or {})
        trig = subs.get("trigger", "")
        trig_ok = bool(re.search(rf"tag\s*=\s*{tag}\b", trig))
        free_ok = bool(re.search(r"^\s*free\s*=\s*yes\s*$", body, re.MULTILINE))
        rec["ideas_trigger_lock"] = 1 if trig_ok else 0
        rec["ideas_free"] = 1 if free_ok else 0
        rep.check(trig_ok, "trigger tag lock")
        rep.check(free_ok, "free = yes")
        if ctx["conn"] is not None:
            fill_ideas(ctx["conn"], tag, subs, idea_names, loc)
        for k in [f"{tag}_ideas", f"{tag}_ideas_start", f"{tag}_ideas_bonus", *idea_names]:
            if k not in loc:
                rep.fail("idea loc missing", k)
            elif k in idea_names and f"{k}_desc" not in loc:
                rep.fail("idea desc missing", f"{k}_desc")
        if idea_names:
            dupes = [k for k in idea_names if k in ctx["vanilla_keys"]]
            if dupes:
                rep.fail("idea key collides with vanilla", ", ".join(dupes))
            mod_dups = [k for k in idea_names if k in ctx["seen_idea_keys"]]
            if mod_dups:
                rep.fail("idea key duplicated in mod", ", ".join(mod_dups))
            ctx["seen_idea_keys"].update(idea_names)

    return rec


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--game", type=Path, default=DEFAULT_GAME)
    ap.add_argument("--mod", type=Path, default=DEFAULT_MOD)
    ap.add_argument(
        "--db", type=Path, default=None,
        help="SQLite output path (default: hre_releasables.sqlite3 next to this script)",
    )
    ap.add_argument("-q", "--quiet", action="store_true", help="only failures/warnings")
    ap.add_argument(
        "command", nargs="?", choices=["remove"], default=None,
        help="subcommand: 'remove' deletes tags from the mod (default: verify)",
    )
    ap.add_argument(
        "tags", nargs="*", metavar="TAG",
        help="tags to remove (only with 'remove')",
    )
    ap.add_argument(
        "--dry-run", action="store_true",
        help="with 'remove': show exactly what would be removed, change nothing",
    )
    return ap


def verify_main(args: argparse.Namespace) -> int:
    mod, game = args.mod, args.game
    tags = parse_tag_file(mod_tags_file(mod))
    base_tags: set[str] = set()
    for f in (game / "common/country_tags").glob("*.txt"):
        base_tags |= set(parse_tag_file(f))

    db_path = args.db or Path(__file__).with_name("hre_releasables.sqlite3")
    db_path.unlink(missing_ok=True)
    conn = sqlite3.connect(db_path)
    init_db(conn)

    seen_idea_keys: set[str] = set()
    _mod_profile, _non_country = country_modifier_profile(game)
    print(f"Country modifier profile: {len(_mod_profile)} legal names mined from "
          f"{len(COUNTRY_MODIFIER_FOLDERS)} vanilla folders")
    _norms = idea_inventory.summarise(idea_inventory.parse_groups(game))
    print(f"Vanilla idea inventory: {_norms['country_count']} country idea sets -> "
          f"norm {_norms['modal_start']} traditions, {_norms['modal_bonus']} ambition, "
          f"{_norms['modal_idea_count']} ideas, 1-{_norms['idea_weight_cap']} modifiers per idea")
    ctx = {
        "mod": mod,
        "game": game,
        "tags": tags,
        "loc": load_loc(mod),
        "game_loc": load_game_loc(game),
        "vanilla_keys": vanilla_idea_keys(game),
        "country_modifier_profile": _mod_profile,
        "non_country_modifier_scopes": _non_country,
        "idea_norms": _norms,
        "seen_idea_keys": seen_idea_keys,
        "conn": conn,
    }

    rep = Report(conn)
    print(f"HRE Releasables verification - {len(tags)} tags\n")

    records: list[dict] = []
    for tag in sorted(tags):
        rep.tag = tag
        records.append(verify_tag(tag, rep, ctx))
    rep.tag = None

    # --- orphans -----------------------------------------------------------------
    stub_orphans = []
    for f in (mod / "history/countries").glob("*.txt"):
        t = f.name.split(" ")[0]
        # Skip base-game-tag override files (e.g. the LIV bishopric patch):
        # they replace the vanilla history stub, they are not mod tags.
        if t not in tags and t not in base_tags and re.fullmatch(r"[A-Z0-9]{3}", t):
            stub_orphans.append(f.name)
    core_orphans: dict[str, list[str]] = {}
    for pf in (mod / "history/provinces").glob("*.txt"):
        for c in province_header(pf)["cores"]:  # type: ignore[union-attr]
            if c not in tags and c not in base_tags:
                core_orphans.setdefault(c, []).append(pf.name)
    collisions = sorted(set(tags) & base_tags)

    print("\n== Global ==")
    if stub_orphans:
        rep.fail("stubs without tag definition", ", ".join(stub_orphans))
    else:
        rep.ok("no orphaned history stubs")
    if core_orphans:
        rep.fail("cores without tag definition", str(core_orphans))
    else:
        rep.ok("no orphaned add_core entries")
    if collisions:
        rep.fail("tag collides with base game", ", ".join(collisions))
    else:
        rep.ok("no base-game tag collisions")

    # duplicate localisation keys: identical text is harmless clutter, differing
    # text means one definition silently wins and an idea shows the wrong text
    loc_dupes: list[str] = []
    loc_conflicts: list[str] = []
    for yml in sorted((mod / "localisation").glob("*.yml")):
        seen: dict[str, tuple[int, str]] = {}
        for ln, raw in enumerate(read_text(yml).splitlines(), 1):
            m = LOC_RE.match(raw.rstrip())
            if not m:
                continue
            key, val = m.group(1), m.group(2)
            if key in seen:
                first_ln, first_val = seen[key]
                where = f"{key} ({yml.name}:{first_ln} and :{ln})"
                (loc_conflicts if val != first_val else loc_dupes).append(where)
            else:
                seen[key] = (ln, val)
    if loc_conflicts:
        rep.fail("duplicate loc keys with conflicting text", ", ".join(loc_conflicts))
    if loc_dupes:
        rep.warn("duplicate loc keys (identical text)", ", ".join(loc_dupes))
    if not loc_conflicts and not loc_dupes:
        rep.ok("no duplicate localisation keys")

    print("\n== Cultures ==")
    check_culture_references(rep, mod, game, tags, records)

    print("\n== Areas ==")
    check_area_references(rep, mod, game)

    print("\n== Colors ==")
    check_revolutionary_colors(rep, mod, game)
    colrows = audit_colors(mod, game, tags)
    if colrows:
        for level, label, detail in colrows:
            # A deliberate collision is exemptable per tag via
            # KNOWN_EXCEPTIONS[tag]["color"]. This section used to fail
            # unconditionally, which meant the only way to share a colour with
            # the base game was to not need one. Tags are pulled out of the
            # detail rather than assumed to be the first word, because a
            # mod-to-mod row starts with the colour value and a mod-to-base
            # row starts with the tag.
            mentioned = [t for t in tags if re.search(rf"\b{t}\b", detail)]
            exc = next((KNOWN_EXCEPTIONS[t]["color"] for t in mentioned
                        if KNOWN_EXCEPTIONS.get(t, {}).get("color")), None)
            if exc:
                rep.log("INFO", label, f"{', '.join(mentioned)} exempt ({exc})")
            else:
                (rep.fail if level == "FAIL" else rep.warn)(label, detail)
    else:
        rep.ok("no color shared between mod tags or with base-game tags")

    gaps = hre_releasable_gaps(
        game, {r["capital"] for r in records if r.get("capital")}, ctx["game_loc"]
    )
    if gaps:
        rep.warn("HRE coverage", f"{len(gaps)} non-capital provinces have no releasable")
        for pid, name, owner in gaps:
            print(f"         {pid:5} {name} (owner {owner})")
    else:
        rep.ok("all non-capital HRE provinces have a releasable")

    for rec in records:
        conn.execute(
            "INSERT OR REPLACE INTO tags (tag, country_ref, name, adj, color, "
            "graphical_culture, flag_status, stub_file, province_file, government, "
            "government_rank, primary_culture, religion, technology_group, capital, "
            "fixed_capital, capital_name, owner, owner_capital, owner_name, "
            "province_culture, province_religion, "
            "province_hre, cores, cores_at_start, releasable_at_start, "
            "owns_provinces_at_start, ideas_block, traditions, ambition, idea_count, "
            "idea_names, ideas_trigger_lock, ideas_free) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
            "?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                rec["tag"], rec.get("country_ref"), rec.get("name"), rec.get("adj"),
                rec.get("color"), rec.get("graphical_culture"), rec.get("flag_status"),
                rec.get("stub_file"), rec.get("province_file"), rec.get("government"),
                rec.get("government_rank"), rec.get("primary_culture"), rec.get("religion"),
                rec.get("technology_group"), rec.get("capital"), rec.get("fixed_capital"),
                rec.get("capital_name"), rec.get("owner"), rec.get("owner_capital"),
                rec.get("owner_name"),
                rec.get("province_culture"), rec.get("province_religion"),
                rec.get("province_hre"), rec.get("cores"),
                rec.get("cores_at_start"), rec.get("releasable_at_start"),
                rec.get("owns_provinces_at_start"), rec.get("ideas_block"),
                rec.get("traditions"), rec.get("ambition"), rec.get("idea_count"),
                rec.get("idea_names"), rec.get("ideas_trigger_lock"),
                rec.get("ideas_free"),
            ),
        )
    for row in conn.execute(
        "SELECT tag, SUM(status = 'FAIL'), SUM(status = 'WARN') FROM checks GROUP BY tag"
    ):
        conn.execute(
            "UPDATE tags SET n_fail = ?, n_warn = ? WHERE tag = ?",
            (row[1] or 0, row[2] or 0, row[0]),
        )
    conn.executemany(
        "INSERT INTO orphans (kind, value, detail) VALUES (?, ?, ?)",
        [("stub_without_tag", n, "") for n in stub_orphans]
        + [("core_without_tag", c, ", ".join(fs)) for c, fs in core_orphans.items()]
        + [("base_game_collision", c, "") for c in collisions]
        + [
            ("province_without_releasable", f"{pid}", f"{name} (owner {owner})")
            for pid, name, owner in gaps
        ],
    )
    conn.executemany(
        "INSERT INTO meta (key, value) VALUES (?, ?)",
        [
            ("schema_version", "2"),
            ("tool", "verify_releasables.py"),
            ("mod", str(mod)),
            ("game", str(game)),
            ("run_at", datetime.now(timezone.utc).isoformat(timespec="seconds")),
            ("tags_total", str(len(tags))),
            ("fails_total", str(rep.fails)),
            ("warns_total", str(rep.warns)),
            ("exit_code", str(1 if rep.fails else 0)),
        ],
    )
    conn.commit()
    conn.close()

    print(f"\nResult: {len(tags)} tags, {rep.fails} FAIL, {rep.warns} WARN")
    print(f"Database: {db_path}")
    return 1 if rep.fails else 0


def remove_main(args: argparse.Namespace) -> int:
    mod = args.mod
    if not mod.is_dir():
        print(f"remove: mod directory not found: {mod}")
        return 2
    tags_in = sorted({t.upper() for t in args.tags})
    if not tags_in:
        print("remove: no tags given (usage: remove TAG [TAG ...] [--dry-run])")
        return 2
    bad = [t for t in tags_in if not re.fullmatch(r"[A-Z0-9]{3}", t)]
    if bad:
        print(f"remove: invalid tag name(s): {', '.join(bad)} (expect 3 letters/digits)")
        return 2
    tags_file = mod_tags_file(mod)
    defined = parse_tag_file(tags_file)
    unknown = [t for t in tags_in if t not in defined]
    if unknown:
        print(
            f"remove: tag(s) not defined in {tags_file.relative_to(mod)}: "
            f"{', '.join(unknown)}"
        )
        return 2

    st = ModState(mod, dry=args.dry_run)
    mode = "DRY RUN (nothing changed)" if args.dry_run else "REMOVE"
    for tag in tags_in:
        print(f"\n== {tag}: {mode} ==")
        for line in _remove_tag(st, args.game, tag):
            print(f"  {line}")
    if args.dry_run:
        print("\nDry run complete - no files changed.")
        return 0
    print("\nRemoval complete. Re-running verification...\n")
    return verify_main(args)


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "remove":
        return remove_main(args)
    return verify_main(args)


if __name__ == "__main__":
    sys.exit(main())
