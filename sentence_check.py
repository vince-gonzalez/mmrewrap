"""Was this database produced by metamath's rewrap?

rewrap unconditionally puts TWO spaces after `.`/`?`/`!`/`:` when the next
character is a capital or opening punctuation, skipping a `.` preceded by a
capital ("J. Smith"). A rewrapped file therefore cannot hold a single space in
that position inside a comment rewrap actually processes.

Three things this has to exclude, each of which made an earlier version report
set.mm itself as "not rewrapped":

  * comments rewrap never touches -- file headers, section banners, $t blocks;
  * gaps that are line breaks rather than spaces;
  * ` math ` regions, because Metamath's negation symbol is `-.` and `. (`
    occurs constantly inside formulas without ending a sentence.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from rewrap_comments import handles

CR = re.compile(r"\$\(.*?\$\)", re.S)
SINGLE = re.compile(r"(?<![A-Z])([.?!:]) ([A-Z(\['\"])")
MASK = ""


def mask_math(block: str) -> str:
    out = []
    inmath = False
    for ch in block:
        if ch == "`":
            inmath = not inmath
            out.append(ch)
        elif inmath:
            out.append(MASK)
        else:
            out.append(ch)
    return "".join(out)


for path in sys.argv[1:]:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    hits: list[str] = []
    total = 0
    for m in CR.finditer(text):
        block = m.group(0)
        ls = text.rfind("\n", 0, m.start()) + 1
        pre = text[ls:m.start()]
        if pre.strip() or not handles(block, len(pre),
                                      following=text[m.end():m.end() + 160]):
            continue
        total += 1
        scan = mask_math(block)
        for s in SINGLE.finditer(scan):
            if "\n" in block[max(0, s.start() - 1):s.end() + 1]:
                continue
            hits.append(block[max(0, s.start() - 46):s.end() + 10].replace("\n", " "))

    name = Path(path).name
    verdict = "consistent with rewrapped" if not hits else "NOT rewrapped"
    print("   %-16s statement comments=%-6d violations=%-5d %s"
          % (name, total, len(hits), verdict))
    for h in hits[:3]:
        print("      ...%s" % h)
