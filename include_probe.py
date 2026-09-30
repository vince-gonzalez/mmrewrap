"""Does the file-inclusion command break the script's statement detection?

wlammen's review point on #5456. Two questions:
  1. do the shipped databases actually use `$[ file $]`?
  2. if an include sits between a comment and its statement, what does the
     script do -- skip it, or misclassify and reflow something it shouldn't?

The second is the one that matters: skipping is safe, misclassifying is not.
"""
import importlib.util
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location(
    "s", r"C:\tmp\setmm-upstream\scripts\rewrap-comments.py")
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)

INCLUDE = re.compile(r"\$\[.*?\$\]", re.S)

print("== 1. do the databases use includes?")
for p in [Path(r"C:\tmp\setmm-upstream\set.mm"),
          Path(r"C:\tmp\setmm-upstream\iset.mm"),
          HERE / "_hol.mm", HERE / "_nf.mm", HERE / "_peano.mm",
          HERE / "_ql.mm", HERE / "_miu.mm", HERE / "_demo0.mm",
          HERE / "_big-unifier.mm"]:
    if not p.exists():
        continue
    t = p.read_text(encoding="utf-8", errors="replace")
    # a real include is outside comments; blank comments first
    masked = re.sub(r"\$\(.*?\$\)", lambda m: " " * len(m.group(0)), t, flags=re.S)
    hits = INCLUDE.findall(masked)
    print("   %-16s includes: %d %s" % (p.name, len(hits),
                                        [h[:40] for h in hits[:2]]))

print()
print("== 2. an include between a comment and its statement")
sample = (
    "$( A comment that is much too long to sit on a single line and therefore "
    "has to be wrapped by the tool under test. $)\n"
    "$[ other.mm $]\n"
    "  mylabel $p |- ph $= ? $.\n")
for m in S.COMMENT.finditer(sample):
    start = sample.rfind("\n", 0, m.start()) + 1
    prefix = sample[start:m.start()]
    following = sample[m.end():m.end() + 160]
    modelled = S.modelled(m.group(0), len(prefix), following)
    print("   following text : %r" % following.split("\n")[0][:40])
    print("   STATEMENT match: %s" % bool(S.STATEMENT.match(following)))
    print("   modelled()     : %s" % modelled)
    print("   -> %s" % ("REFLOWED (unsafe)" if modelled
                        else "left alone (safe)"))

print()
print("== 3. and with no include, the same comment")
sample2 = sample.replace("$[ other.mm $]\n", "")
for m in S.COMMENT.finditer(sample2):
    start = sample2.rfind("\n", 0, m.start()) + 1
    prefix = sample2[start:m.start()]
    following = sample2[m.end():m.end() + 160]
    print("   modelled(): %s -> %s"
          % (S.modelled(m.group(0), len(prefix), following),
             "reflowed" if S.modelled(m.group(0), len(prefix), following)
             else "left alone"))
