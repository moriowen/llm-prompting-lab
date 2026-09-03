"""Curves, inflection location, and the rule that picks the two table temperatures."""

from collections import Counter, defaultdict

from src import generate
from src.utils import config, trace
from src.utils.constants import LADDER


def query_index() -> dict:
    """qid -> query metadata, per task, so trials can be grouped by complexity band."""
    return {
        "task1": {q["qid"]: q for q in generate.load("task1_queries")},
        "task2": {q["qid"]: q for q in generate.load("task2_queries")},
    }


def band_of(task: str, item: dict) -> int:
    return item["l"] if task == "task1" else item["places"]


def cells(trials, arm="zeroshot", strict=False) -> dict:
    """(model, task, band, temp) -> {accuracy, self_consistency, n, invalid}."""
    index = query_index()
    field = "correct" if strict else "correct_norm"
    groups = defaultdict(list)
    for t in trials:
        # Models outside LADDER are supplementary: they are run to answer side questions
        # and never reach the tables. Dropped here rather than downstream because report()
        # pools every surviving cell into the curve that picks the two table temperatures,
        # so admitting them would let a model the deliverable never reports move the
        # selection. Their own curves are analysed separately.
        if t["model"] not in LADDER:
            continue
        # t["ladder"] is the supplementary *query* set, unrelated to LADDER above. Its
        # trials carry colliding qids for different queries, so joining them to the main
        # query files would silently mislabel their complexity band.
        if t["arm"] != arm or t.get("ladder") or t["qid"] not in index[t["task"]]:
            continue
        band = band_of(t["task"], index[t["task"]][t["qid"]])
        groups[(t["model"], t["task"], band, t["temperature"])].append(t)

    out = {}
    for key, group in groups.items():
        # Invalid trials (truncation, missing FINAL: marker) are excluded from the
        # accuracy denominator and reported separately, per section 4.7.
        good = [t for t in group if not t["invalid"]]
        by_query = defaultdict(list)
        for t in good:
            by_query[t["qid"]].append(t)
        consistencies = []
        for draws in by_query.values():
            modal = Counter(d["normalized"] for d in draws).most_common(1)
            consistencies.append(modal[0][1] / len(draws) if draws else 0.0)
        out[key] = {
            "accuracy": sum(t[field] for t in good) / len(good) if good else 0.0,
            "self_consistency": sum(consistencies) / len(consistencies) if consistencies else 0.0,
            "n": len(good), "invalid": len(group) - len(good), "queries": len(by_query),
        }
    return out


def curve(cell_map, temps=None, **filters) -> list[tuple[float, dict]]:
    """The (temperature, stats) series matching model/task/band filters, pooled if absent."""
    temps = temps or config.TEMP_GRID
    series = []
    for temp in temps:
        picked = [v for (m, tk, b, t), v in cell_map.items() if t == temp
                  and filters.get("model", m) == m and filters.get("task", tk) == tk
                  and filters.get("band", b) == b]
        if not picked:
            continue
        total = sum(p["n"] for p in picked)
        if not total:
            continue
        # Pooled points are weighted by trial count, so a cell with fewer valid trials
        # does not count as much as a full one.
        series.append((temp, {
            "accuracy": sum(p["accuracy"] * p["n"] for p in picked) / total,
            "self_consistency": sum(p["self_consistency"] * p["n"] for p in picked) / total,
            "n": total, "invalid": sum(p["invalid"] for p in picked),
        }))
    return series


def shape(series, key=None) -> dict:
    """Classify a curve and locate its inflection. The rule is fixed in config."""
    key = key or config.INFLECTION_CURVE
    temps = [t for t, _ in series]
    values = [s[key] for _, s in series]
    if len(values) < 3:
        return {"shape": "insufficient", "knee": None, "range": None}
    spread = max(values) - min(values)
    drops = [(values[i] - values[i + 1], i) for i in range(len(values) - 1)]
    worst, at = max(drops)
    if spread <= config.FLAT_RANGE:
        level = "ceiling" if max(values) > 0.5 else "floor"
        return {"shape": f"flat_at_{level}", "knee": None, "range": spread,
                "curve": key, "values": values, "temps": temps}
    if worst >= config.KNEE_DROP:
        return {"shape": "knee", "knee": (temps[at], temps[at + 1]), "knee_index": at,
                "drop": worst, "range": spread, "curve": key,
                "values": values, "temps": temps}
    return {"shape": "monotone", "knee": None, "range": spread, "curve": key,
            "values": values, "temps": temps}


def choose_pair(series) -> dict:
    """The two table temperatures, chosen by committed code from pooled data."""
    info = shape(series)
    temps = [t for t, _ in series]
    if info["shape"] == "knee":
        i = info["knee_index"]
        # One point clearly below the knee and one clearly above: maximum contrast that
        # is still local to the degradation, rather than the endpoints by default.
        low, high = temps[max(0, i - 1)], temps[min(len(temps) - 1, i + 2)]
    else:
        # Monotone or flat: the endpoints, for maximum separation. A flat curve means
        # the null result gets reported, not that the choice was arbitrary.
        low, high = temps[0], temps[-1]
    return {**info, "pair": (low, high)}


def report(arm="zeroshot") -> dict:
    """Everything the report's sweep section needs: pooled decision plus per-model shapes."""
    _, trials = trace.load_all()
    cell_map = cells(trials, arm=arm)
    models = sorted({m for m, _, _, _ in cell_map})
    tasks = sorted({t for _, t, _, _ in cell_map})
    pooled = curve(cell_map)
    decision = choose_pair(pooled) if pooled else {"shape": "insufficient", "pair": (0.0, 1.0)}
    per_model = {}
    for model in models:
        for task in tasks:
            for band in sorted({b for _, tk, b, _ in cell_map if tk == task}):
                series = curve(cell_map, model=model, task=task, band=band)
                if series:
                    per_model[f"{model}|{task}|l={band}"] = {
                        "series": series, **shape(series)}
    return {"cells": cell_map, "pooled": pooled, "decision": decision,
            "per_model": per_model, "arm": arm}
