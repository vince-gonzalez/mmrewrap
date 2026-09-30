"""Where do the remaining mismatches live?

A contributor rewraps the comment attached to the theorem they edited. That is
the population that matters; file headers and section decorations are edited by
maintainers and are a different animal.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from rewrap_comments import rewrap_block, handles

t = Path(r"C:\tmp\setmm-upstream\set.mm").read_text(encoding="utf-8", errors="replace")
CR = re.compile(r"\$\(.*?\$\)", re.S)
# a statement comment is immediately followed by `label $a` or `label $p`
NEXT = re.compile(r"\s*[A-Za-z0-9_.\-]+\s+\$[ap]\s")
DECOR = re.compile(r"[#*=\-]{8,}")

buckets = {"statement": [0, 0], "section header": [0, 0], "other": [0, 0]}

for m in CR.finditer(t):
    ls = t.rfind("\n", 0, m.start()) + 1
    pre = t[ls:m.start()]
    block = m.group(0)
    if pre.strip() or not handles(block):
        continue
    if DECOR.search(block):
        kind = "section header"
    elif NEXT.match(t[m.end():m.end() + 160]):
        kind = "statement"
    else:
        kind = "other"
    ok = rewrap_block(block, len(pre)) == pre + block
    buckets[kind][0] += 1
    buckets[kind][1] += ok

for k, (n, s) in buckets.items():
    print("   %-16s %6d comments   identical %6d   %.3f%%"
          % (k, n, s, 100.0 * s / n if n else 0.0))
