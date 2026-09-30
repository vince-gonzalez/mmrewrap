#!/usr/bin/env python3
"""Rewrap Metamath comments exactly as `metamath 'write source /rewrap'` does.

`scripts/rewrap` shells out to the C `metamath` executable. A contributor
without a build cannot rewrap, so comments get wrapped by hand and reviewers ask
for it again.

This is a transcription of `rewrapComment()` in `mmpars.c` plus the line-break
loop of `printLongLine()` in `mminou.c`, not an inference from examples. It is
checked against every comment in set.mm, which CONTRIBUTING.md states CI keeps
in rewrapped state.
"""
from __future__ import annotations

import re

SCREEN_WIDTH = 79
NB = "\x04"                                   # ASCII_4: a space that cannot break

OPENING_PUNCTUATION = "(['\""
CLOSING_PUNCTUATION = ".,;)?!:]'\""
SENTENCE_END_PUNCTUATION = ")'\""

PROOF_DISCOURAGED_MARKUP = "(Proof modification is discouraged.)"
USAGE_DISCOURAGED_MARKUP = "(New usage is discouraged.)"


def _space_surround(s: str, ch: str, math_exception: bool = False) -> str:
    """Ensure every unescaped `ch` has a space on both sides (mmpars.c).

    `math_exception` reproduces the backtick carve-out documented in the C: a
    CLOSING backtick followed by `_` or `-` gets no space, because ``` ` a ` _2 ```
    does not render as a subscript while ``` ` a `_2 ``` does.
    """
    out = list(s)
    i = 1
    mathmode = 0
    while i < len(out) - 1:
        if out[i] != ch:
            i += 1
            continue
        if out[i - 1] == ch or (i + 1 < len(out) and out[i + 1] == ch):
            i += 2                             # `` or ~~ escape
            continue
        mathmode = 1 - mathmode
        nxt = out[i + 1] if i + 1 < len(out) else ""
        if nxt not in (" ", "\n", ""):
            if not math_exception or mathmode == 1 or nxt not in ("_", "-"):
                out.insert(i + 1, " ")
        if out[i - 1] != " ":
            out.insert(i, " ")
            i += 1
        i += 1
    return "".join(out)


def _two_spaces_after_sentences(c: str) -> str:
    """Two spaces after . ? ! : -- under the exact guard mmpars.c uses."""
    for ch in ".?!:":
        i = 1
        while True:
            p = c.find(ch, i)
            if p < 0:
                break
            i = p + 1
            if ch == "." and p > 0 and "A" <= c[p - 1] <= "Z":
                continue                       # initials of names: "J. Smith"
            q = p + 1
            if q < len(c) and c[q] in SENTENCE_END_PUNCTUATION:
                q += 1
            if q >= len(c) or c[q] != " ":
                continue
            nxt = c[q + 1] if q + 1 < len(c) else ""
            if ("A" <= nxt <= "Z") or (nxt and nxt in OPENING_PUNCTUATION):
                c = c[:q + 1] + " " + c[q + 1:]
                i = q + 2
    return c


def _mark_nonbreaking(c: str) -> str:
    """Build mmpars.c's template of spaces that must not become line breaks."""
    n = len(c)
    tmpl = [" "] * n
    for p in range(2, n - 2):
        if c[p] != " ":
            continue
        if c[p - 1] == "~" and c[p - 2] != "~":
            tmpl[p] = NB                                   # "~ label"
        elif (c[p - 2] == " " or c[p - 2] in OPENING_PUNCTUATION) \
                and c[p - 1] in OPENING_PUNCTUATION:
            tmpl[p] = NB                                   # after "(" etc.
        elif (p + 2 < n
              and (c[p + 2] == " " or c[p + 2] == "\n" or c[p + 2] == NB
                   or c[p + 2] in CLOSING_PUNCTUATION)
              and c[p + 1] in CLOSING_PUNCTUATION):
            tmpl[p] = NB                                   # before ")" etc.
        elif c[p - 3] == " " and c[p - 2] == "p" and c[p - 1] == ".":
            tmpl[p] = NB                                   # " p. 49"
    if n >= 3:
        tmpl[n - 3] = NB                                   # the space before "$)"
    return "".join(NB if tmpl[p] == NB else c[p] for p in range(n))


def normalize(comment: str) -> str:
    """Everything rewrapComment() does before the line breaking."""
    c = comment
    c = _space_surround(c, "`", math_exception=True)
    if "`" not in c[1:]:
        c = _space_surround(c, "~")

    # newlines become spaces unless doubled (a blank line is a paragraph break)
    body = list(c)
    for p in range(2, len(body) - 2):
        if body[p] == "\n" and body[p - 1] != "\n" and body[p + 1] != "\n":
            body[p] = " "
    c = "".join(body)
    c = re.sub(r"  +", " ", c)                            # edit(...,16)

    while len(c) >= 4 and (c[-4] == " " or c[-4] == "\n"):
        c = c[:-4] + c[-2:]
    if len(c) >= 4 and c[-4].islower():
        c = c[:-3] + ". $)"

    # spaces inside math mode never break
    out, math = [], False
    for p, chx in enumerate(c):
        if chx == "`":
            math = not math
        out.append(NB if (math and chx == " " and 2 <= p < len(c) - 2) else chx)
    c = "".join(out)

    for markup in (PROOF_DISCOURAGED_MARKUP, USAGE_DISCOURAGED_MARKUP):
        p = c.find(markup)
        if p >= 0:
            c = c[:p] + markup.replace(" ", NB) + c[p + len(markup):]

    c = _two_spaces_after_sentences(c)
    return _mark_nonbreaking(c)


def wrap(text: str, first_prefix: str, cont_prefix: str,
         width: int = SCREEN_WIDTH) -> list[str]:
    """printLongLine()'s loop: scan back from column width+1 for a break space.

    When no breakable space exists at or before the limit the line overflows,
    which is how long URLs survive intact.
    """
    lines: list[str] = []
    line = first_prefix + text
    first = True
    while len(line) > width:
        p = width                                  # index just past the limit
        while p > 0 and line[p] != " ":
            p -= 1
        if p <= len(first_prefix if first else cont_prefix):
            # nothing breakable at or before the limit -- a long URL. metamath
            # widens the margin until the token fits rather than splitting it,
            # so take the next space AFTER the limit and carry on.
            q = line.find(" ", width)
            if q < 0:
                break
            p = q
        lines.append(line[:p].rstrip(" " + NB))
        line = cont_prefix + line[p + 1:].lstrip()
        first = False
    lines.append(line.rstrip(" " + NB))
    return lines


def rewrap_block(block: str, indent: int, width: int = SCREEN_WIDTH) -> str:
    """Rewrap one `$( ... $)` comment whose `$(` sits at column `indent`."""
    if not (block.startswith("$(") and block.endswith("$)")):
        raise ValueError("not a comment block")
    c = normalize(block)
    pad = " " * indent
    paragraphs = c.split("\n\n")
    outs: list[str] = []
    for k, para in enumerate(paragraphs):
        # mmpars.c strips the leading spaces after every newline before adding
        # `indent + 3`; leaving them makes each later paragraph one column deep
        body = para.strip("\n").lstrip(" ")
        # only the first paragraph carries the `$( `; the rest resume at the
        # continuation indent, which is where `$( ` would have put them
        pre = pad if k == 0 else pad + "   "
        lines = wrap(body, pre, pad + "   ", width)
        outs.append("\n".join(lines))
    return "\n\n".join(outs).replace(NB, " ")


COMMENT_RE = re.compile(r"\$\(.*?\$\)", re.S)


STATEMENT_FOLLOWS = re.compile(r"\s*[A-Za-z0-9_.\-]+\s+\$[ap]\s")


def handles(block: str, indent: int = 0, width: int = SCREEN_WIDTH,
            following: str | None = None) -> bool:
    """Whether this implementation reproduces `rewrap` for this comment.

    Two refusals, both mechanical rather than guessed:

    * metamath itself leaves a comment containing the literal ``<HTML>`` alone.
    * A run of characters that cannot be broken -- in practice ``~`` followed by
      a long URL, since the space after a tilde is non-breaking -- does not fit
      the margin. metamath widens the margin for those; that path is not
      modelled here, so the comment is returned untouched instead of guessed at.

    Refusing is the point. A rewrap tool that reformats a comment it does not
    understand is worse than one that admits the gap.
    """
    if "<HTML>" in block:
        return False
    if following is not None and not STATEMENT_FOLLOWS.match(following):
        # The rewrapping block in mmpars.c `outputStatement` lives inside the
        # `$a`/`$p` case and ends `break; // End of $a, $p cases`. A comment not
        # attached to a statement -- a file header, a section banner -- is never
        # reflowed by metamath, so reflowing it here would be a false edit.
        return False
    budget = width - indent - 3
    for run in normalize(block).replace(NB, "\x00").split(" "):
        if len(run.replace("\x00", " ").strip()) > budget:
            return False
    return True
