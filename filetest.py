"""File-level test: run the tool over a whole database and diff the bytes.

Every previous measurement was per-comment. This is the test that matters for a
contributor: they run the tool on a 51MB file that is ALREADY correctly wrapped,
and the file must come out byte-identical. Anything else is corruption.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from rewrap_comments import COMMENT_RE, handles, rewrap_block


def rewrap_text(text: str) -> tuple[str, int, int, list[str]]:
    out, pos, done, refused, names = [], 0, 0, 0, []
    for m in COMMENT_RE.finditer(text):
        out.append(text[pos:m.start()])
        ls = text.rfind("\n", 0, m.start()) + 1
        prefix = text[ls:m.start()]
        block = m.group(0)
        following = text[m.end():m.end() + 160]
        if prefix.strip() or not handles(block, len(prefix), following=following):
            out.append(block)
            refused += 1
        else:
            new = rewrap_block(block, len(prefix))[len(prefix):]
            out.append(new)
            done += 1
            if new != block:
                names.append(block.split("\n")[0][:50])
        pos = m.end()
    out.append(text[pos:])
    return "".join(out), done, refused, names


for path in sys.argv[1:]:
    p = Path(path)
    if not p.exists():
        print(f"   {p.name:12} MISSING")
        continue
    raw = p.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    result, done, refused, changed = rewrap_text(text)
    same = result == text
    print("   %-12s %10d bytes  processed=%-6d refused=%-5d  IDENTICAL=%s"
          % (p.name, len(raw), done, refused, same))
    if not same:
        # locate the first divergence precisely
        n = min(len(result), len(text))
        i = next((k for k in range(n) if result[k] != text[k]), n)
        line = text.count("\n", 0, i) + 1
        print(f"      first divergence at char {i}, line {line}")
        print("      original:", repr(text[max(0, i - 60):i + 60]))
        print("      produced:", repr(result[max(0, i - 60):i + 60]))
        print(f"      length {len(text)} -> {len(result)}")
        print(f"      comments it CHANGED: {len(changed)}")
        for c in changed[:5]:
            print("        ", c)
