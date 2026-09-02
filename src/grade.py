"""Grading. Returns a record per trial, never a bare bool."""

import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from fractions import Fraction

# The marker can land mid-line and wrapped in markdown ("**FINAL: 2.2**"), so it is
# matched anywhere a colon follows it, and the last occurrence wins.
FINAL = re.compile(r"(?<![A-Za-z])FINAL\s*:\s*(.*)", re.IGNORECASE)
NUMBER = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?(?:[eE][-+]?\d+)?")
DECIMAL_COMMA = re.compile(r"[-+]?\d+,\d+")


def extract(raw: str, arm: str) -> tuple[str, bool]:
    """(answer, extraction_ok). Only the CoT arms need the answer pulled out of prose."""
    if arm not in ("cot", "cot_verbose"):
        return raw.strip(), True
    hits = [m.group(1).strip() for m in FINAL.finditer(raw) if m.group(1).strip()]
    # A CoT response with no FINAL: marker is an invalid trial, not a wrong answer.
    return (hits[-1], True) if hits else ("", False)


def _strip_wrapping(text: str) -> str:
    """Drop fences, quotes, markdown and a leading 'The answer is:' style preamble."""
    text = re.sub(r"```[a-z]*", "", text).strip()
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return ""
    text = lines[-1].strip()          # prose first, answer last, is the usual shape
    text = re.sub(r"^.*?[:=]\s*", "", text)
    return text.strip(" \t`'\"*_.,!")


# --- task 1 ---------------------------------------------------------------------------

def grade_task1(item: dict, raw: str, arm: str) -> dict:
    """valid / correct under the handout's two criteria, strict and normalised."""
    extracted, ok = extract(raw, arm)
    normalized = _strip_wrapping(extracted)
    gold, length = item["gold"], item["l"]

    # The handout defines valid as len(s_out) == len(s), so under a strict reading a
    # preamble makes the trial invalid. Both readings are computed; the report shows both.
    valid = len(extracted) == length
    correct = extracted == gold
    valid_norm = len(normalized) == length
    correct_norm = normalized == gold

    if not ok:
        error = "extraction_failed"
    elif correct:
        error = "none"
    elif not extracted:
        error = "empty"
    elif correct_norm:
        error = "extra_text"
    elif len(normalized) != length:
        error = "wrong_length"
    elif sorted(normalized) == sorted(gold):
        error = "wrong_order"
    else:
        error = "wrong_chars"

    return {"valid": valid, "correct": correct, "valid_norm": valid_norm,
            "correct_norm": correct_norm, "error_type": error,
            "extracted": extracted, "normalized": normalized,
            "extraction_ok": ok, "gold": gold}


# --- task 2 ---------------------------------------------------------------------------

def _parse(text: str) -> tuple[Decimal | None, str | None]:
    """First number-like token -> (value, canonical text without separators)."""
    # A decimal comma (0,3107) is a plausible output from a multilingual model and is
    # a formatting difference, not an arithmetic one. Normalise it before parsing.
    if DECIMAL_COMMA.fullmatch(text.strip()):
        text = text.strip().replace(",", ".")
    m = NUMBER.search(text)
    if not m:
        return None, None
    token = m.group(0).replace(",", "")
    try:
        return Decimal(token), token
    except InvalidOperation:
        return None, None


def _round_half_up(a: int, b: int, places: int) -> Decimal:
    with localcontext() as ctx:
        ctx.prec = places + 30
        return (Decimal(a) / Decimal(b)).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)


def grade_task2(item: dict, raw: str, arm: str) -> dict:
    """Correctness plus the section 4.4 error taxonomy."""
    extracted, ok = extract(raw, arm)
    a, b, places, gold = item["a"], item["b"], item["places"], item["gold"]
    value, token = _parse(_strip_wrapping(extracted) or extracted)
    exact = Fraction(a, b)

    correct = extracted == gold
    correct_norm = value is not None and value == Decimal(gold)

    if not ok:
        error = "extraction_failed"
    elif value is None:
        error = "unparseable"
    elif correct:
        error = "none"
    elif correct_norm:
        # Right value, wrong surface form: 2,05078125 or 2.05078125e0 or a dropped
        # trailing zero. Section 4.4 scores these as correct after normalisation.
        error = "format_only"
    else:
        # Read the precision off the Decimal rather than the text, so scientific
        # notation and thousands separators are handled the same way.
        out_places = max(0, -value.as_tuple().exponent)
        # Every rounding convention -- half-up, half-even, truncation -- lands within
        # one unit of the last place it printed. Inside that, the division itself was
        # right and only the presentation is wrong.
        # out_places == 0 means it answered with a whole number, which the handout
        # forbids outright -- that is a wrong answer, not a precision slip.
        digits_right = out_places >= 1 and abs(Fraction(value) - exact) < Fraction(1, 10 ** out_places)
        if digits_right and out_places != places:
            error = "precision_error"       # right value, wrong number of places
        elif digits_right:
            error = "rounding_error"        # correct quotient, rounded wrong
        else:
            error = "wrong_digits"          # the division itself is wrong

    return {"valid": value is not None, "correct": correct,
            "valid_norm": value is not None, "correct_norm": correct_norm,
            "error_type": error, "extracted": extracted,
            "normalized": token or "", "extraction_ok": ok, "gold": gold}


def grade(task: str, item: dict, raw: str, arm: str) -> dict:
    """Dispatch."""
    return (grade_task1 if task == "task1" else grade_task2)(item, raw, arm)


TASK1_ERRORS = ("none", "extra_text", "wrong_length", "wrong_order", "wrong_chars",
                "empty", "extraction_failed")
TASK2_ERRORS = ("none", "format_only", "precision_error", "rounding_error",
                "wrong_digits", "unparseable", "extraction_failed")
