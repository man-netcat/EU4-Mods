#!/usr/bin/env bash
# Prepare a cloud (or any non-author) machine to run tools/build.py and
# tools/validate.py. Idempotent. Needs the private eu4-ck3-reference repo cloned
# next to this repo (or at $REFERENCE_DIR); without it, only deps install.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REF="${REFERENCE_DIR:-$(cd "$HERE/../.." && pwd)/../eu4-ck3-reference}"

python3 -c "import sqlalchemy" 2>/dev/null || pip install -q -r "$HERE/requirements.txt"
mkdir -p "$HERE/cache"

if [ -d "$REF/eu4" ] && [ -d "$REF/ck3/game" ]; then
  if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
    {
      echo "export EU4_GAME='$REF/eu4'"
      echo "export CK3_GAME='$REF/ck3/game'"
    } >> "$CLAUDE_ENV_FILE"
  fi
  echo "reference found: EU4_GAME=$REF/eu4 CK3_GAME=$REF/ck3/game"
else
  echo "reference repo not found at $REF - ask Claude to add man-netcat/eu4-ck3-reference" \
       "and clone it to $REF, then re-run tools/cloud_setup.sh" >&2
fi
