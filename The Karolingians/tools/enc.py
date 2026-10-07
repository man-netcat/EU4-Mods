#!/usr/bin/env python3

import codecs
import re
import unicodedata
from pathlib import Path

NAMES: dict[str, str] = {}
_slug_key: dict[str, str] = {}
_used_keys: set[str] = set()

_LOC_RE = re.compile(r'^[ \t]*([\w.\-]+)\s*:\d*\s*"(.*?)"[ \t\r\n]*$', re.M)


def load_loc(path) -> int:
    text = Path(path).read_text(encoding="utf-8").lstrip("\ufeff")
    keys = 0
    for k, v in _LOC_RE.findall(text):
        if k.startswith("KC_"):
            NAMES.setdefault(k, v)
            keys += 1
    return keys


def _pdx_handler(exc: UnicodeError):
    out = bytearray()
    for ch in exc.object[exc.start : exc.end]:
        if ch == "\ufffd":
            out += b"\xef\xbf\xbd"
        elif "\udc80" <= ch <= "\udcff":
            out += bytes([ord(ch) & 0xFF])
        else:
            raise UnicodeEncodeError(
                exc.encoding, exc.object, exc.start, exc.end, "unencodable"
            )
    return bytes(out), exc.end


codecs.register_error("pdx", _pdx_handler)


def encname(s: str) -> str:
    try:
        s.encode("cp1252")
    except UnicodeEncodeError:
        pass
    else:
        return s
    if s in _slug_key:
        return _slug_key[s]
    key = _fresh_key(s)
    _slug_key[s] = key
    _used_keys.add(key)
    NAMES[key] = s
    return key


def decode(s: str) -> str:
    if s is None:
        return None
    return NAMES.get(s, s)


def _slug(s: str) -> str:
    out = []
    for ch in unicodedata.normalize("NFKD", s):
        if unicodedata.combining(ch):
            continue
        if ch.isalnum() and ch.isascii():
            out.append(ch)
    base = re.sub(r"\W", "_", "".join(out)) or "Name"
    if base[0].isdigit():
        base = "N" + base
    return base


def _fresh_key(s: str) -> str:
    base = _slug(s)
    key = base
    i = 1
    while key in _used_keys:
        key = f"{base}_{i}"
        i += 1
    return "KC_" + key


def names_loc_body() -> str:
    return "\n".join(f' {k}:0 "{v}"' for k, v in sorted(NAMES.items()))
