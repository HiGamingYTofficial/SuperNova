"""lib/text_effects.py — pure functions for the text-styling commands.

Kept out of cogs/ deliberately: this is shared, stateless logic with no
Discord API calls in it, so it's easy to unit test and easy to reuse
from more than one command later.
"""

from __future__ import annotations

import random

_BOLD_MAP = {
    **{chr(c): chr(0x1D400 + (c - ord("A"))) for c in range(ord("A"), ord("Z") + 1)},
    **{chr(c): chr(0x1D41A + (c - ord("a"))) for c in range(ord("a"), ord("z") + 1)},
    **{chr(c): chr(0x1D7CE + (c - ord("0"))) for c in range(ord("0"), ord("9") + 1)},
}

_FANCY_MAP = {
    **{chr(c): chr(0x1D4D0 + (c - ord("A"))) for c in range(ord("A"), ord("Z") + 1)},
    **{chr(c): chr(0x1D4EA + (c - ord("a"))) for c in range(ord("a"), ord("z") + 1)},
}

_UWU_REPLACEMENTS = (
    ("r", "w"), ("l", "w"), ("R", "W"), ("L", "W"),
    ("no", "nyo"), ("na", "nya"), ("nu", "nyu"), ("ne", "nye"),
)
_UWU_FACES = ["(・`ω´・)", "(´｡• ω •｡`)", "OwO", "UwU", ">w<", "^w^", "(￣ω￣)"]


def to_bold(text: str) -> str:
    """Maps to Unicode 'Mathematical Bold' code points — renders as bold
    everywhere Discord shows plain text (usernames, embed titles, etc.),
    unlike Markdown **bold** which only renders in message bodies."""
    return "".join(_BOLD_MAP.get(ch, ch) for ch in text)


def to_fancy(text: str) -> str:
    """Maps to Unicode 'Mathematical Script' code points for a cursive look."""
    return "".join(_FANCY_MAP.get(ch, ch) for ch in text)


def uwuify(text: str, *, seed: int | None = None) -> str:
    """Lighthearted, reversible-in-spirit text transform. `seed` is only
    exposed for deterministic tests; commands should leave it unset."""
    rng = random.Random(seed)
    result = text
    for old, new in _UWU_REPLACEMENTS:
        result = result.replace(old, new)
    if rng.random() < 0.5:
        result += f" {rng.choice(_UWU_FACES)}"
    return result


def reverse_text(text: str) -> str:
    return text[::-1]


def mock_text(text: str) -> str:
    """SpOnGeBoB mOcKiNg CaSe."""
    return "".join(ch.upper() if i % 2 else ch.lower() for i, ch in enumerate(text))


def clap_text(text: str) -> str:
    return " 👏 ".join(text.split())


_FULLWIDTH_OFFSET = 0xFF00 - 0x20


def vaporwave_text(text: str) -> str:
    """Converts to full-width unicode characters for that ｖａｐｏｒｗａｖｅ look."""
    out = []
    for ch in text:
        if ch == " ":
            out.append("　")  # ideographic space, matches the full-width rhythm
        elif 0x21 <= ord(ch) <= 0x7E:
            out.append(chr(ord(ch) + _FULLWIDTH_OFFSET))
        else:
            out.append(ch)
    return "".join(out)
