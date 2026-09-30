"""Final verification: does the tool reproduce `rewrap` on everything it accepts?

Reports, for each population, how many comments it accepts and whether every
accepted comment round-trips byte-identically. Anything less than 100% on the
accepted set means the refusal gate is not tight enough.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from rewrap_comments import rewrap_block, handles

t = Path(r"C:\tmp\setmm-upstream\set.mm").read_text(encoding="utf-8", errors="replace")
CR = re.compile(r"\$\(.*?\$\)", re.S)
NEXT = re.compile(r"\s*[A-Za-z0-9_.\-]+\s+\$[ap]\s")
DECOR = re.compile(r"[#*=\-]{8,}")

pops = {"statement": [0, 0, 0], "section header": [0, 0, 0], "other": [0, 0, 0]}
bad = []

for m in CR.finditer(t):
    ls = t.rfind("\n", 0, m.start()) + 1
    pre = t[ls:m.start()]
    block = m.group(0)
    if pre.strip():
        continue
    if DECOR.search(block):
        k = "section header"
    elif NEXT.match(t[m.end():m.end() + 160]):
        k = "statement"
    else:
        k = "other"
    pops[k][0] += 1
    if not handles(block, len(pre), following=t[m.end():m.end() + 160]):
        pops[k][2] += 1
        continue
    if rewrap_block(block, len(pre)) == pre + block:
        pops[k][1] += 1
    elif len(bad) < 5:
        bad.append((k, pre + block))

print("   %-16s %8s %9s %9s %9s" % ("population", "total", "accepted", "exact", "refused"))
for k, (tot, ok, ref) in pops.items():
    acc = tot - ref
    pct = 100.0 * ok / acc if acc else 0.0
    print("   %-16s %8d %9d %9d %9d   %.4f%%" % (k, tot, acc, ok, ref, pct))

gtot = sum(v[0] for v in pops.values())
gok = sum(v[1] for v in pops.values())
gref = sum(v[2] for v in pops.values())
gacc = gtot - gref
print()
print("   ALL              %8d %9d %9d %9d   %.4f%%"
      % (gtot, gacc, gok, gref, 100.0 * gok / gacc if gacc else 0.0))
if bad:
    print()
    print("   accepted but NOT reproduced (gate too loose):")
    for k, f in bad[:3]:
        print("   [%s] %s" % (k, f.split("\n")[0][:90]))
