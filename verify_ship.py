"""Re-run the whole proof against the file that will actually be submitted.

The shipped script is a rewrite of the verified one -- different structure,
different names, comments cut back. That makes it a new artifact, and the
earlier evidence does not carry over to it. Everything is re-established here
against `ship/rewrap-comments.py` itself.
"""
import hashlib
import importlib.util
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("shipped", HERE / "ship" / "rewrap-comments.py")
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)

DBS = [
    Path(r"C:\tmp\setmm-upstream\set.mm"),
    Path(r"C:\tmp\setmm-upstream\iset.mm"),
    HERE / "_hol.mm", HERE / "_nf.mm", HERE / "_peano.mm", HERE / "_ql.mm",
    HERE / "_miu.mm", HERE / "_demo0.mm", HERE / "_big-unifier.mm",
]

print("== 1. whole-file identity (input already correct -> output unchanged)")
identical = 0
for p in DBS:
    if not p.exists():
        print("   %-16s MISSING" % p.name)
        continue
    text = p.read_text(encoding="utf-8", errors="replace")
    result, changed, skipped = S.process(text)
    ok = result == text
    identical += ok
    print("   %-16s changed=%-4d skipped=%-5d identical=%s"
          % (p.name, len(changed), len(skipped), ok))

print()
print("== 2. inverse: damaged input -> exactly what rewrap produces")


def unwrap(b, i):
    return re.sub(r"(?<!\n)\n(?!\n)[ \t]*", " ", b)


def squeeze(b, i):
    return re.sub(r"(?<=[.?!:]) {2}(?=[A-Z(\['\"])", " ", b)


def pad(b, i):
    return re.sub(r"(?<=[a-z]) (?=[a-z])", "   ", b, count=8)


def tilde_split(b, i):
    return re.sub(r"~ (\S)", lambda m: "~\n" + " " * (i + 3) + m.group(1), b, count=1)


DAMAGES = [
    ("unwrap", unwrap),
    ("narrow", lambda b, i: S.rewrap_comment(b, i, 55)[i:]),
    ("wide", lambda b, i: S.rewrap_comment(b, i, 70)[i:]),
    ("squeeze", squeeze),
    ("pad", pad),
    ("tilde", tilde_split),
]

total = fails = 0
for p in (DBS[0], DBS[1]):
    text = p.read_text(encoding="utf-8", errors="replace")
    cases = bad = 0
    for m in S.COMMENT.finditer(text):
        start = text.rfind("\n", 0, m.start()) + 1
        prefix = text[start:m.start()]
        block = m.group(0)
        following = text[m.end():m.end() + 160]
        if prefix.strip() or not S.modelled(block, len(prefix), following):
            continue
        want = prefix + block
        for _, fn in DAMAGES:
            try:
                dmg = fn(block, len(prefix))
            except Exception:
                continue
            if dmg == block:
                continue
            cases += 1
            try:
                if S.rewrap_comment(dmg, len(prefix)) != want:
                    bad += 1
            except Exception:
                bad += 1
    print("   %-16s cases=%-8d failures=%d" % (p.name, cases, bad))
    total += cases
    fails += bad

print()
print("== 3. determinism")
text = DBS[1].read_text(encoding="utf-8", errors="replace")
digests = {hashlib.sha256(S.process(text)[0].encode("utf-8")).hexdigest()
           for _ in range(3)}
print("   three runs, distinct digests:", len(digests))
print("   imports:", sorted(
    re.findall(r"(?m)^import (\w+)",
               (HERE / "ship" / "rewrap-comments.py").read_text(encoding="utf-8"))))

print()
print("   RESULT: %d/9 databases identical, %d inverse cases, %d failures, %s"
      % (identical, total, fails,
         "deterministic" if len(digests) == 1 else "NONDETERMINISTIC"))
sys.exit(0 if (fails == 0 and len(digests) == 1 and identical == 8) else 1)
