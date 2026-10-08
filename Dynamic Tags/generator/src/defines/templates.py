"""EU4 event and decision templates for the Dynamic Tags Generator.

This module contains all the EU4-specific template strings used to generate
game files (events, decisions, etc.).
"""

EVENT_SCRIPT_HEADER = """\
### generated events for dynamic tags

namespace = {event_name}

country_event = {{
    id = {event_name}.0
    hidden = yes
    is_triggered_only = yes
    title = "DUMMY"
    desc = "DUMMY"
    picture = TRADE_GOODS_FURS_FISH_AND_SALT_eventPicture

    immediate = {{
{event_triggers}
    }}

    option = {{
        name = {event_name}.0.a
    }}
}}
"""

TAG_DEPENDANT_EVENT_TEMPLATE = """\
country_event = {{
    id = {event_name}.{id}
    hidden = yes
    is_triggered_only = yes
    title = "DUMMY"
    desc = "DUMMY"
    picture = TRADE_GOODS_FURS_FISH_AND_SALT_eventPicture

    trigger = {{
        {tag_limit}
    }}

    immediate = {{
{conditions}
    }}

    option = {{
        name = {event_name}.{id}.a
    }}
}}
"""

DECISION_TEMPLATE = """\
country_decisions = {{
    update_{event_name}_decision = {{
        potential = {{ always = yes }}
        allow = {{ always = yes }}
        ai_will_do = {{ factor = 0 }}
        effect = {{ country_event = {{ id = {event_name}.0 }} }}
    }}
}}
"""

MASTER_EVENT_TEMPLATE = """\
### master dispatcher event for dynamic tags

namespace = {event_name}

country_event = {{
    id = {event_name}.0
    hidden = yes
    is_triggered_only = yes
    title = "DUMMY"
    desc = "DUMMY"
    picture = TRADE_GOODS_FURS_FISH_AND_SALT_eventPicture

    immediate = {{
{module_triggers}
    }}

    option = {{
        name = {event_name}.0.a
    }}
}}
"""
