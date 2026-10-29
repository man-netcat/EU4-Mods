#!/usr/bin/env python3
"""How a check reports: OK and FAIL lines, warnings, and the list of failures the run ends on."""

fail: list = []


def _s(m):
    return m.encode("ascii", "replace").decode("ascii")


def note(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + _s(msg))
    if not ok:
        fail.append(msg)


def warn(msg):
    print("  WARN " + _s(msg))


def reset():
    fail.clear()


def summary() -> int:
    """Print the closing line and return the process exit code."""
    print("\n" + ("ALL CHECKS PASSED" if not fail else f"{len(fail)} FAILURES"))
    return 1 if fail else 0
