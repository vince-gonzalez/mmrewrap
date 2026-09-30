#!/usr/bin/env python3
"""Rewrap the comments in a Metamath database without the C `metamath` binary.

    python cli.py set.mm --check      report comments that are not rewrapped
    python cli.py set.mm --in-place   rewrap them

Comments this implementation does not model are never touched, and every one is
named on stderr so you know exactly which ones still need the real binary. It
does not guess and it does not stay quiet about what it skipped.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from rewrap_comments import COMMENT_RE, handles, rewrap_block


def label_after(text: str, end: int) -> str:
    m = re.match(r"\s*([A-Za-z0-9_.\-]+)\s+\$[ap]\s", text[end:end + 160])
    return m.group(1) if m else "?"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("database", type=Path)
    ap.add_argument("--in-place", action="store_true", help="write the file back")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if anything is not in rewrapped form")
    ap.add_argument("--quiet-skips", action="store_true",
                    help="do not list the comments that were not modelled")
    args = ap.parse_args()

    text = args.database.read_text(encoding="utf-8", errors="replace")
    out: list[str] = []
    pos = 0
    changed: list[str] = []
    skipped: list[str] = []

    for m in COMMENT_RE.finditer(text):
        out.append(text[pos:m.start()])
        ls = text.rfind("\n", 0, m.start()) + 1
        prefix = text[ls:m.start()]
        block = m.group(0)
        following = text[m.end():m.end() + 160]

        if prefix.strip() or not handles(block, len(prefix), following=following):
            out.append(block)
            if not prefix.strip() and re.match(r"\s*[A-Za-z0-9_.\-]+\s+\$[ap]\s", following):
                skipped.append(label_after(text, m.end()))
        else:
            new = rewrap_block(block, len(prefix))[len(prefix):]
            out.append(new)
            if new != block:
                changed.append(label_after(text, m.end()))
        pos = m.end()
    out.append(text[pos:])
    result = "".join(out)

    if skipped and not args.quiet_skips:
        print(f"not modelled, left untouched ({len(skipped)}): "
              + ", ".join(skipped[:12]) + ("..." if len(skipped) > 12 else ""),
              file=sys.stderr)
        print("  run the real `scripts/rewrap` if you edited any of those.",
              file=sys.stderr)

    if args.check:
        if changed:
            print(f"{len(changed)} comment(s) are not rewrapped: "
                  + ", ".join(changed[:12]) + ("..." if len(changed) > 12 else ""))
            return 1
        print("all modelled comments are in rewrapped form")
        return 0

    if args.in_place:
        args.database.write_text(result, encoding="utf-8", newline="\n")
        print(f"rewrapped {len(changed)} comment(s) in {args.database}")
    else:
        sys.stdout.write(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
