#!/usr/bin/env python3
"""Verify the install copy is byte-identical to the generated OUT tree.

Run after syncing the mod to the install directory:
    python3 verify_install.py

Compares every file under OUT/ with its counterpart under the install
directory. Reports missing / extra / different files. Exits 0 when the
install is a faithful copy, 1 otherwise.
"""
import filecmp
import os
import sys

import verify_common as vc


def walk(root):
    out = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d != "tools"]
        for f in fn:
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, root)
            out.append(rel)
    return sorted(out)


if not os.path.isdir(vc.OUT):
    print("generated mod dir missing:", vc.OUT)
    sys.exit(1)
if not os.path.isdir(vc.INSTALL):
    print("install mod dir missing:", vc.INSTALL)
    sys.exit(1)

a = walk(vc.OUT)
b = walk(vc.INSTALL)
sa, sb = set(a), set(b)
missing = sorted(sa - sb)          # in OUT, not in install
extra = sorted(sb - sa)            # in install, not in OUT
common = sorted(sa & sb)
diff = [rel for rel in common
        if not filecmp.cmp(os.path.join(vc.OUT, rel), os.path.join(vc.INSTALL, rel),
                           shallow=False)]

print("OUT files:", len(a))
print("INSTALL files:", len(b))
print("common:", len(common), " missing:", len(missing), " extra:", len(extra),
      " different:", len(diff))
for rel in missing:
    print("  MISSING  ", rel)
for rel in extra:
    print("  EXTRA    ", rel)
for rel in diff:
    print("  DIFFERS  ", rel)

ok = not missing and not extra and not diff
print("ALL IDENTICAL" if ok else "INSTALL IS OUT OF SYNC")
sys.exit(0 if ok else 1)