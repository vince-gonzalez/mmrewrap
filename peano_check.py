"""Is peano.mm in rewrapped state, or is the tool wrong about it?

A greedily filled comment has a defining property: no line could take the first
unit of the next line without exceeding the margin. If peano.mm's own comments
violate that, the file was never rewrapped and the tool's divergence is the tool
being right. If they satisfy it, the tool is wrong and this PR does not happen.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from rewrap_comments import SCREEN_WIDTH, handles

CR = re.compile(r"\$\(.*?\$\)", re.S)

for path in sys.argv[1:]:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    violations = 0
    checked = 0
    examples = []
    for m in CR.finditer(text):
        ls = text.rfind("\n", 0, m.start()) + 1
        pre = text[ls:m.start()]
        block = m.group(0)
        if pre.strip() or not handles(block, len(pre),
                                      following=text[m.end():m.end() + 160]):
            continue
        lines = (pre + block).split("\n")
        if len(lines) < 2:
            continue
        checked += 1
        for i in range(len(lines) - 1):
            cur = lines[i].rstrip()
            nxt = lines[i + 1].strip()
            if not nxt:
                continue
            first = nxt.split()[0]
            # a single space is the minimum join; if even that fits, the line
            # was not filled greedily
            if len(cur) + 1 + len(first) <= SCREEN_WIDTH:
                violations += 1
                if len(examples) < 3:
                    examples.append((len(cur), cur[-58:], first))
                break
    name = Path(path).name
    verdict = ("NOT rewrapped" if violations else "consistent with rewrapped")
    print("   %-14s multi-line comments=%-6d greedy violations=%-5d  %s"
          % (name, checked, violations, verdict))
    for w, tail, nxt in examples:
        print("      line ends at %d: ...%s   | next word %r would fit" % (w, tail, nxt))
