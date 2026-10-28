"""Minimal Paradox script parser -> list of (key, value) pairs; value is str or nested pair list."""
import re

TOK = re.compile(r'"[^"]*"|[{}=<>]=?|[^\s{}=<>"#]+|#[^\n]*')


def parse(text):
    toks = [t for t in TOK.findall(text.lstrip("﻿")) if not t.startswith("#")]
    pos = 0

    def block():
        nonlocal pos
        items = []
        while pos < len(toks):
            t = toks[pos]
            if t == "}":
                pos += 1
                return items
            pos += 1
            if t == "{":
                items.append((None, block()))
            elif pos < len(toks) and toks[pos] in ("=", "<", ">", "<=", ">="):
                op = toks[pos]
                pos += 1
                if toks[pos] == "{":
                    pos += 1
                    items.append((t, block()))
                else:
                    items.append((t, toks[pos].strip('"')))
                    pos += 1
            else:
                items.append((None, t.strip('"')))
        return items

    return block()


def get(items, key, default=None):
    return next((v for k, v in items if k == key), default)


def getall(items, key):
    return [v for k, v in items if k == key]
