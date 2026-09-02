"""Seeded query generation. Every gold answer here is computed by Python, never by a model."""

import json
import random
import string
from decimal import Decimal, ROUND_HALF_UP, localcontext
from fractions import Fraction
from pathlib import Path

from src.utils import config
from src.utils.constants import FAMOUS_FRACTIONS

DATA = Path("data")
ALPHABET = string.ascii_letters  # exactly the handout's 52: a-z and A-Z


# --- task 1 -------------------------------------------------------------------------

def make_string(rng: random.Random, length: int) -> str:
    """A random mixed-case string. Case is forced to vary because it changes tokenization."""
    while True:
        s = "".join(rng.choice(ALPHABET) for _ in range(length))
        # An all-lower or all-upper string tokenizes very differently from a mixed one,
        # and section 4.3 wants the case pattern to be a variable we can report, not an
        # accident of the draw.
        if any(c.islower() for c in s) and any(c.isupper() for c in s):
            return s


def case_pattern(s: str) -> str:
    """e.g. 'uLlUl' -> the shape that section 4.3 correlates against."""
    return "".join("U" if c.isupper() else "l" for c in s)


def task1_item(s: str) -> dict:
    gold = s[::-1]
    # Two checks that are trivially true if the code is right and loudly false if not.
    assert gold[::-1] == s, f"involution failed on {s!r}"
    assert sorted(gold) == sorted(s), f"multiset changed on {s!r}"
    return {
        "qid": None, "s": s, "l": len(s), "gold": gold,
        "case_pattern": case_pattern(s),
        "n_upper": sum(c.isupper() for c in s),
        "distinct_chars": len(set(s)),
    }


def generate_task1(seed: int, lengths=config.TASK1_LENGTHS, per_band=config.QUERIES_PER_BAND):
    """5 strings per length band, mixed case, no duplicates."""
    rng = random.Random(seed)
    items, seen = [], set()
    for length in lengths:
        made = 0
        while made < per_band:
            s = make_string(rng, length)
            if s in seen:
                continue
            seen.add(s)
            items.append(task1_item(s))
            made += 1
    for i, item in enumerate(items, 1):
        item["qid"] = f"Q{i}"
    return items


# --- task 2 -------------------------------------------------------------------------

def gold_decimal(a: int, b: int, places: int) -> str:
    """A/B rounded half-up to `places`, via Decimal at high precision."""
    # Never float division: round(a/b, 8) accumulates float error and python's round()
    # is banker's rounding, which is not what a human -- or a model -- produces.
    with localcontext() as ctx:
        ctx.prec = places + 30
        q = Decimal(a) / Decimal(b)
        return str(q.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP))


def gold_fraction(a: int, b: int, places: int) -> str:
    """The same answer by an independent route, for cross-checking gold_decimal."""
    scaled = Fraction(a * 10 ** places, b)
    n = scaled.numerator // scaled.denominator
    if scaled - n >= Fraction(1, 2):  # round half up, explicitly
        n += 1
    digits = str(n).rjust(places + 1, "0")
    return f"{digits[:-places]}.{digits[-places:]}" if places else digits


def is_tie(a: int, b: int, places: int) -> bool:
    """True when the value sits exactly on the rounding boundary."""
    # Grading a tie penalises the model for our unstated convention, not its arithmetic.
    scaled = Fraction(a * 10 ** places, b)
    return scaled - (scaled.numerator // scaled.denominator) == Fraction(1, 2)


def period_length(b: int) -> int:
    """Length of the repeating block of 1/b; 0 if the expansion terminates."""
    d = b
    for p in (2, 5):
        while d % p == 0:
            d //= p
    if d == 1:
        return 0
    k, r = 1, 10 % d
    while r != 1:
        r = (r * 10) % d
        k += 1
    return k


def terminating_len(b: int) -> int:
    """Number of decimal digits in a terminating expansion of 1/b."""
    v2 = v5 = 0
    d = b
    while d % 2 == 0:
        d //= 2
        v2 += 1
    while d % 5 == 0:
        d //= 5
        v5 += 1
    return max(v2, v5)


def stratum(a: int, b: int) -> tuple[str, str]:
    """(expansion kind, magnitude) -- recorded per query so the analysis can split on it."""
    f = Fraction(a, b)
    p = period_length(f.denominator)
    kind = "terminating" if p == 0 else ("long_period" if p >= 10 else "short_period")
    return kind, "A>B" if a > b else "A<B"


def task2_item(a: int, b: int, places: int) -> dict:
    dec, frac = gold_decimal(a, b, places), gold_fraction(a, b, places)
    # Two independent implementations agreeing is verification. One implementation
    # running successfully is not.
    assert dec == frac, f"gold mismatch on {a}/{b} @{places}: {dec} vs {frac}"
    kind, magnitude = stratum(a, b)
    return {
        "qid": None, "a": a, "b": b, "places": places, "gold": dec,
        "expansion": kind, "magnitude": magnitude,
        "period": period_length(Fraction(a, b).denominator),
        "decimal_len": terminating_len(Fraction(a, b).denominator),
        "exact": str(Fraction(a, b)),
    }


# Five slots per band, filled in order. Fixing the strata in advance stops the draw
# from handing one band five easy terminating fractions and the other five hard ones.
# 2**9 = 512 is the largest power of two under the B <= 999 cap.
MAX_TERM_LEN = 9

SLOTS = [
    ("short_period", "A>B"),
    ("short_period", "A<B"),
    ("terminating", "A<B"),
    ("terminating", "A>B"),
    ("long_period", "A<B"),
]


def generate_task2(seed: int, places_bands=config.TASK2_PLACES, slots=SLOTS):
    """5 divisions per decimal-place band, one per stratum slot, ties and famous pairs rejected."""
    rng = random.Random(seed)
    items, seen = [], set()
    rejected = {"integer": 0, "tie": 0, "famous": 0, "duplicate": 0, "too_short": 0}
    for places in places_bands:
        for want_kind, want_mag in slots:
            while True:
                a, b = rng.randint(2, 999), rng.randint(2, 999)
                if b == 0 or a % b == 0:      # the handout requires a non-integer result
                    rejected["integer"] += 1
                    continue
                f = Fraction(a, b)
                if (f.numerator, f.denominator) in FAMOUS_FRACTIONS:
                    rejected["famous"] += 1
                    continue
                if is_tie(a, b, places):
                    rejected["tie"] += 1
                    continue
                if stratum(a, b) != (want_kind, want_mag):
                    continue
                # A terminating fraction shorter than the rounding position is a
                # padded-zeros query (7.70000): it tests trailing-zero formatting, not
                # division. Require the expansion to reach the rounding position.
                # (capped at MAX_TERM_LEN: with B <= 999 the longest achievable
                # terminating expansion is 1/512, nine digits, so a 12-place band
                # cannot ask for twelve.)
                want_len = min(places, MAX_TERM_LEN)
                if want_kind == "terminating" and terminating_len(f.denominator) < want_len:
                    rejected["too_short"] += 1
                    continue
                if (a, b) in seen:
                    rejected["duplicate"] += 1
                    continue
                seen.add((a, b))
                items.append(task2_item(a, b, places))
                break
    for i, item in enumerate(items, 1):
        item["qid"] = f"Q{i}"
    return items, rejected


# --- pools and ladders ---------------------------------------------------------------

def generate_fewshot(task1_items, task2_items):
    """Held-out shots, drawn with a different seed and asserted disjoint from the tests."""
    pool = {"task1": {}, "task2": {}}
    t1 = generate_task1(config.FEWSHOT_SEED, per_band=config.N_SHOTS)
    for length in config.TASK1_LENGTHS:
        pool["task1"][str(length)] = [i for i in t1 if i["l"] == length]
    t2, _ = generate_task2(config.FEWSHOT_SEED, slots=SLOTS[: config.N_SHOTS])
    for places in config.TASK2_PLACES:
        pool["task2"][str(places)] = [i for i in t2 if i["places"] == places]

    test_s = {i["s"] for i in task1_items}
    shot_s = {i["s"] for band in pool["task1"].values() for i in band}
    assert not (test_s & shot_s), f"few-shot overlap on task 1: {test_s & shot_s}"
    test_ab = {(i["a"], i["b"]) for i in task2_items}
    shot_ab = {(i["a"], i["b"]) for band in pool["task2"].values() for i in band}
    assert not (test_ab & shot_ab), f"few-shot overlap on task 2: {test_ab & shot_ab}"
    return pool


def generate_ladder():
    """Supplementary complexity ladder. Free to run locally, so the bands go wider."""
    t1 = generate_task1(config.LADDER_SEED, lengths=(3, 5, 8, 12, 16, 20))
    t2, _ = generate_task2(config.LADDER_SEED, places_bands=(2, 5, 8, 12))
    return {"task1": t1, "task2": t2}


def build() -> dict:
    """Generate everything from the committed seeds. Pure function of config."""
    t1 = generate_task1(config.SEED)
    t2, rejected = generate_task2(config.SEED)
    return {
        "task1_queries": t1,
        "task2_queries": t2,
        "fewshot_pool": generate_fewshot(t1, t2),
        "ladder_queries": generate_ladder(),
        "_rejected": rejected,
    }


def write(out=DATA) -> dict:
    """Write data/*.json and report the rejection counts."""
    out.mkdir(exist_ok=True)
    built = build()
    rejected = built.pop("_rejected")
    for name, payload in built.items():
        (out / f"{name}.json").write_text(json.dumps(payload, indent=2) + "\n")
    return rejected


def load(name: str):
    """Read one committed data file."""
    return json.loads((DATA / f"{name}.json").read_text())
