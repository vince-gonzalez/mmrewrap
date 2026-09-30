"""What do the last mismatching statement comments have in common?"""
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from rewrap_comments import rewrap_block, handles

t = Path(r"C:\tmp\setmm-upstream\set.mm").read_text(encoding="utf-8", errors="replace")
CR = re.compile(r"\$\(.*?\$\)", re.S)
NEXT = re.compile(r"\s*[A-Za-z0-9_.\-]+\s+\$[ap]\s")
DECOR = re.compile(r"[#*=\-]{8,}")

kinds = Counter()
shown = 0
for m in CR.finditer(t):
    ls = t.rfind("\n", 0, m.start()) + 1
    pre = t[ls:m.start()]
    block = m.group(0)
    if pre.strip() or not handles(block) or DECOR.search(block):
        continue
    if not NEXT.match(t[m.end():m.end() + 160]):
        continue
    got = rewrap_block(block, len(pre))
    full = pre + block
    if got == full:
        continue

    o, g = full.split("\n"), got.split("\n")
    i = next((k for k in range(max(len(o), len(g)))
              if (o[k] if k < len(o) else None) != (g[k] if k < len(g) else None)), 0)
    ol = o[i] if i < len(o) else ""
    gl = g[i] if i < len(g) else ""
    if "  " in ol and "  " not in gl:
        kinds["original has a double space mine lacks"] += 1
    elif "  " in gl and "  " not in ol:
        kinds["mine has a double space original lacks"] += 1
    elif len(ol) < len(gl):
        kinds["original breaks earlier"] += 1
    else:
        kinds["original breaks later"] += 1
    if shown < 4 and len(ol) != len(gl):
        print("   ---")
        print("   orig %3d|%s" % (len(ol), ol))
        print("   mine %3d|%s" % (len(gl), gl))
        shown += 1

print()
for k, v in kinds.most_common():
    print("   %5d  %s" % (v, k))
print("   total  %d" % sum(kinds.values()))
