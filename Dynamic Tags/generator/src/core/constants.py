"""Configuration constants for the EU4 Dynamic Tags Generator.

This module contains all configuration constants that control the behavior
of the dynamic tags generation process.
"""

from ..defines import EVENT_NAME

# Game event triggers that should trigger dynamic tag updates
ON_ACTION_TRIGGERS = [
    "on_bi_yearly_pulse",
    "on_country_creation",
    "on_country_released",
    "on_government_change",
    "on_monarch_death",
    "on_native_change_government",
    "on_primary_culture_changed",
    "on_reform_changed",
    "on_reform_enacted",
    "on_religion_change",
    "on_startup",
]

# Global localisation keys for the decision system
GLOBAL_DECISION_KEYS = {
    "title": f'update_{EVENT_NAME}_decision_title:0 "Update Dynamic Tags"',
    "desc": f'update_{EVENT_NAME}_decision_desc:0 "Force update dynamic tags (e.g. after a government change). Happens automatically every 2 in-game years."',
    "tooltip": f'update_{EVENT_NAME}_decision_tooltip:0 "Force update dynamic tags (e.g. after a government change)."',
}

# Tags the game engine or the wiki reserves; never allocate these
RESERVED_TAGS = frozenset(
    {
        "ADD",
        "ADM",
        "AND",
        "ART",
        "AUX",
        "CAV",
        "CON",
        "DIP",
        "INF",
        "MIL",
        "NOT",
        "NUL",
        "PRN",
        "RGB",
        "SUM",
        "VAL",
    }
)

# Default file encoding for localisation files
LOCALISATION_ENCODING = "utf-8-sig"

# Default file encoding for other files
DEFAULT_ENCODING = "utf-8"
