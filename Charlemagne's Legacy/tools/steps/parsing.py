#!/usr/bin/env python3
"""Reading Paradox script: key/value and block parsing, dated history blocks, the effective owner at the start date."""

import re
from functools import lru_cache
from tagdb import CTRY_DATE
from steps.layout import START_DT


def strip_dated(text):
    out, depth = [], 0
    for ln in text.splitlines():
        if re.match(r"^\s*\d+\.\d+\.\d+\s*=", ln):
            break
        out.append(ln)
        code = ln.split("#", 1)[0]
        depth += code.count("{") - code.count("}")
    while out and not out[-1].strip():
        out.pop()
    while depth > 0:
        out.append("}")
        depth -= 1
    return "\n".join(out) + "\n"


def strip_non_867(text):
    # Drop every dated block but 867.1.1: no history besides the start date.
    # Top-level fields stay (they describe the start); only dated entries go.
    out, cur, keep, depth = [], None, False, 0
    for ln in text.splitlines():
        s = ln.strip()
        if cur is None:
            m = re.match(r"^(\d+\.\d+\.\d+)\s*=", s)
            if m:
                keep = m.group(1) == CTRY_DATE
                code = ln.split("#", 1)[0]
                depth = code.count("{") - code.count("}")
                cur = [ln] if keep else []
                if depth <= 0:
                    if keep:
                        out.extend(cur)
                    cur = None
                continue
            out.append(ln)
        else:
            if keep:
                cur.append(ln)
            code = ln.split("#", 1)[0]
            depth += code.count("{") - code.count("}")
            if depth <= 0:
                if keep:
                    out.extend(cur)
                cur = None
    return "\n".join(out).strip("\n") + "\n"


@lru_cache(maxsize=None)
def parse(path):
    txt = open(path, encoding="utf-8", errors="surrogateescape").read()
    lines = []
    for ln in txt.splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        lines.append((len(ln) - len(ln.lstrip()), s))

    depth = 0
    started_dated = False
    scalars, cores0, cores_all = {}, [], []
    for _, s in lines:
        opens = s.count("{")
        closes = s.count("}")
        m = None
        if depth == 0 and not started_dated and "=" in s and not s.endswith("{"):
            m = s
        if depth == 0:
            if s.split("=")[0].strip().replace("_", "").isdigit() and "=" in s:
                started_dated = True
        if m:
            k, _, v = m.partition("=")
            k, v = k.strip(), re.split(r"#|//", v, 1)[0].strip()
            if k == "add_core":
                cores0.append(v)
                cores_all.append(v)
            else:
                scalars[k] = v
        else:
            for c in re.findall(r"add_core\s*=\s*([A-Z]{3})", s):
                cores_all.append(c)
        depth += opens - closes
        if depth < 0:
            depth = 0
    return scalars, cores0, cores_all


def parse_block_file(path):
    text = open(path, encoding="utf-8", errors="replace").read()
    blocks = []
    cur_key, cur = None, []
    depth = 0
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            if cur_key is not None:
                cur.append(line)
            continue
        if depth == 0:
            m = re.match(r"^([A-Za-z0-9_]+)\s*=\s*\{", s)
            if m:
                cur_key, cur = m.group(1), [line]
                depth = 1
                continue
        else:
            cur.append(line)
            depth += s.count("{") - s.count("}")
            if depth == 0:
                blocks.append((cur_key, cur))
                cur_key, cur = None, []
    return blocks


DATE_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)\s*=\s*\{")

KV_RE = re.compile(r"\b(owner|controller|add_core|remove_core)\s*=\s*([A-Za-z0-9_]+)")


def split_header_and_blocks(lines):
    i = 0
    n = len(lines)
    header = []
    while i < n and not DATE_RE.match(lines[i].strip()):
        header.append(lines[i])
        i += 1
    yield None, "\n".join(header)
    while i < n:
        m = DATE_RE.match(lines[i].strip())
        if not m:
            i += 1
            continue
        date = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        depth = lines[i].count("{") - lines[i].count("}")
        body = [lines[i]]
        i += 1
        while i < n and depth > 0:
            depth += lines[i].count("{") - lines[i].count("}")
            body.append(lines[i])
            i += 1
        yield date, "\n".join(body)


def effective(text):
    owner = controller = None
    cores = set()
    for date, block in split_header_and_blocks(text.splitlines()):
        if date is not None and date > START_DT:
            continue
        for key, val in KV_RE.findall(block):
            if key == "owner":
                owner = val
            elif key == "controller":
                controller = val
            elif key == "add_core":
                cores.add(val)
            elif key == "remove_core":
                cores.discard(val)
    return owner, controller, cores
