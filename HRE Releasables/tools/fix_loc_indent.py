#!/usr/bin/env python3
"""fix_loc_indent.py - normalise indentation in EU4 localisation yml files.

Walks every .yml file under the given paths (default: the mod's localisation
folder) and re-indents each line from scratch:

- Entry lines (KEY:N "value") get exactly two leading spaces.
- All other lines (language headers, comments, blanks) get zero.
- The original content of each line is preserved except its leading
  whitespace, so the fix is idempotent: running it twice changes nothing.

Example:
  python3 tools/fix_loc_indent.py
  python3 tools/fix_loc_indent.py path/to/file.yml
  python3 tools/fix_loc_indent.py dir_one dir_two --check
"""

import argparse
import os
import re
import sys

ENTRY = re.compile(r"^[A-Za-z0-9_]+:\d+\s+\"")


def fix_line(line):
    content = line.strip()
    if not content:
        return ""
    if ENTRY.match(content):
        return "  " + content
    return content


def fix_file(path, check_only):
    with open(path, "rb") as f:
        raw = f.read()
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines()
    fixed = [fix_line(l) for l in lines]
    changed = sum(1 for a, b in zip(lines, fixed) if a != b)
    if check_only:
        return changed, None
    if changed == 0:
        return changed, None
    out = newline.join(fixed) + newline
    with open(path, "wb") as f:
        f.write(b"\xef\xbb\xbf" if bom else b"")
        f.write(out.encode("utf-8"))
    return changed, fixed


def collect(paths):
    files = []
    for p in paths:
        if os.path.isfile(p):
            files.append(p)
        elif os.path.isdir(p):
            for root, _dirs, names in os.walk(p):
                for n in sorted(names):
                    if n.endswith(".yml"):
                        files.append(os.path.join(root, n))
    return sorted(set(files))


def main():
    ap = argparse.ArgumentParser(description="normalise yml localisation indentation")
    ap.add_argument("paths", nargs="*", help="files or dirs (default: mod localisation)")
    ap.add_argument("--check", action="store_true", help="report only, do not write")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    mod = os.path.normpath(os.path.join(here, ".."))
    paths = args.paths or [os.path.join(mod, "localisation")]

    files = collect(paths)
    if not files:
        print("no .yml files found under:", " ".join(paths))
        return 1

    total = 0
    for f in files:
        changed, _ = fix_file(f, args.check)
        total += changed
        state = "fixed" if changed else "ok"
        print(f"{state}: {f} ({changed} lines)")
    print(f"total: {total} lines {'would change' if args.check else 'changed'}")
    return 0 if total == 0 or not args.check else 1


if __name__ == "__main__":
    sys.exit(main())