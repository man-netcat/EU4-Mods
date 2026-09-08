#!/bin/bash
# verify_formable.sh — Validates a formable nation tag against EU4 basegame and mod structure
# Usage: ./verify_formable.sh <TAG> [basegame_path]
# Example: ./verify_formable.sh PAK
#          ./verify_formable.sh SLV "/home/rick/Paradox/Games/Europa Universalis IV"

set -uo pipefail

# ─── Config ──────────────────────────────────────────────────────────────────
MOD_DIR="$(cd "$(dirname "$0")" && pwd)"
BASEGAME="${2:-/home/rick/Paradox/Games/Europa Universalis IV}"
PROVINCES_CSV="/home/rick/Paradox/EU4 Resources/EU4 provinces.csv"
AREA_FILE="$BASEGAME/map/area.txt"
REGION_FILE="$BASEGAME/map/region.txt"
SUPERREGION_FILE="$BASEGAME/map/superregion.txt"
COUNTRY_TAGS_BASE="$BASEGAME/common/country_tags/00_countries.txt"

TAG="${1:-}"
if [ -z "$TAG" ]; then
  echo "Usage: $0 <TAG> [basegame_path]"
  echo "  TAG         3-letter country tag (e.g. PAK, SLV, SVK)"
  echo "  basegame    Path to EU4 installation (default: $BASEGAME)"
  exit 1
fi

# ─── Helpers ─────────────────────────────────────────────────────────────────
PASS=0
FAIL=0
WARN=0

pass() { ((PASS++)); echo "  ✅ $1"; }
fail() { ((FAIL++)); echo "  ❌ $1"; }
warn() { ((WARN++)); echo "  ⚠️  $1"; }

separator() { echo ""; echo "═══ $1 ═══"; }

# ─── Start ───────────────────────────────────────────────────────────────────
echo ""
echo "🔍 Verifying formable tag: $TAG"
echo "   Mod:    $MOD_DIR"
echo "   Base:   $BASEGAME"

# ═══════════════════════════════════════════════════════════════════════════════
# 1. TAG REGISTRATION
# ═══════════════════════════════════════════════════════════════════════════════
separator "1. Tag Registration"

# 1a. Tag exists in mod country_tags
TAG_FILE=$(grep "^$TAG " "$MOD_DIR/common/country_tags/more_formables.txt" 2>/dev/null || true)
if [ -n "$TAG_FILE" ]; then
  pass "Tag $TAG found in mod country_tags"
else
  fail "Tag $TAG NOT found in mod country_tags"
fi

# 1b. Extract country def filename from tag line
COUNTRY_FILE=$(echo "$TAG_FILE" | grep -oE '"countries/[^"]+' | sed 's/"countries\///')
if [ -n "$COUNTRY_FILE" ]; then
  pass "Country file: countries/$COUNTRY_FILE"
else
  fail "Could not extract country file path from tag line"
fi

# 1c. Tag doesn't conflict with vanilla
VANILLA_TAG=$(grep "^$TAG " "$COUNTRY_TAGS_BASE" 2>/dev/null || true)
if [ -n "$VANILLA_TAG" ]; then
  warn "Tag $TAG also exists in vanilla! ($VANILLA_TAG)"
else
  pass "Tag $TAG does not conflict with vanilla"
fi

# 1d. Tag doesn't conflict with other mod tags (across all enabled mods)
MOD_BASE="/home/rick/.local/share/Paradox Interactive/Europa Universalis IV/mod"
CONFLICT_COUNT=0
for OTHER_MOD_DIR in "$MOD_BASE"/*/; do
  [ -d "$OTHER_MOD_DIR/common/country_tags" ] || continue
  for F in "$OTHER_MOD_DIR/common/country_tags"/*.txt; do
    [ -f "$F" ] || continue
    REAL_F=$(realpath "$F" 2>/dev/null || echo "$F")
    REAL_MOD_TAG=$(realpath "$MOD_DIR/common/country_tags/more_formables.txt" 2>/dev/null || echo "$MOD_DIR/common/country_tags/more_formables.txt")
    [ "$REAL_F" = "$REAL_MOD_TAG" ] && continue
    MATCH=$(grep "^$TAG " "$F" 2>/dev/null || true)
    if [ -n "$MATCH" ]; then
      warn "Tag $TAG also defined in: $F"
      ((CONFLICT_COUNT++))
    fi
  done
done
if [ "$CONFLICT_COUNT" -eq 0 ]; then
  pass "No cross-mod tag conflicts"
fi

# ═══════════════════════════════════════════════════════════════════════════════
# 2. COUNTRY DEFINITION FILE
# ═══════════════════════════════════════════════════════════════════════════════
separator "2. Country Definition"

COUNTRY_DEF="$MOD_DIR/common/countries/$COUNTRY_FILE"
if [ -f "$COUNTRY_DEF" ]; then
  pass "Country definition file exists: $COUNTRY_FILE"

  # 2a. Has graphical_culture
  if grep -q "graphical_culture" "$COUNTRY_DEF"; then
    GFX=$(grep "graphical_culture" "$COUNTRY_DEF" | head -1 | sed 's/.*= *//')
    pass "graphical_culture = $GFX"
    # Verify it's a valid value
    case "$GFX" in
      westerngfx|easterngfx|asiangfx|mongolgfx|muslimgfx|indiangfx|africangfx|southerngfx|aboriginalgfx)
        pass "Valid graphical_culture value" ;;
      *) warn "Unusual graphical_culture: $GFX" ;;
    esac
  else
    fail "Missing graphical_culture"
  fi

  # 2b. Has color
  if grep -q "color = {" "$COUNTRY_DEF"; then
    COLOR=$(grep "color = {" "$COUNTRY_DEF" | head -1)
    pass "Color defined"
    # Check RGB values are 0-255
    RGB=$(echo "$COLOR" | grep -oE '[0-9]+' | head -3)
    BAD_COLOR=0
    for V in $RGB; do
      [ "$V" -gt 255 ] 2>/dev/null && BAD_COLOR=1
    done
    if [ "$BAD_COLOR" -eq 1 ]; then
      fail "Color values out of range (0-255): $COLOR"
    fi
  else
    fail "Missing color definition"
  fi

  # 2c. Has historical_idea_groups
  if grep -q "historical_idea_groups" "$COUNTRY_DEF"; then
    IDEAS=$(grep -A 10 "historical_idea_groups" "$COUNTRY_DEF" | grep -oE '[a-z_]+_ideas' | head -8)
    IDEA_COUNT=$(echo "$IDEAS" | grep -c '_ideas' || true)
    if [ "$IDEA_COUNT" -ge 8 ]; then
      pass "historical_idea_groups has $IDEA_COUNT entries"
    else
      warn "historical_idea_groups has only $IDEA_COUNT entries (expected 8)"
    fi
  else
    fail "Missing historical_idea_groups"
  fi

  # 2d. Has monarch_names
  if grep -q "monarch_names" "$COUNTRY_DEF"; then
    MN_COUNT=$(grep -c '"[^"]*"' "$COUNTRY_DEF" | head -1 || true)
    pass "monarch_names defined"
  else
    warn "No monarch_names defined"
  fi

  # 2e. Has leader_names
  if grep -q "leader_names" "$COUNTRY_DEF"; then
    pass "leader_names defined"
  else
    warn "No leader_names defined"
  fi

  # 2f. Has ship_names
  if grep -q "ship_names" "$COUNTRY_DEF"; then
    pass "ship_names defined"
  else
    warn "No ship_names defined"
  fi
else
  fail "Country definition file NOT found: $COUNTRY_FILE"
fi

# ═══════════════════════════════════════════════════════════════════════════════
# 3. HISTORY FILE
# ═══════════════════════════════════════════════════════════════════════════════
separator "3. History File"

HIST_DIR="$MOD_DIR/history/countries"
HIST_FILE=$(ls "$HIST_DIR" | grep "^$TAG - " 2>/dev/null || true)
if [ -n "$HIST_FILE" ]; then
  pass "History file found: $HIST_FILE"
  HIST_PATH="$HIST_DIR/$HIST_FILE"

  # 3a. Has government
  if grep -q "government" "$HIST_PATH"; then
    GOV=$(grep "government" "$HIST_PATH" | head -1 | sed 's/.*= *//')
    pass "government = $GOV"
  else
    warn "No government defined in history"
  fi

  # 3b. Has capital
  if grep -q "capital" "$HIST_PATH"; then
    CAP=$(grep "capital" "$HIST_PATH" | head -1 | grep -oE '[0-9]+')
    if [ -n "$CAP" ]; then
      # Verify capital province exists
      PROV=$(grep "^$CAP;" "$PROVINCES_CSV" 2>/dev/null || true)
      if [ -n "$PROV" ]; then
        PROV_NAME=$(echo "$PROV" | cut -d';' -f2)
        pass "capital = $CAP ($PROV_NAME)"
      else
        fail "capital = $CAP does not exist in province database!"
      fi
    fi
  else
    warn "No capital defined in history"
  fi
else
  warn "No history file found for $TAG (OK if formed via decision only)"
fi

# ═══════════════════════════════════════════════════════════════════════════════
# 4. FLAG FILE
# ═══════════════════════════════════════════════════════════════════════════════
separator "4. Flag File"

FLAG_FILE="$MOD_DIR/gfx/flags/$TAG.tga"
if [ -f "$FLAG_FILE" ]; then
  FILE_SIZE=$(stat -c%s "$FLAG_FILE" 2>/dev/null || stat -f%z "$FLAG_FILE" 2>/dev/null || echo "0")
  if [ "$FILE_SIZE" -gt 0 ]; then
    pass "Flag file exists: gfx/flags/$TAG.tga ($FILE_SIZE bytes)"
  else
    fail "Flag file exists but is empty: gfx/flags/$TAG.tga"
  fi
else
  # Check if vanilla has a flag for this tag
  VANILLA_FLAG="$BASEGAME/gfx/flags/$TAG.tga"
  if [ -f "$VANILLA_FLAG" ]; then
    pass "No mod flag, but vanilla flag exists (will use vanilla)"
  else
    fail "No flag file! Neither mod nor vanilla has gfx/flags/$TAG.tga"
  fi
fi

# ═══════════════════════════════════════════════════════════════════════════════
# 5. DECISIONS
# ═══════════════════════════════════════════════════════════════════════════════
separator "5. Decisions"

# Find which decision file contains this tag's formation decision
DECISIONS_DIR="$MOD_DIR/decisions"
DECISION_FILE=""
DECISION_NAME=""
DEC_BLOCK=""

extract_decision_block() {
  local file="$1"
  local anchor="$2"
  awk -v pat="$anchor" '
    BEGIN { n=0 }
    { lines[n++] = $0 }
    END {
      target = -1
      for (i = 0; i < n; i++) {
        if (index(lines[i], pat) > 0) { target = i; break }
      }
      if (target < 0) exit
      start = target
      for (i = target; i >= 0; i--) {
        if (lines[i] ~ /^\t[a-z][a-z_]* = \{/) { start = i; break }
      }
      depth = 0
      for (i = start; i < n; i++) {
        for (j = 1; j <= length(lines[i]); j++) {
          c = substr(lines[i], j, 1)
          if (c == "{") depth++
          if (c == "}") depth--
        }
        print lines[i]
        if (depth <= 0 && i > start) exit
      }
    }
  ' "$file"
}

for DF in "$DECISIONS_DIR"/*.txt; do
  [ -f "$DF" ] || continue
  if grep -q "change_tag = $TAG" "$DF" 2>/dev/null; then
    DECISION_FILE="$DF"
    DECISION_NAME=$(basename "$DF")
    DEC_BLOCK=$(extract_decision_block "$DF" "change_tag = $TAG")
    break
  fi
  if grep -q "override_country_name" "$DF" 2>/dev/null && grep -q "tag = $TAG" "$DF" 2>/dev/null; then
    DECISION_FILE="$DF"
    DECISION_NAME=$(basename "$DF")
    DEC_BLOCK=$(extract_decision_block "$DF" "override_country_name")
    break
  fi
done

if [ -n "$DECISION_FILE" ]; then
  pass "Formation/upgrade decision found in: $DECISION_NAME"

  if echo "$DEC_BLOCK" | grep -q "major = yes"; then
    pass "Decision is marked major = yes"
  else
    warn "Decision may not be marked major = yes"
  fi

  # 5c. Verify province IDs in provinces_to_highlight and allow
  echo ""
  echo "  Province ID checks:"
  echo "$DEC_BLOCK" | grep -oE 'province_id = [0-9]+' | grep -oE '[0-9]+' | sort -u | while read -r PID; do
    PROV=$(grep "^$PID;" "$PROVINCES_CSV" 2>/dev/null || true)
    if [ -n "$PROV" ]; then
      PROV_NAME=$(echo "$PROV" | cut -d';' -f2)
      PROV_AREA=$(echo "$PROV" | cut -d';' -f6)
      pass "Province $PID: $PROV_NAME (area: $PROV_AREA)"
    else
      fail "Province $PID: NOT FOUND in province database!"
    fi
  done

  # 5d. Verify owns_core_province references
  echo ""
  echo "  owns_core_province checks:"
  echo "$DEC_BLOCK" | grep -oE 'owns_core_province = [0-9]+' | grep -oE '[0-9]+' | sort -u | while read -r PID; do
    PROV=$(grep "^$PID;" "$PROVINCES_CSV" 2>/dev/null || true)
    if [ -n "$PROV" ]; then
      PROV_NAME=$(echo "$PROV" | cut -d';' -f2)
      pass "owns_core_province $PID: $PROV_NAME"
    else
      fail "owns_core_province $PID: NOT FOUND!"
    fi
  done

  # 5e. Verify area names in claims
  echo ""
  echo "  Area name checks:"
  echo "$DEC_BLOCK" | grep -oE '[a-z_]+_area' | sort -u | while read -r AREA; do
    if grep -q "^$AREA" "$AREA_FILE" 2>/dev/null; then
      pass "Area: $AREA"
    else
      fail "Area: $AREA NOT FOUND in basegame area.txt!"
    fi
  done

  # 5f. Verify move_capital province
  MOVE_CAP=$(echo "$DEC_BLOCK" | grep -oE '[0-9]+ = \{' | grep -B 1 "move_capital" | grep -oE '[0-9]+' | head -1 || true)
  if [ -n "$MOVE_CAP" ]; then
    PROV=$(grep "^$MOVE_CAP;" "$PROVINCES_CSV" 2>/dev/null || true)
    if [ -n "$PROV" ]; then
      PROV_NAME=$(echo "$PROV" | cut -d';' -f2)
      pass "move_capital province $MOVE_CAP: $PROV_NAME"
    else
      fail "move_capital province $MOVE_CAP: NOT FOUND!"
    fi
  fi

  # 5g. Check for set_country_flag
  if echo "$DEC_BLOCK" | grep -q "set_country_flag"; then
    FLAG=$(echo "$DEC_BLOCK" | grep "set_country_flag" | head -1 | awk '{print $NF}')
    pass "Sets country_flag: $FLAG"
  else
    warn "No set_country_flag found (re-forming not prevented)"
  fi

  # 5h. Check for on_change_tag_effect
  if echo "$DEC_BLOCK" | grep -q "on_change_tag_effect"; then
    pass "Calls on_change_tag_effect"
  else
    warn "No on_change_tag_effect call"
  fi

else
  fail "No formation decision found for tag $TAG in $DECISIONS_DIR/"
fi

# ═══════════════════════════════════════════════════════════════════════════════
# 6. NATIONAL IDEAS
# ═══════════════════════════════════════════════════════════════════════════════
separator "6. National Ideas"

IDEAS_DIR="$MOD_DIR/common/ideas"
IDEA_SET=""
for IF in "$IDEAS_DIR"/*.txt; do
  [ -f "$IF" ] || continue
  if grep -q "${TAG}_ideas" "$IF" 2>/dev/null; then
    IDEA_SET="$IF"
    break
  fi
done

if [ -n "$IDEA_SET" ]; then
  pass "Idea set found: $(basename "$IDEA_SET")"

  # Count ideas in the set
  IDEA_CONTENT=$(sed -n "/${TAG}_ideas = {/,/^}/p" "$IDEA_SET" 2>/dev/null || true)
  IDEA_COUNT=$(echo "$IDEA_CONTENT" | grep -cE '^\t[a-z_]+ = \{' 2>/dev/null || true)
  # Also check without leading tab
  IDEA_COUNT2=$(echo "$IDEA_CONTENT" | grep -cE '^[[:space:]][a-z_]+ = \{' 2>/dev/null || true)
  TOTAL_IDEAS=$((IDEA_COUNT + IDEA_COUNT2))

  if [ "$TOTAL_IDEAS" -ge 9 ]; then
    pass "Idea set has $TOTAL_IDEAS ideas (traditions + 7 + ambition)"
  elif [ "$TOTAL_IDEAS" -ge 7 ]; then
    warn "Idea set has $TOTAL_IDEAS ideas (expected 9: traditions + 7 + ambition)"
  else
    fail "Idea set has only $TOTAL_IDEAS ideas (expected 9)"
  fi

  # Check trigger matches tag
  if echo "$IDEA_CONTENT" | grep -q "tag = $TAG"; then
    pass "Idea trigger matches tag = $TAG"
  else
    fail "Idea trigger does NOT match tag = $TAG!"
  fi

  # Check has start, bonus, free
  for SECTION in "start" "bonus" "trigger"; do
    if echo "$IDEA_CONTENT" | grep -q "$SECTION = {"; then
      pass "Has $SECTION block"
    else
      fail "Missing $SECTION block in ideas"
    fi
  done

  if echo "$IDEA_CONTENT" | grep -q "free = yes"; then
    pass "Has free = yes"
  else
    warn "Missing free = yes"
  fi
else
  fail "No idea set found for ${TAG}_ideas in $IDEAS_DIR/"
fi

# ═══════════════════════════════════════════════════════════════════════════════
# 7. LOCALISATION
# ═══════════════════════════════════════════════════════════════════════════════
separator "7. Localisation"

LOC_DIR="$MOD_DIR/localisation/english"
if [ -d "$LOC_DIR" ]; then
  # Check for tag name loc
  TAG_LOC=$(grep -l "^ $TAG:" "$LOC_DIR"/*.yml 2>/dev/null || true)
  if [ -n "$TAG_LOC" ]; then
    pass "Tag localisation found: $(basename "$TAG_LOC")"
    TAG_NAME=$(grep "^ $TAG:" "$TAG_LOC" | head -1 | sed 's/.*:0 "//;s/"//')
    pass "  Display name: $TAG_NAME"
  else
    fail "No localisation for tag $TAG in $LOC_DIR/"
  fi

  # Check for ADJ loc
  ADJ_LOC=$(grep -l "^ ${TAG}_ADJ:" "$LOC_DIR"/*.yml 2>/dev/null || true)
  if [ -n "$ADJ_LOC" ]; then
    pass "Adjective localisation found"
  else
    warn "No adjective localisation (${TAG}_ADJ)"
  fi

  # Check for idea loc
  IDEA_LOC=$(grep -l "^ ${TAG}_ideas:" "$LOC_DIR"/*.yml 2>/dev/null || true)
  if [ -n "$IDEA_LOC" ]; then
    pass "Idea set localisation found"
  else
    fail "No localisation for ${TAG}_ideas"
  fi

  DEC_NAME=$(echo "$DEC_BLOCK" 2>/dev/null | head -1 | grep -oE '[a-z_]+' | head -1 || true)
  if [ -n "$DEC_NAME" ]; then
    DEC_TITLE_KEY="${DEC_NAME}_title"
    DEC_DESC_KEY="${DEC_NAME}_desc"
    TITLE_LOC=$(grep -l "^ $DEC_TITLE_KEY:" "$LOC_DIR"/*.yml 2>/dev/null || true)
    if [ -n "$TITLE_LOC" ]; then
      pass "Decision title loc: $DEC_TITLE_KEY"
    else
      fail "Missing decision title loc: $DEC_TITLE_KEY"
    fi
    DESC_LOC=$(grep -l "^ $DEC_DESC_KEY:" "$LOC_DIR"/*.yml 2>/dev/null || true)
    if [ -n "$DESC_LOC" ]; then
      pass "Decision desc loc: $DEC_DESC_KEY"
    else
      fail "Missing decision desc loc: $DEC_DESC_KEY"
    fi
  fi

  # Check idea name locs
  if [ -n "$IDEA_SET" ]; then
    echo ""
    echo "  Idea localisation checks:"
    echo "$IDEA_CONTENT" 2>/dev/null | grep -oP '^\t\K[a-z_]+(?= = \{)' 2>/dev/null | grep -vE '^(start|bonus|trigger)$' | while read -r IK; do
      IK_LOC=$(grep -l "^ $IK:" "$LOC_DIR"/*.yml 2>/dev/null || true)
      IK_DESC_LOC=$(grep -l "^ ${IK}_desc:" "$LOC_DIR"/*.yml 2>/dev/null || true)
      if [ -n "$IK_LOC" ] && [ -n "$IK_DESC_LOC" ]; then
        pass "Idea loc: $IK + desc"
      elif [ -n "$IK_LOC" ]; then
        warn "Idea loc: $IK (missing _desc)"
      else
        fail "Missing idea loc: $IK"
      fi
    done
  fi
else
  fail "localisation/english/ directory not found"
fi

# ═══════════════════════════════════════════════════════════════════════════════
# 8. EVENTS (if applicable)
# ═══════════════════════════════════════════════════════════════════════════════
separator "8. Events"

EVENTS_DIR="$MOD_DIR/events"
EVENT_NAMESPACE=""
for EF in "$EVENTS_DIR"/*.txt; do
  [ -f "$EF" ] || continue
  if grep -q "tag = $TAG" "$EF" 2>/dev/null; then
    EVENT_NAMESPACE=$(grep "namespace = " "$EF" | head -1 | awk '{print $3}')
    pass "Events found in: $(basename "$EF") (namespace: $EVENT_NAMESPACE)"

    # Check for vanilla namespace conflicts
    VANILLA_NS=$(grep -r "namespace = $EVENT_NAMESPACE" "$BASEGAME/events/" 2>/dev/null | head -1 || true)
    if [ -n "$VANILLA_NS" ]; then
      fail "Namespace '$EVENT_NAMESPACE' conflicts with vanilla!"
    else
      pass "Namespace '$EVENT_NAMESPACE' does not conflict with vanilla"
    fi
    break
  fi
done
if [ -z "$EVENT_NAMESPACE" ]; then
  pass "No events for $TAG (OK if no rename event)"
fi

# ═══════════════════════════════════════════════════════════════════════════════
# 9. CULTURES (if applicable)
# ═══════════════════════════════════════════════════════════════════════════════
separator "9. Cultures"

# Check what primary_cultures can form this tag (from decision potential block)
if [ -n "$DEC_BLOCK" ]; then
  FORMING_CULTURES=$(echo "$DEC_BLOCK" | grep -oE 'primary_culture = [a-z_]+' | grep -oE '[a-z_]+$' | sort -u)
  if [ -n "$FORMING_CULTURES" ]; then
    echo "  Cultures that can form $TAG:"
    for CULTURE in $FORMING_CULTURES; do
      # Check if culture exists in vanilla
      VANILLA_CULTURE=$(grep -rl "$CULTURE" "$BASEGAME/common/cultures/" 2>/dev/null | head -1 || true)
      # Also check mod cultures
      MOD_CULTURE=$(grep -rl "$CULTURE" "$MOD_DIR/common/cultures/" 2>/dev/null | head -1 || true)
      if [ -n "$VANILLA_CULTURE" ] || [ -n "$MOD_CULTURE" ]; then
        pass "Culture '$CULTURE' exists"
      else
        fail "Culture '$CULTURE' NOT FOUND in vanilla or mod!"
      fi
    done
  fi
fi

# Check if the mod defines custom cultures
if [ -d "$MOD_DIR/common/cultures" ]; then
  for CF in "$MOD_DIR/common/cultures"/*.txt; do
    [ -f "$CF" ] || continue
    CULTURE_GROUP=$(head -1 "$CF" | tr -d ' {' || true)
    if [ -n "$CULTURE_GROUP" ]; then
      pass "Mod defines culture group: $CULTURE_GROUP"
    fi
  done
fi

# ═══════════════════════════════════════════════════════════════════════════════
# 10. INTEGRITY CHECKS
# ═══════════════════════════════════════════════════════════════════════════════
separator "10. Integrity Checks"

# 10a. All tags in country_tags have matching country def files
echo "  Checking all tags in mod..."
while IFS='=' read -r T PATH_LINE; do
  T=$(echo "$T" | tr -d ' ')
  FNAME=$(echo "$PATH_LINE" | xargs | tr -d '"' | sed 's|countries/||')
  if [ -f "$MOD_DIR/common/countries/$FNAME" ]; then
    : # ok
  else
    fail "Tag $T references missing file: countries/$FNAME"
  fi
done < <(grep '^[A-Z]' "$MOD_DIR/common/country_tags/more_formables.txt" 2>/dev/null)

# 10b. All country def files have matching tags
echo "  Checking all country def files..."
for CF in "$MOD_DIR/common/countries"/*.txt; do
  [ -f "$CF" ] || continue
  FNAME=$(basename "$CF")
  if ! grep -q "\"countries/$FNAME\"" "$MOD_DIR/common/country_tags/more_formables.txt" 2>/dev/null; then
    warn "Country def file '$FNAME' has no tag in country_tags"
  fi
done

# 10c. All history files have matching tags
echo "  Checking all history files..."
for HF in "$MOD_DIR/history/countries"/*.txt; do
  [ -f "$HF" ] || continue
  FNAME=$(basename "$HF")
  HIST_TAG=$(echo "$FNAME" | cut -d' ' -f1)
  if ! grep -q "^$HIST_TAG " "$MOD_DIR/common/country_tags/more_formables.txt" 2>/dev/null; then
    warn "History file '$FNAME' has tag '$HIST_TAG' not in country_tags"
  fi
done

# ═══════════════════════════════════════════════════════════════════════════════
# 11. NAME-CHANGE / UPGRADE PATH
# ═══════════════════════════════════════════════════════════════════════════════
separator "11. Name-Change / Upgrade Path"

if [ -n "$DEC_BLOCK" ]; then
  OVERRIDE_NAME=$(echo "$DEC_BLOCK" | grep -oE 'override_country_name = [A-Z_]+' | head -1 | awk '{print $3}' || true)
  CHANGE_TO=$(echo "$DEC_BLOCK" | grep -oE 'change_tag = [A-Z_]+' | head -1 | awk '{print $3}' || true)

  if [ -n "$OVERRIDE_NAME" ]; then
    pass "Decision uses override_country_name = $OVERRIDE_NAME (Great Armenia style)"

    if [ -d "$MOD_DIR/localisation/english" ]; then
      OV_LOC=$(grep -l "^ $OVERRIDE_NAME:" "$MOD_DIR/localisation/english/"*.yml 2>/dev/null || true)
      if [ -n "$OV_LOC" ]; then
        OV_DISPLAY=$(grep "^ $OVERRIDE_NAME:" "$OV_LOC" | head -1 | sed 's/.*:0 "//;s/"//')
        pass "override_country_name loc key '$OVERRIDE_NAME' exists: \"$OV_DISPLAY\""
      else
        fail "override_country_name loc key '$OVERRIDE_NAME' NOT FOUND in localisation!"
      fi
    else
      fail "localisation/english/ directory not found"
    fi

    UPGRADE_FLAG=$(echo "$DEC_BLOCK" | grep -oE 'set_country_flag = [a-z_]+' | awk '{print $3}' | head -1 || true)
    if [ -n "$UPGRADE_FLAG" ]; then
      pass "Decision sets flag: $UPGRADE_FLAG"
    fi

    if echo "$DEC_BLOCK" | grep -q "swap_free_idea_group"; then
      pass "Decision calls swap_free_idea_group"
    else
      warn "No swap_free_idea_group — upgraded ideas may not activate"
    fi

    if echo "$DEC_BLOCK" | grep -q "change_tag = "; then
      warn "Decision uses change_tag — this is a tag-change, not a name-override upgrade"
    else
      pass "Same-tag upgrade (no change_tag) — correct Great Armenia pattern"
    fi

    if echo "$DEC_BLOCK" | grep -q "has_overriden_name_flag"; then
      pass "Sets has_overriden_name_flag"
    else
      warn "Missing has_overriden_name_flag"
    fi

  elif [ -n "$CHANGE_TO" ]; then
    pass "Standard tag-change formable: → $CHANGE_TO"

    DEC_TAG=$(echo "$DEC_BLOCK" | grep -m1 -oE 'tag = [A-Z]{3}' | awk '{print $3}' || true)
    if [ -n "$DEC_TAG" ]; then
      if [ "$DEC_TAG" = "$CHANGE_TO" ]; then
        pass "Any-culture formable → $CHANGE_TO"
      else
        pass "Tag-specific upgrade: $DEC_TAG → $CHANGE_TO"

        VANILLA_SRC=$(grep "^$DEC_TAG " "$COUNTRY_TAGS_BASE" 2>/dev/null || true)
        if [ -n "$VANILLA_SRC" ]; then
          pass "Source tag $DEC_TAG exists in vanilla"
        else
          MOD_SRC=$(grep "^$DEC_TAG " "$MOD_DIR/common/country_tags/"*.txt 2>/dev/null || true)
          if [ -n "$MOD_SRC" ]; then
            pass "Source tag $DEC_TAG exists in mod"
          else
            warn "Source tag $DEC_TAG not found in vanilla or mod"
          fi
        fi

        SRC_HIST=$(ls "$HIST_DIR" 2>/dev/null | grep "^$DEC_TAG - " || true)
        VANILLA_SRC_HIST=$(ls "$BASEGAME/history/countries" 2>/dev/null | grep "^$DEC_TAG - " || true)
        if [ -n "$SRC_HIST" ] || [ -n "$VANILLA_SRC_HIST" ]; then
          pass "Source tag $DEC_TAG has a history file"
        else
          warn "Source tag $DEC_TAG has no history file"
        fi

        UPGRADE_FLAG2=$(echo "$DEC_BLOCK" | grep -oE 'set_country_flag = [a-z_]+' | awk '{print $3}' | tail -1 || true)
        if [ -n "$UPGRADE_FLAG2" ]; then
          pass "Decision sets country_flag: $UPGRADE_FLAG2"
        else
          warn "No set_country_flag found (re-forming not prevented)"
        fi

        SRC_IDEAS=""
        for IF in "$BASEGAME/common/ideas"/*.txt "$MOD_DIR/common/ideas"/*.txt; do
          [ -f "$IF" ] || continue
          if grep -q "${DEC_TAG}_ideas" "$IF" 2>/dev/null; then
            SRC_IDEAS="$IF"
            break
          fi
        done
        if [ -n "$SRC_IDEAS" ]; then
          pass "Source tag $DEC_TAG has ideas: $(basename "$SRC_IDEAS")"
        else
          warn "Source tag $DEC_TAG has no ideas found"
        fi

        TARGET_IDEAS=""
        for IF in "$MOD_DIR/common/ideas"/*.txt; do
          [ -f "$IF" ] || continue
          if grep -q "${CHANGE_TO}_ideas" "$IF" 2>/dev/null; then
            TARGET_IDEAS="$IF"
            break
          fi
        done
        if [ -n "$TARGET_IDEAS" ]; then
          pass "Target tag $CHANGE_TO has mod ideas: $(basename "$TARGET_IDEAS")"
        else
          warn "Target tag $CHANGE_TO has no mod ideas found"
        fi
      fi
    fi

    if echo "$DEC_BLOCK" | grep -q "adm_tech"; then
      TECH_REQ=$(echo "$DEC_BLOCK" | grep -oE 'adm_tech = [0-9]+' | head -1 | awk '{print $3}' || true)
      pass "Tech requirement: admin tech $TECH_REQ"
    fi

  else
    warn "Decision has no override_country_name or change_tag — unusual"
  fi
fi

# ═══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════
separator "SUMMARY"
echo ""
TOTAL=$((PASS + FAIL + WARN))
echo "  Total checks: $TOTAL"
echo "  ✅ Passed:     $PASS"
echo "  ❌ Failed:     $FAIL"
echo "  ⚠️  Warnings:   $WARN"
echo ""

if [ "$FAIL" -eq 0 ]; then
  echo "  🎉 ALL CHECKS PASSED for tag $TAG!"
else
  echo "  🔧 $FAIL issues need fixing for tag $TAG."
fi
echo ""
