"""The test that matters: can the tool REPAIR damage, not merely leave good input alone?

Every previous check was a fixed point -- feed it a correct file, get the same
file. That proves it does no harm. It does not prove it does the job.

Every comment in set.mm and iset.mm is a known-correct output of the real
`rewrap`. So each one is a test case with a known answer: damage it in a way
rewrap is defined to repair, run the tool, and demand the original back
byte-for-byte. A single failure is a real defect.

The damages are chosen to exercise each documented stage of rewrapComment():

  unwrap        every single newline becomes a space   -> the refill
  narrow / wide re-wrapped at 55 / 70 columns          -> the margin
  squeeze       double spaces collapsed to one         -> the sentence rule
  pad           extra spaces injected between words    -> edit(...,16)
  tilde-split   a line broken between ~ and its label  -> the tilde rule

Paragraph breaks (blank lines) are preserved by every damage, because rewrap
preserves them too -- destroying them would be asking the tool to invent
structure rather than restore it.
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from rewrap_comments import COMMENT_RE, handles, rewrap_block


def unwrap(block: str, indent: int) -> str:
    """Single newlines to spaces; blank lines survive."""
    return re.sub(r"(?<!\n)\n(?!\n)[ \t]*", " ", block)


def rewrap_at(block: str, indent: int, width: int) -> str:
    """Re-flow at the wrong margin, using the tool itself as the flow engine."""
    return rewrap_block(block, indent, width=width)[indent:]


def squeeze(block: str, indent: int) -> str:
    """Collapse the two-space sentence gaps rewrap inserts."""
    return re.sub(r"(?<=[.?!:]) {2}(?=[A-Z(\['\"])", " ", block)


def pad(block: str, indent: int) -> str:
    """Extra spaces between words, which edit(...,16) removes."""
    return re.sub(r"(?<=[a-z]) (?=[a-z])", "   ", block, count=8)


def tilde_split(block: str, indent: int) -> str:
    """Break a line between a tilde and its label -- the markup-breaking case."""
    return re.sub(r"~ (\S)", lambda m: "~\n" + " " * (indent + 3) + m.group(1),
                  block, count=1)


DAMAGES = [
    ("unwrap", unwrap),
    ("narrow", lambda b, i: rewrap_at(b, i, 55)),
    ("wide", lambda b, i: rewrap_at(b, i, 70)),
    ("squeeze", squeeze),
    ("pad", pad),
    ("tilde-split", tilde_split),
]


def run(path: Path) -> tuple[int, int, Counter]:
    text = path.read_text(encoding="utf-8", errors="replace")
    cases = fails = 0
    by_damage: Counter[str] = Counter()
    examples: list[tuple[str, str, str, str]] = []

    for m in COMMENT_RE.finditer(text):
        ls = text.rfind("\n", 0, m.start()) + 1
        pre = text[ls:m.start()]
        block = m.group(0)
        if pre.strip() or not handles(block, len(pre),
                                      following=text[m.end():m.end() + 160]):
            continue
        want = pre + block
        for name, fn in DAMAGES:
            try:
                damaged = fn(block, len(pre))
            except Exception:
                continue
            if damaged == block:
                continue                       # damage did not apply; not a case
            cases += 1
            try:
                got = rewrap_block(damaged, len(pre))
            except Exception as e:
                fails += 1
                by_damage[name] += 1
                if len(examples) < 6:
                    examples.append((name, block[:60], "EXCEPTION " + repr(e), ""))
                continue
            if got != want:
                fails += 1
                by_damage[name] += 1
                if len(examples) < 6:
                    o = want.split("\n")
                    g = got.split("\n")
                    i = next((k for k in range(max(len(o), len(g)))
                              if (o[k] if k < len(o) else None)
                              != (g[k] if k < len(g) else None)), 0)
                    examples.append((name, block.split("\n")[0][:52],
                                     o[i] if i < len(o) else "(missing)",
                                     g[i] if i < len(g) else "(missing)"))

    print("   %-12s cases=%-8d failures=%-6d %s"
          % (path.name, cases, fails, "ALL REPAIRED" if not fails else "DEFECTS"))
    if by_damage:
        print("      by damage:", dict(by_damage))
    for name, sub, o, g in examples[:4]:
        print("      [%s] %s" % (name, sub))
        print("         want |%s|" % o)
        print("         got  |%s|" % g)
    return cases, fails, by_damage


total_cases = total_fails = 0
for p in sys.argv[1:]:
    c, f, _ = run(Path(p))
    total_cases += c
    total_fails += f

print()
print("   TOTAL cases=%d failures=%d" % (total_cases, total_fails))
sys.exit(1 if total_fails else 0)
