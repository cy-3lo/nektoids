"""A number written as a short line of text, to copy, paste and keep (D-205, D-413): a board's
text and a level's word.

The number is written in base 59, the alphanumerics without I, l and O, which are read as 1, 1
and 0, in blocks of at most BLOCK characters, each followed by CHECKS check characters of a
Reed-Solomon code over the integers mod 59, a field since 59 is prime. The version of the format
is a hidden first symbol: never written, it enters every check, so a text of another version,
or of another kind, fails them. Distance CHECKS + 1 = 5: in each block one wrong character is
put right, and two are refused, never read as another number. Pure Python, no pygame.
"""

from __future__ import annotations

from collections.abc import Sequence

ALPHABET = "0123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"  # no I, l, O
P = len(ALPHABET)  # 59, a prime: the check characters are reckoned mod 59
READ = {c: i for i, c in enumerate(ALPHABET)} | {"I": 1, "l": 1, "O": 0}
IGNORED = " -\t\n"  # spaces and dashes a person may put in
CHECKS = 4
BLOCK = P - 2 - CHECKS  # data characters a block holds: P - 1 symbols, the version one of them
ROOT = 2  # a primitive root mod 59: its powers are every non-zero symbol
POWER = [pow(ROOT, i, P) for i in range(P - 1)]
LOG = {value: i for i, value in enumerate(POWER)}


def spell(number: int, version: int) -> str:
    """`number` written in base 59, in blocks, each with its check characters."""
    data = []
    while number:
        number, digit = divmod(number, P)
        data.append(digit)
    data = data[::-1] or [0]
    blocks = [data[i : i + BLOCK] for i in range(0, len(data), BLOCK)]
    return "".join(ALPHABET[s] for block in blocks for s in (*block, *_checks(version, block)))


def unspell(text: str, version: int, what: str) -> tuple[int, bool]:
    """The number `text` writes, and whether a wrong character was put right; ValueError,
    naming `what` it should hold, for a text of another version or with two wrong characters."""
    symbols = []
    for char in text:
        if char in IGNORED:
            continue
        if char not in READ:
            raise ValueError(f"no {what} has the character {char!r}")
        symbols.append(READ[char])
    size = BLOCK + CHECKS
    blocks = [symbols[i : i + size] for i in range(0, len(symbols), size)]
    if not blocks or len(blocks[-1]) <= CHECKS:
        raise ValueError(f"this text is too short to hold a {what}")
    number, corrected = 0, False
    for block in blocks:
        fixed = _corrected([version, *block])
        if fixed is None:
            raise ValueError(f"this text holds no {what}: mistyped, or of another version")
        corrected |= fixed[1:] != block
        for digit in fixed[1:-CHECKS]:
            number = number * P + digit
    return number, corrected


def _generator() -> list[int]:
    """The product of (x - ROOT^j) for j = 1..CHECKS, lowest degree first."""
    g = [1]
    for j in range(1, CHECKS + 1):
        g = [(lower - POWER[j] * same) % P for same, lower in zip([*g, 0], [0, *g], strict=True)]
    return g


GENERATOR = _generator()[::-1]  # highest degree first


def _checks(version: int, block: Sequence[int]) -> list[int]:
    """The check symbols of the version and `block`: minus the remainder of their polynomial,
    times x^CHECKS, divided by the generator, so the whole word divides by it."""
    rest = [version, *block, *[0] * CHECKS]
    for i in range(len(rest) - CHECKS):
        if rest[i]:
            factor = rest[i]
            for j in range(1, len(GENERATOR)):
                rest[i + j] = (rest[i + j] - GENERATOR[j] * factor) % P
    return [(-r) % P for r in rest[-CHECKS:]]


def _corrected(word: list[int]) -> list[int] | None:
    """The word with one wrong symbol put right, the hidden first one excepted; None if it has
    two or more. Its syndromes are the word's values at ROOT^j: all 0 for a word of the code,
    e X^j for one error of e at the place whose locator is X."""
    syndromes = []
    for j in range(1, CHECKS + 1):
        value = 0
        for symbol in word:
            value = (value * POWER[j] + symbol) % P
        syndromes.append(value)
    if not any(syndromes):
        return word
    if not all(syndromes) or any(
        (syndromes[j + 1] * syndromes[j + 1] - syndromes[j] * syndromes[j + 2]) % P
        for j in range(CHECKS - 2)
    ):
        return None
    locator = syndromes[1] * pow(syndromes[0], P - 2, P) % P  # ROOT^p, p from the last symbol
    where = len(word) - 1 - LOG[locator]
    if where < 1:  # the version, or before the word: not one error
        return None
    fixed = list(word)
    fixed[where] = (fixed[where] - syndromes[0] * pow(locator, P - 2, P)) % P
    return fixed
