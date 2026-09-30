"""Properties that must hold, beyond the reproduction count.

A 100% match against set.mm only proves the tool agrees with a file that is
already correct. These three checks test the things that number cannot:

  1. idempotency  - rewrapping an already-rewrapped comment changes nothing
  2. the gate can fail - a deliberately mangled comment is NOT reported as fine
  3. no line the tool emits exceeds the margin
"""
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from rewrap_comments import rewrap_block, handles, SCREEN_WIDTH

t = Path(r"C:\tmp\setmm-upstream\set.mm").read_text(encoding="utf-8", errors="replace")
CR = re.compile(r"\$\(.*?\$\)", re.S)

accepted = []
for m in CR.finditer(t):
    ls = t.rfind("\n", 0, m.start()) + 1
    pre = t[ls:m.start()]
    if pre.strip():
        continue
    b = m.group(0)
    if handles(b, len(pre), following=t[m.end():m.end() + 160]):
        accepted.append((b, len(pre)))

print("   accepted comments:", len(accepted))

# 1. idempotency
noni = 0
for b, ind in accepted:
    once = rewrap_block(b, ind)
    body = once[ind:]
    twice = rewrap_block(body, ind)
    if twice != once:
        noni += 1
print("   1. idempotent          :", "PASS" if noni == 0 else f"FAIL on {noni}")

# 2. the gate can fail -- unwrap a comment onto one line and confirm the tool
#    reports a difference. Only comments whose collapsed form EXCEEDS the margin
#    must change; one that already fits on a single line is correctly left as
#    it is, and demanding otherwise tests the wrong thing.
rng = random.Random(11)
sample = [(b, ind) for b, ind in rng.sample(accepted, 800)
          if ind + len(re.sub(r"\s*\n\s*", " ", b)) > SCREEN_WIDTH]
detected = 0
for b, ind in sample:
    mangled = re.sub(r"\s*\n\s*", " ", b)          # collapse to a single line
    out = rewrap_block(mangled, ind)
    if out != " " * ind + mangled:
        detected += 1
print("   2. detects a mangled   : %s  (%d over-long samples)"
      % ("PASS" if detected == len(sample)
         else f"FAIL {len(sample)-detected}/{len(sample)} undetected", len(sample)))

# 3. margin respected on everything it emits
over = 0
worst = 0
for b, ind in accepted:
    for line in rewrap_block(b, ind).split("\n"):
        if len(line) > SCREEN_WIDTH:
            over += 1
            worst = max(worst, len(line))
print("   3. no line over %d    : %s" % (SCREEN_WIDTH,
      "PASS" if over == 0 else f"FAIL {over} lines, worst {worst}"))
