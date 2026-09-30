#!/usr/bin/env python3
"""Reflow every comment in set.mm and require byte-identical output.

set.mm is the oracle: every comment in it has already been through the real
`metamath ... /rewrap`, so any rule this implementation gets wrong shows up as a
mismatch. The mismatch set is the specification.
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from rewrap_comments import rewrap_block  # noqa: E402

SETMM = Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\tmp\setmm-upstream\set.mm")
COMMENT_RE = re.compile(r"\$\(.*?\$\)", re.S)

text = SETMM.read_text(encoding="utf-8", errors="replace")
print(f"database: {SETMM}  {len(text):,} bytes")

total = same = skipped = 0
fails: list[tuple[str, str, int]] = []

for m in COMMENT_RE.finditer(text):
    line_start = text.rfind("\n", 0, m.start()) + 1
    prefix = text[line_start:m.start()]
    if prefix.strip():
        skipped += 1
        continue
    original_full = prefix + m.group(0)
    if "\n" not in original_full:
        # single-line comments are only interesting if they COULD have been
        # longer; a greedy filler must leave them alone
        pass
    total += 1
    got = rewrap_block(m.group(0), len(prefix))
    if got == original_full:
        same += 1
    elif len(fails) < 4000:
        fails.append((original_full, got, len(prefix)))

pct = 100.0 * same / total if total else 0.0
print(f"comments compared : {total:,}")
print(f"byte-identical    : {same:,}  ({pct:.3f}%)")
print(f"mismatched        : {total - same:,}")
print(f"skipped (inline)  : {skipped:,}")

if fails:
    # classify the first divergent line of each failure
    kinds: Counter[str] = Counter()
    for orig, got, ind in fails:
        o = orig.split("\n")
        g = got.split("\n")
        i = next((k for k in range(max(len(o), len(g)))
                  if (o[k] if k < len(o) else None) != (g[k] if k < len(g) else None)), 0)
        ol = o[i] if i < len(o) else ""
        gl = g[i] if i < len(g) else ""
        if len(o) != len(g):
            kinds["line count differs"] += 1
        elif ol.rstrip() == gl.rstrip():
            kinds["trailing whitespace"] += 1
        elif ol.lstrip() == gl.lstrip():
            kinds["indentation"] += 1
        elif "`" in ol or "`" in gl:
            kinds["math string (backticks)"] += 1
        elif "~" in ol or "~" in gl:
            kinds["label reference (~)"] += 1
        elif "  " in ol or "  " in gl:
            kinds["double space"] += 1
        else:
            kinds["other"] += 1
    print()
    print("failure classes:")
    for k, n in kinds.most_common():
        print(f"   {n:6}  {k}")
    print()
    print("first 3 mismatches:")
    for orig, got, ind in fails[:3]:
        print("   --- original")
        for l in orig.split("\n")[:6]:
            print(f"   {len(l):3}|{l}")
        print("   --- produced")
        for l in got.split("\n")[:6]:
            print(f"   {len(l):3}|{l}")
        print()
