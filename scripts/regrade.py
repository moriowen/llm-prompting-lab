"""Re-derive every stored grade from the raw text already in runs/. Queries no model.

Grading happens at run time and is baked into the JSONL, so a grade.py fix does not reach
trials that are already recorded. Everything grade() needs -- task, arm, item, raw -- is in
the trace, so the fix can be applied to the existing corpus without re-running inference.
That keeps the repaired cells on exactly the sampling configuration they were run with,
which a re-run would not: nothing pins a re-run to reproduce the original draws.

Writes via a temp file and os.replace, so an interrupted pass cannot leave a half-written
cell. `--check` reports what would change and writes nothing.
"""

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import generate, grade as grading
from src.utils import trace

# The regraded fields. Anything else on a trial line -- timings, tokens, prompt, raw -- is
# carried through untouched, so this rewrites grades and nothing else.
GRADE_FIELDS = ("valid", "correct", "valid_norm", "correct_norm", "error_type",
                "extracted", "normalized", "extraction_ok", "gold")


def items_for(task: str, ladder: bool) -> dict:
    """qid -> query, from the committed ground truth the cell was run against."""
    if ladder:
        return {q["qid"]: q for q in generate.load("ladder_queries")[task]}
    return {q["qid"]: q for q in generate.load(f"{task}_queries")}


def regrade_file(path: Path, apply: bool) -> Counter:
    """Regrade one cell. Returns counts of what changed."""
    records = trace.load(path)
    if not records or records[0].get("type") != "run":
        return Counter({"skipped_no_header": 1})
    header = records[0]
    task, arm = header["task"], header["arm"]
    items = items_for(task, header.get("ladder", False))

    counts, out = Counter(), [header]
    for rec in records[1:]:
        if rec.get("type") != "trial" or rec["qid"] not in items:
            out.append(rec)
            continue
        counts["trials"] += 1
        g = grading.grade(task, items[rec["qid"]], rec.get("raw", ""), arm)
        # invalid is derived exactly as experiment.py derives it, from the truncation
        # flag already stored plus the freshly computed extraction result.
        invalid = bool(rec.get("truncated")) or not g["extraction_ok"]
        if invalid != bool(rec.get("invalid")):
            counts["invalid_changed"] += 1
        if any(rec.get(k) != g[k] for k in GRADE_FIELDS):
            counts["grade_changed"] += 1
        if bool(rec.get("correct_norm")) != bool(g["correct_norm"]):
            counts["correctness_changed"] += 1
        out.append({**rec, **g, "invalid": invalid})

    if apply and (counts["grade_changed"] or counts["invalid_changed"]):
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w") as f:
            for rec in out:
                f.write(json.dumps(rec, default=str) + "\n")
        os.replace(tmp, path)
        counts["files_written"] += 1
    return counts


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true", help="report changes, write nothing")
    args = p.parse_args()

    total = Counter()
    for path in sorted(trace.RUNS.rglob("*.jsonl")):
        c = regrade_file(path, apply=not args.check)
        total.update(c)
        if c["invalid_changed"] or c["correctness_changed"]:
            print(f"{str(path):58} trials={c['trials']:4} "
                  f"invalid{'->' if not args.check else '~'}{c['invalid_changed']:4} "
                  f"correctness_changed={c['correctness_changed']}")
    print(f"\n{'checked' if args.check else 'regraded'}: {total['trials']} trials, "
          f"{total['invalid_changed']} invalid flags changed, "
          f"{total['grade_changed']} grade records changed, "
          f"{total['correctness_changed']} correctness changed, "
          f"{total['files_written']} files written")


if __name__ == "__main__":
    main()
