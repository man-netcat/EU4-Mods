#!/usr/bin/env python3

import codecs
import re
import unicodedata

_SPECIAL = {
    "ß": "ss",
    "ẞ": "SS",
    "ł": "l",
    "Ł": "L",
    "đ": "d",
    "Đ": "D",
    "ð": "d",
    "Ð": "D",
    "ı": "i",
    "ħ": "h",
    "Ħ": "H",
    "ŧ": "t",
    "Ŧ": "T",
    "ŋ": "n",
    "Ŋ": "N",
    "ø": "o",
    "Ø": "O",
    "ʼ": "'",
    "‘": "'",
    "’": "'",
    "“": '"',
    "”": '"',
    "–": "-",
    "—": "-",
    "…": "...",
}


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


def _encodable(s: str) -> bool:
    try:
        s.encode("cp1252")
    except UnicodeEncodeError:
        return False
    return True


def _one(ch: str) -> str:
    if _encodable(ch):
        return ch
    if ch in _SPECIAL:
        return _SPECIAL[ch]
    folded = "".join(
        c for c in unicodedata.normalize("NFKD", ch) if not unicodedata.combining(c)
    )
    if folded and _encodable(folded):
        return folded
    return ""


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


def encname(s: str) -> str:
    if s is None:
        return None
    if _encodable(s):
        return s
    out = "".join(_one(ch) for ch in s).strip()
    if not out:
        return _slug(s)
    if not _encodable(out):
        out = "".join(c for c in out if _encodable(c)) or _slug(s)
    return out
