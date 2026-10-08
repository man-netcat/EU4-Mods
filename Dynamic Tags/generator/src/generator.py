#!/usr/bin/env python3
"""EU4 Dynamic Tags Generator.

For every configured rule and base tag this generator allocates a fresh,
unused 3-letter tag and copies the base tag's country definition, flag and
localisation to it. Hidden events then switch a country between its base tag
and the variant tag while the rule's conditions hold, so the flag (and
everything else tied to the tag) changes dynamically.
"""

import glob
import itertools
import os
import re
import shutil
import string

from .core.constants import (
    GLOBAL_DECISION_KEYS,
    LOCALISATION_ENCODING,
    ON_ACTION_TRIGGERS,
    RESERVED_TAGS,
)
from .core.file_helpers import (
    build_decisions_file_path,
    build_event_file_path,
    build_global_localisation_file_path,
    build_localisation_file_path,
    build_master_event_file_path,
    build_mod_path,
    build_on_actions_file_path,
    ensure_directory,
    write_file_with_directory,
)
from .core.logging_utils import (
    log_error,
    log_master,
    log_module,
    log_warning,
    print_section_header,
)
from .defines.game_config import EVENT_NAME
from .defines.paths import (
    FLAG_SOURCES_CONFIG_PATH,
    MODULES_CONFIG_PATH,
    MOD_PATH,
    RULES_DIR,
    SOURCES_CONFIG_PATH,
    TAGS_PATH,
)
from .defines.templates import (
    DECISION_TEMPLATE,
    EVENT_SCRIPT_HEADER,
    MASTER_EVENT_TEMPLATE,
    TAG_DEPENDANT_EVENT_TEMPLATE,
)
from .utils import (
    build_change_tag_if,
    parse_rules_dir,
    read_conf_paths,
    read_lines,
    read_modules_config,
    read_tags_list,
)

MANIFEST_PATH = ".generated_manifest.txt"
TAG_LINE_RE = re.compile(r'^\s*([A-Za-z0-9]{3})\s*=\s*"([^"]+)"')
LOC_KEY_RE = re.compile(r'^\s*([A-Za-z0-9]{3}(?:_ADJ)?):\d*\s*"(.*)"\s*$')


def _rel_to_mod(path: str) -> str:
    """Return path relative to the mod root."""
    return os.path.relpath(os.path.abspath(path), os.path.abspath(MOD_PATH))


def cleanup_previous_outputs():
    """Delete all files recorded by the previous run."""
    removed = 0
    for entry in read_lines(MANIFEST_PATH):
        path = os.path.join(os.path.abspath(MOD_PATH), entry)
        if os.path.isfile(path):
            os.remove(path)
            removed += 1
    if removed:
        log_master(f"removed {removed} file(s) from the previous run")


def _write_manifest(paths: list[str]):
    unique = sorted({path for path in map(_rel_to_mod, paths)})
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(unique) + "\n")


class SourceIndex:
    """Index of tags, flags and localisation across all configured source roots.

    Roots are given in load order: for tags and localisation later roots
    override earlier ones, mirroring the in-game behaviour.
    """

    def __init__(self, roots: list[str]):
        self.roots = roots
        self.tag_defs: dict[str, str] = {}  # tag -> path of its country file
        self.flags_by_root: dict[str, dict[str, str]] = {}  # root -> {tag: flag path}
        self.loc: dict[str, str] = {}  # loc key -> value
        self.used_names: set[str] = set(RESERVED_TAGS)
        self._build()

    def _build(self):
        for root in self.roots:
            self._index_country_tags(root)
            self._index_flags(root)
            self._index_localisation(root)
        log_master(
            f"sources: {len(self.roots)} root(s), {len(self.tag_defs)} tag(s), "
            f"{len(self.used_names)} used/reserved name(s), {len(self.loc)} localisation key(s)"
        )

    def _index_country_tags(self, root: str):
        pattern = os.path.join(root, "common", "country_tags", "*.txt")
        for path in sorted(glob.glob(pattern)):
            with open(path, encoding="utf-8-sig", errors="replace") as f:
                for line in f:
                    if line.lstrip().startswith("#"):
                        continue
                    match = TAG_LINE_RE.match(line)
                    if match:
                        tag, rel = match.group(1).upper(), match.group(2)
                        self.tag_defs[tag] = os.path.join(root, "common", *rel.split("/"))
                        self.used_names.add(tag)

    def _index_flags(self, root: str):
        flag_dir = os.path.join(root, "gfx", "flags")
        flags: dict[str, str] = {}
        if os.path.isdir(flag_dir):
            for filename in sorted(os.listdir(flag_dir)):
                stem, ext = os.path.splitext(filename)
                if ext.lower() == ".tga" and re.fullmatch(r"[A-Za-z0-9]{3}", stem):
                    flags[stem.upper()] = os.path.join(flag_dir, filename)
                    self.used_names.add(stem.upper())
        self.flags_by_root[root] = flags

    def _index_localisation(self, root: str):
        localisation_dir = os.path.join(root, "localisation")
        if not os.path.isdir(localisation_dir):
            return
        for dirpath, dirnames, filenames in os.walk(localisation_dir):
            dirnames.sort()
            for filename in sorted(filenames):
                if not filename.endswith("l_english.yml"):
                    continue
                path = os.path.join(dirpath, filename)
                with open(path, encoding="utf-8-sig", errors="replace") as f:
                    for line in f:
                        match = LOC_KEY_RE.match(line)
                        if match:
                            self.loc[match.group(1).upper()] = match.group(2)


class TagAllocator:
    """Allocates unused 3-letter tags in deterministic order (AAA, AAB, ...)."""

    def __init__(self, used_names: set[str]):
        self._used = set(used_names)
        self._pool = (
            "".join(letters)
            for letters in itertools.product(string.ascii_uppercase, repeat=3)
        )

    def allocate(self) -> str | None:
        for tag in self._pool:
            if tag not in self._used:
                self._used.add(tag)
                return tag
        return None


class ModuleBuilder:
    """Builds all generated files for a single module."""

    def __init__(self, name: str, modules_root: str, index: SourceIndex, allocator: TagAllocator, flag_roots: list[str]):
        self.name = name
        self.index = index
        self.allocator = allocator
        self.flag_roots = flag_roots
        self.module_path = os.path.join(modules_root, name)
        self.event_name = f"{EVENT_NAME}_{name.lower()}"
        self.rules = parse_rules_dir(os.path.join(self.module_path, RULES_DIR))
        self.tags = read_tags_list(os.path.join(self.module_path, TAGS_PATH))
        self.files: list[str] = []
        rule_ids = [rule.id for rule in self.rules]
        if len(set(rule_ids)) != len(rule_ids):
            duplicates = sorted({rule_id for rule_id in rule_ids if rule_ids.count(rule_id) > 1})
            log_error(name, f"duplicate rule ids: {duplicates}")
            raise SystemExit(1)

    def build(self) -> tuple[bool, dict]:
        stats = {"variants": 0, "flags_copied": 0, "flags_missing": 0}

        if not self.rules:
            log_module(self.name, "(skipped - no rules)")
            return False, stats
        if not self.tags:
            log_module(self.name, "(skipped - no tags)")
            return False, stats

        dispatcher_lines: list[str] = []
        event_blocks: list[str] = []
        loc_lines = ["l_english:", " #Generated by EU4 Dynamic Tags Generator"]
        tag_lines: list[str] = []
        event_id = 1

        for base in self._unique_tags():
            blocks, involved, tag_stats = self._build_tag(base, loc_lines, tag_lines)
            for key, value in tag_stats.items():
                stats[key] += value
            if not blocks:
                continue

            if len(involved) == 1:
                tag_limit = f"tag = {involved[0]}"
            else:
                tag_limit = "OR = { " + " ".join(f"tag = {tag}" for tag in involved) + " }"

            dispatcher_lines.append(
                f"        if = {{ limit = {{ {tag_limit} }} country_event = {{ id = {self.event_name}.{event_id} }} }}"
            )
            event_blocks.append(
                TAG_DEPENDANT_EVENT_TEMPLATE.format(
                    event_name=self.event_name,
                    id=event_id,
                    tag_limit=tag_limit,
                    conditions="\n".join(blocks),
                )
            )
            event_id += 1

        if not dispatcher_lines:
            log_module(self.name, "(skipped - no applicable tags)")
            return False, stats

        self._check_duplicate_loc_keys(loc_lines)
        self._write_outputs(dispatcher_lines, event_blocks, loc_lines, tag_lines)

        log_module(
            self.name,
            f"{len(dispatcher_lines)} tag event(s), {stats['variants']} variant tag(s), "
            f"{stats['flags_copied']} flag(s) copied, {stats['flags_missing']} missing",
        )
        return True, stats

    def _unique_tags(self) -> list[str]:
        seen: set[str] = set()
        unique = []
        for tag in self.tags:
            if tag not in seen:
                seen.add(tag)
                unique.append(tag)
        return unique

    def _build_tag(self, base: str, loc_lines: list[str], tag_lines: list[str]) -> tuple[list[str], list[str], dict]:
        stats = {"variants": 0, "flags_copied": 0, "flags_missing": 0}

        country_file = self.index.tag_defs.get(base)
        if not country_file or not os.path.isfile(country_file):
            log_warning(self.name, f"unknown base tag '{base}' - skipped")
            return [], [], stats

        applicable = [rule for rule in self.rules if not rule.tags or base in rule.tags]
        if not applicable:
            return [], [], stats

        with open(country_file, "rb") as f:
            country_content = f.read()

        name = self.index.loc.get(base)
        name_adj = self.index.loc.get(f"{base}_ADJ")
        if not name:
            log_warning(self.name, f"missing localisation for '{base}' - using tag as name")
            name = base
        if not name_adj:
            log_warning(self.name, f"missing adjective for '{base}' - using name")
            name_adj = name

        blocks: list[str] = []
        involved = [base]
        for rule in applicable:
            if not rule.conditions:
                log_warning(self.name, f"rule '{rule.id}' has no conditions - skipped for {base}")
                continue

            new_tag = self.allocator.allocate()
            if not new_tag:
                log_error(self.name, "ran out of free 3-letter tags")
                raise SystemExit(1)

            self._write_country_file(new_tag, base, rule.id, country_content, tag_lines)

            if self._copy_flag(new_tag, base, rule.id):
                stats["flags_copied"] += 1
            else:
                stats["flags_missing"] += 1
                log_warning(self.name, f"no flag found for {base} ({rule.id})")

            loc_lines.append(f' {new_tag}:0 "{name}"')
            loc_lines.append(f' {new_tag}_ADJ:0 "{name_adj}"')

            blocks.append(build_change_tag_if(f"tag = {new_tag} NOT = {{ {rule.conditions} }}", base))
            blocks.append(build_change_tag_if(f"tag = {base} {rule.conditions}", new_tag))

            involved.append(new_tag)
            stats["variants"] += 1

        return blocks, involved, stats

    def _write_country_file(self, new_tag: str, base: str, rule_id: str, content: bytes, tag_lines: list[str]):
        filename = f"DynamicTags_{self.name}_{base}_{rule_id}.txt"
        path = build_mod_path("common", "countries", filename)
        ensure_directory(os.path.dirname(path))
        with open(path, "wb") as f:
            f.write(content)
        self.files.append(path)
        tag_lines.append(f'{new_tag} = "countries/{filename}"')

    def _copy_flag(self, new_tag: str, base: str, rule_id: str) -> bool:
        flag_source = self._find_flag(base, rule_id)
        if not flag_source:
            return False
        dest = build_mod_path("gfx", "flags", f"{new_tag}.tga")
        ensure_directory(os.path.dirname(dest))
        shutil.copyfile(flag_source, dest)
        self.files.append(dest)
        return True

    def _find_flag(self, base: str, rule_id: str) -> str | None:
        for root in self.flag_roots:
            for filename in (f"{base}_{rule_id}.tga", f"{base}.tga"):
                path = os.path.join(root, filename)
                if os.path.isfile(path):
                    return path
        for root in reversed(self.index.roots):
            path = self.index.flags_by_root[root].get(base)
            if path:
                return path
        return None

    def _check_duplicate_loc_keys(self, loc_lines: list[str]):
        seen: set[str] = set()
        for line in loc_lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped == "l_english:":
                continue
            key = stripped.split(":", 1)[0]
            if key in seen:
                log_error(self.name, f"duplicate localisation key '{key}'")
                raise SystemExit(1)
            seen.add(key)

    def _write_outputs(self, dispatcher_lines, event_blocks, loc_lines, tag_lines):
        header = EVENT_SCRIPT_HEADER.format(
            event_name=self.event_name, event_triggers="\n".join(dispatcher_lines)
        )
        event_path = build_event_file_path(self.event_name)
        write_file_with_directory(event_path, "\n".join([header] + event_blocks))
        self.files.append(event_path)

        tags_path = build_mod_path("common", "country_tags", f"{self.event_name}.txt")
        write_file_with_directory(
            tags_path,
            "# Generated by EU4 Dynamic Tags Generator\n" + "\n".join(tag_lines) + "\n",
        )
        self.files.append(tags_path)

        loc_path = build_localisation_file_path(self.event_name)
        write_file_with_directory(loc_path, "\n".join(loc_lines), LOCALISATION_ENCODING)
        self.files.append(loc_path)


def generate_on_actions() -> str:
    """Generate on_actions file that triggers events on various game events."""
    on_actions_lines = [
        f"{trigger} = {{ events = {{ {EVENT_NAME}.0 }} }}"
        for trigger in ON_ACTION_TRIGGERS
    ]
    on_actions_path = build_on_actions_file_path(EVENT_NAME)
    write_file_with_directory(on_actions_path, "\n\n".join(on_actions_lines))
    return on_actions_path


def generate_decision() -> str:
    """Generate decision file that allows manual triggering of tag updates."""
    decision_content = DECISION_TEMPLATE.format(event_name=EVENT_NAME)
    decision_path = build_decisions_file_path(EVENT_NAME)
    write_file_with_directory(decision_path, decision_content)
    return decision_path


def generate_global_localisation() -> str:
    """Generate the shared localisation file for the decision keys."""
    global_loc_lines = [
        "l_english:",
        " #Generated by EU4 Dynamic Tags Generator",
        " #decision",
        " " + GLOBAL_DECISION_KEYS["title"],
        " " + GLOBAL_DECISION_KEYS["desc"],
        " " + GLOBAL_DECISION_KEYS["tooltip"],
    ]
    global_loc_path = build_global_localisation_file_path(EVENT_NAME)
    write_file_with_directory(global_loc_path, "\n".join(global_loc_lines), LOCALISATION_ENCODING)
    return global_loc_path


def build_modules(modules_root: str):
    """Main entry point: build all modules and the shared mod files."""
    print_section_header("EU4 Dynamic Tags Generator")

    roots = read_conf_paths(SOURCES_CONFIG_PATH)
    if not roots:
        log_error("master", f"no usable roots configured in {SOURCES_CONFIG_PATH}")
        raise SystemExit(1)
    flag_roots = read_conf_paths(FLAG_SOURCES_CONFIG_PATH)

    index = SourceIndex(roots)
    allocator = TagAllocator(index.used_names)

    module_names = read_modules_config(os.path.join(os.path.dirname(modules_root), MODULES_CONFIG_PATH))
    builders = [
        ModuleBuilder(name, modules_root, index, allocator, flag_roots)
        for name in module_names
    ]

    cleanup_previous_outputs()

    manifest: list[str] = []
    triggers: list[str] = []
    built = 0
    skipped = 0
    total_variants = 0
    total_flags_copied = 0
    total_flags_missing = 0

    for i, builder in enumerate(builders, 1):
        log_master(f"[{i}/{len(builders)}] {builder.name}")
        success, stats = builder.build()
        manifest.extend(builder.files)
        if not success:
            skipped += 1
            continue
        built += 1
        triggers.append(f"country_event = {{ id = {builder.event_name}.0 }}")
        total_variants += stats["variants"]
        total_flags_copied += stats["flags_copied"]
        total_flags_missing += stats["flags_missing"]

    if not triggers:
        log_error("master", "no modules generated events - nothing to write")
        raise SystemExit(1)

    master_content = MASTER_EVENT_TEMPLATE.format(
        event_name=EVENT_NAME,
        module_triggers="\n".join("        " + trigger for trigger in triggers),
    )
    master_path = build_master_event_file_path(EVENT_NAME)
    write_file_with_directory(master_path, master_content)
    manifest.append(master_path)

    manifest.append(generate_on_actions())
    manifest.append(generate_decision())
    manifest.append(generate_global_localisation())
    _write_manifest(manifest)

    log_master(f"Built {built} module(s), skipped {skipped}")
    log_master(f"Generated {total_variants} variant tag(s)")
    log_master(f"Flags: {total_flags_copied} copied, {total_flags_missing} missing")
    log_master("Mod files generated")
