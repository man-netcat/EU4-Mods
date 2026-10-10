"""Normalize Paradox .yml loc files: UTF-8 BOM, LF endings, one leading
space on entry lines, no trailing whitespace, single trailing newline.

Usage: python3 tools/locfmt.py [--check] [path ...]   (default: localisation/)
--check only reports inconsistencies and exits 1 if any are found.
"""
import sys

HEADER_MARK = "l_english:"


def fmt_file(path, check=False):
    with open(path, "rb") as f:
        raw = f.read()
    text = raw.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    out = []
    fixes = []
    for i, ln in enumerate(text.split("\n"), 1):
        stripped = ln.strip()
        if not stripped or stripped.startswith("#") or stripped == HEADER_MARK:
            new = ln.rstrip()
        else:
            new = " " + ln.strip()
        if new != ln:
            fixes.append(i)
        out.append(new)
    # exactly one trailing newline: drop trailing blanks, re-add one
    while len(out) > 1 and not out[-1]:
        out.pop()
    new_text = "\n".join(out) + "\n"
    new_raw = b"\xef\xbb\xbf" + new_text.encode("utf-8")
    if new_raw != raw:
        if not check:
            with open(path, "wb") as f:
                f.write(new_raw)
        return fixes
    return []


def main(argv):
    check = "--check" in argv
    paths = [a for a in argv[1:] if a != "--check"]
    if not paths:
        import glob
        import os

        paths = sorted(
            glob.glob(os.path.join("localisation", "**", "*.yml"), recursive=True)
        )
    bad = 0
    for p in paths:
        fixes = fmt_file(p, check)
        if fixes:
            bad += 1
            print(f"{p}: {'would fix' if check else 'fixed'} lines {fixes}")
    if check:
        print("loc inconsistent" if bad else "loc consistent")
        return 1 if bad else 0
    print(f"done, {bad} file(s) touched")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
