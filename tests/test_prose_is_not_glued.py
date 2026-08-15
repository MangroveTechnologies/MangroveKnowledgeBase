"""Prose split across source lines keeps its spaces.

Python concatenates adjacent string literals with nothing between them, so a sentence wrapped for
line length loses the space at every wrap unless one is written in. The result reads almost right --
"the spreadactually paid", "Itexists to reduce" -- and it lands in node summaries, in the rendered
graph and in the published package, where nothing else looks at it again. 195 of these shipped in
the chapter-one prose before this test existed.

Only sentences are checked. A literal with no whitespace and operator punctuation is a regex or a
line of JavaScript, where the missing space is the point.
"""
from __future__ import annotations

import io
import subprocess
import tokenize
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def looks_like_code(text: str) -> bool:
    return " " not in text and any(c in text for c in "|;={}()<>")


def is_glued(left: str, right: str) -> bool:
    if not left or not right or looks_like_code(left) or looks_like_code(right):
        return False
    if left.endswith((" ", "\n")) or right.startswith((" ", "\n")):
        return False
    # A single trailing hyphen splits one word on purpose; `--` is an em dash and needs its space.
    return not (left.endswith("-") and not left.endswith("--"))


def glued_joins(path: Path) -> list[tuple[int, str]]:
    """Every place two prose literals on different lines run together."""
    found: list[tuple[int, str]] = []
    previous = None
    for token in tokenize.tokenize(io.BytesIO(path.read_bytes()).readline):
        if token.type == tokenize.STRING:
            if previous is not None and previous.end[0] != token.start[0]:
                try:
                    left, right = eval(previous.string), eval(token.string)  # noqa: S307
                except Exception:
                    left = right = None
                if isinstance(left, str) and isinstance(right, str) and is_glued(left, right):
                    found.append((token.start[0], f"{left[-30:]!r} + {right[:30]!r}"))
            previous = token
        elif token.type not in (tokenize.NL, tokenize.NEWLINE, tokenize.COMMENT,
                                tokenize.INDENT, tokenize.DEDENT):
            previous = None
    return found


def tracked_sources() -> list[Path]:
    out = subprocess.run(["git", "ls-files", "*.py"], cwd=REPO, capture_output=True, text=True)
    return [REPO / name for name in out.stdout.split()]


def test_no_wrapped_sentence_loses_its_space():
    offenders = [f"{path.relative_to(REPO)}:{line}  {sample}"
                 for path in tracked_sources() for line, sample in glued_joins(path)]
    assert not offenders, (
        "a wrapped sentence runs its words together -- add the trailing space to the first "
        "literal:\n  " + "\n  ".join(offenders))


def test_the_check_recognises_a_glued_join():
    """Reintroduce the defect and confirm it is seen; a check that never fires proves nothing."""
    assert is_glued("ending in a word", "starting in another")
    assert is_glued("an em dash --", "then the clause")
    assert not is_glued("ending with a space ", "starting a word")
    assert not is_glued("a hyphenated compo-", "und word")
    assert not looks_like_code("a sentence; with a semicolon")
    assert looks_like_code("ctx.beginPath();ctx.arc(n.x,n.y)")
