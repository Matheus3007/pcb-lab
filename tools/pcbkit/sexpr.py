"""Minimal S-expression reader/writer for KiCad files (.kicad_sym, .kicad_sch).

Nodes are lists; atoms are `str`; quoted strings are `Q` (a str subclass) so they round-trip
with their quotes. Pure Python, no KiCad needed.
"""
from __future__ import annotations

import re

_TOKEN = re.compile(r'"((?:[^"\\]|\\.)*)"|([()])|([^\s()"]+)')


class Q(str):
    """A quoted string atom."""


def parse(text: str) -> list:
    stack: list[list] = [[]]
    for m in _TOKEN.finditer(text):
        s, paren, atom = m.groups()
        if paren == "(":
            stack.append([])
        elif paren == ")":
            node = stack.pop()
            stack[-1].append(node)
        elif s is not None:
            stack[-1].append(Q(re.sub(r"\\(.)", lambda e: {"n": "\n", "t": "\t"}.get(e[1], e[1]), s)))
        else:
            stack[-1].append(atom)
    return stack[0]


def _atom(a) -> str:
    if isinstance(a, Q):
        return '"' + a.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
    if isinstance(a, float):
        return fmt(a)
    return str(a)


def fmt(v: float) -> str:
    """Number formatting KiCad-style: up to 4 decimals, no trailing zeros, no -0."""
    s = f"{round(float(v), 4):.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def dump(node, indent: int = 0) -> str:
    """KiCad-like layout: a node on one line if it has no child lists, else children indented."""
    if not isinstance(node, list):
        return _atom(node)
    pad = "\t" * indent
    k = _first_list(node)
    if k == len(node):
        return pad + "(" + " ".join(_atom(a) for a in node) + ")"
    out = [pad + "(" + " ".join(_atom(a) for a in node[:k])]
    for c in node[k:]:
        out.append(dump(c, indent + 1) if isinstance(c, list) else "\t" * (indent + 1) + _atom(c))
    out.append(pad + ")")
    return "\n".join(out)


def _first_list(node) -> int:
    for i, c in enumerate(node):
        if isinstance(c, list):
            return i
    return len(node)


# -- queries -----------------------------------------------------------------
def head(node) -> str | None:
    return node[0] if isinstance(node, list) and node and isinstance(node[0], str) else None


def find(node, name: str) -> list | None:
    for c in node:
        if head(c) == name:
            return c
    return None


def find_all(node, name: str) -> list[list]:
    return [c for c in node if head(c) == name]


def prop(node, name: str) -> str | None:
    for c in find_all(node, "property"):
        if c[1] == name:
            return str(c[2])
    return None
