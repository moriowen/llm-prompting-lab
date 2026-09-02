"""Re-derive every query and gold answer from the seed and diff against committed data/."""

import json
from decimal import Decimal
from fractions import Fraction

from src import generate


def check_task1(items) -> list[str]:
    """The involution and the multiset are both trivially true if the code is right."""
    problems = []
    for i in items:
        if i["gold"][::-1] != i["s"]:
            problems.append(f"task1 {i['qid']}: reverse(reverse(s)) != s")
        if sorted(i["gold"]) != sorted(i["s"]):
            problems.append(f"task1 {i['qid']}: character multiset changed")
        if len(i["gold"]) != i["l"]:
            problems.append(f"task1 {i['qid']}: gold length {len(i['gold'])} != l {i['l']}")
    return problems


def check_task2(items) -> list[str]:
    """Decimal vs Fraction, independently, plus the handout's own constraints."""
    problems = []
    for i in items:
        a, b, places = i["a"], i["b"], i["places"]
        if generate.gold_decimal(a, b, places) != i["gold"]:
            problems.append(f"task2 {i['qid']}: Decimal route disagrees with committed gold")
        if generate.gold_fraction(a, b, places) != i["gold"]:
            problems.append(f"task2 {i['qid']}: Fraction route disagrees with committed gold")
        if a % b == 0:
            problems.append(f"task2 {i['qid']}: {a}/{b} is a whole number, which the handout forbids")
        if generate.is_tie(a, b, places):
            problems.append(f"task2 {i['qid']}: sits exactly on the rounding boundary")
        if len(i["gold"].split(".")[1]) != places:
            problems.append(f"task2 {i['qid']}: gold does not carry exactly {places} places")
        # The gold must be within half an ulp of the exact rational value.
        if abs(Fraction(i["gold"]) - Fraction(a, b)) > Fraction(1, 2 * 10 ** places):
            problems.append(f"task2 {i['qid']}: gold is further than half an ulp from A/B")
    return problems


def check_disjoint(t1, t2, pool) -> list[str]:
    """A few-shot example that is also a test item would contaminate our own experiment."""
    problems = []
    shots = {i["s"] for band in pool["task1"].values() for i in band}
    if overlap := shots & {i["s"] for i in t1}:
        problems.append(f"few-shot pool overlaps task 1 test set: {overlap}")
    shots2 = {(i["a"], i["b"]) for band in pool["task2"].values() for i in band}
    if overlap := shots2 & {(i["a"], i["b"]) for i in t2}:
        problems.append(f"few-shot pool overlaps task 2 test set: {overlap}")
    return problems


def check_drift(built) -> list[str]:
    """Committed data/ must equal what the seed produces today."""
    problems = []
    for name, payload in built.items():
        try:
            on_disk = generate.load(name)
        except FileNotFoundError:
            problems.append(f"{name}.json is missing")
            continue
        if json.dumps(on_disk, sort_keys=True) != json.dumps(payload, sort_keys=True):
            problems.append(f"{name}.json has drifted from the seed -- re-run `main.py generate`")
    return problems


def run() -> list[str]:
    """Every ground-truth check. Returns problems; empty means the invariant holds."""
    built = generate.build()
    built.pop("_rejected")
    t1, t2 = built["task1_queries"], built["task2_queries"]
    problems = check_task1(t1) + check_task2(t2) + check_drift(built)
    problems += check_disjoint(t1, t2, built["fewshot_pool"])
    problems += check_task1(built["ladder_queries"]["task1"])
    problems += check_task2(built["ladder_queries"]["task2"])
    return problems
