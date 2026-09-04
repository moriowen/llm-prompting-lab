"""Report text for the problem, assumptions, findings, and conclusions.

Result placeholders such as `{...}` are filled from runs/ when the report is built.
Re-grading or adding runs updates those values. This module uses the same committed
traces as the explorer and does not call a model.
"""

import html
import re
from collections import Counter, defaultdict

from src import generate
from src.utils import config, trace
from src.utils.constants import LADDER, MODEL_REGISTRY, TASK_NAMES

ARMS = ("zeroshot", "fewshot", "fewshot_verbose", "cot", "cot_verbose")
ARM_NAMES = {"zeroshot": "zero-shot", "fewshot": "few-shot",
             "fewshot_verbose": "few-shot (verbose)", "cot": "CoT",
             "cot_verbose": "CoT (verbose)"}


def esc(x) -> str:
    return html.escape(str(x))


def size(alias: str) -> float:
    return float(MODEL_REGISTRY[alias]["params"].rstrip("B"))


def by_size() -> list[str]:
    return sorted(MODEL_REGISTRY, key=size)


# --- statistics -----------------------------------------------------------------------

def stats(trials: list[dict]) -> dict:
    """Every figure the prose and the tables can cite, keyed for lookup by fig()."""
    q1 = {q["qid"]: q for q in generate.load("task1_queries")}
    q2 = {q["qid"]: q for q in generate.load("task2_queries")}
    items = {"task1": q1, "task2": q2}

    # The ladder reuses qids for different queries and is not part of this analysis.
    main = [t for t in trials if not t.get("ladder")]

    arm, band, stable, tax = defaultdict(list), defaultdict(list), {}, defaultdict(Counter)
    for t in main:
        key = (t["model"], t["task"], t["arm"])
        arm[key].append(t)
        if t["arm"] == "zeroshot":
            q = items[t["task"]][t["qid"]]
            band[(t["model"], t["task"], q["l"] if t["task"] == "task1" else q["places"])].append(t)
            tax[(t["model"], t["task"])][t["error_type"]] += 1

    def score(rows: list[dict]) -> dict:
        good = [t for t in rows if not t["invalid"]]
        n = len(good)
        return {"n": len(rows), "valid_n": n, "invalid": len(rows) - n,
                "acc": sum(t["correct_norm"] for t in good) / n if n else 0.0,
                "accs": sum(t["correct"] for t in good) / n if n else 0.0,
                "valid": sum(t["valid_norm"] for t in good) / n if n else 0.0}

    # An item is "always"/"never" if it is right at every / no temperature it was drawn
    # at. The split is the whole point of finding 1: if temperature drove accuracy,
    # almost everything would land in "sometimes".
    for m in {t["model"] for t in main}:
        for task in ("task1", "task2"):
            hit, tot = Counter(), Counter()
            for t in main:
                if (t["model"], t["task"], t["arm"]) != (m, task, "zeroshot") or t["invalid"]:
                    continue
                tot[t["qid"]] += 1
                hit[t["qid"]] += bool(t["correct_norm"])
            if tot:
                stable[(m, task)] = {
                    "never": sum(1 for q in tot if hit[q] == 0),
                    "always": sum(1 for q in tot if hit[q] == tot[q]),
                    "sometimes": sum(1 for q in tot if 0 < hit[q] < tot[q]),
                    "items": len(tot)}

    # Pooled accuracy per temperature, for the sparklines in finding 1.
    curve = {}
    for m in {t["model"] for t in main}:
        for task in ("task1", "task2"):
            pts = []
            for T in config.TEMP_GRID:
                rows = [t for t in main if (t["model"], t["task"], t["arm"], t["temperature"])
                        == (m, task, "zeroshot", T)]
                if rows:
                    pts.append((T, score(rows)["acc"]))
            if pts:
                curve[(m, task)] = pts

    # Case pattern is a proxy for item identity on task 1: with ten strings, a per-pattern
    # accuracy of 1.00 or 0.00 is one string, not a property of the pattern.
    pattern = defaultdict(lambda: [0, 0])
    for t in main:
        if t["task"] == "task1" and t["arm"] == "zeroshot" and not t["invalid"]:
            p = pattern[(t["model"], q1[t["qid"]]["case_pattern"])]
            p[0] += bool(t["correct_norm"])
            p[1] += 1

    return {"arm": {k: score(v) for k, v in arm.items()}, "band": {k: score(v) for k, v in band.items()},
            "stable": stable, "tax": tax, "curve": curve, "pattern": dict(pattern),
            "models": sorted({t["model"] for t in main}, key=size),
            "n_trials": len(trials), "n_main": len(main)}


REF = re.compile(r"\{([a-z_]+(?: [^}]+)?)\}")


def fig(spec: str, S: dict) -> str:
    """Resolve one {...} reference against the computed statistics."""
    kind, *rest = spec.split()
    if kind in ("acc", "accs", "valid"):
        return f"{S['arm'][tuple(rest)][kind]:.3f}"
    if kind in ("n", "invalid", "valid_n"):
        return str(S["arm"][tuple(rest)][kind])
    if kind == "delta":                      # {delta <model> <task> <arm> <baseline>}
        m, task, a, b = rest
        return f"{S['arm'][(m, task, a)]['acc'] - S['arm'][(m, task, b)]['acc']:+.3f}"
    if kind == "band":                       # {band <model> <task> <band>}
        m, task, b = rest
        return f"{S['band'][(m, task, int(b))]['acc']:.3f}"
    if kind == "stab":                       # {stab <model> <task> <never|always|...>}
        m, task, which = rest
        return str(S["stable"][(m, task)][which])
    if kind == "tax":                        # {tax <model> <task> <error_type>}
        m, task, e = rest
        return str(S["tax"][(m, task)][e])
    if kind == "tax_share":                  # share of the model's *errors*, not its trials
        m, task, e = rest
        c = S["tax"][(m, task)]
        return f"{100 * c[e] / max(1, sum(c.values()) - c['none']):.0f}%"
    if kind in ("floor_models", "floor_trials"):
        # The models that never once got a division right, in any arm, at any
        # temperature -- and how many trials that verdict rests on.
        floor = [m for m in S["models"]
                 if any(tk == "task2" for (mm, tk, _) in S["arm"] if mm == m)
                 and all(v["acc"] == 0 for (mm, tk, _), v in S["arm"].items()
                         if mm == m and tk == "task2")]
        if kind == "floor_models":
            return str(len(floor))
        return f"{sum(v['n'] for (m, tk, _), v in S['arm'].items() if m in floor and tk == 'task2'):,}"
    if kind == "n_trials":
        return f"{S['n_trials']:,}"
    if kind == "n_models":
        return str(len(S["models"]))
    if kind == "n_temps":
        return str(len(config.TEMP_GRID))
    raise KeyError(spec)


def resolve(text: str, S: dict) -> str:
    """Substitute every {...} in a prose block."""
    return REF.sub(lambda m: fig(m.group(1), S), text)


# --- tables ---------------------------------------------------------------------------

def table(head: list[str], rows: list[list[str]], cls: str = "") -> str:
    h = "".join(f"<th>{c}</th>" for c in head)
    b = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f"<div class='scroll'><table class='{cls}'><tr>{h}</tr>{b}</table></div>"


def model_cell(m: str) -> str:
    """Model name with its size, and a mark for the three that are the original ladder."""
    tag = " <span class='pill'>ladder</span>" if m in LADDER else ""
    return f"<span class='mono'>{esc(m)}</span>{tag}"


def results_table(S: dict, task: str) -> str:
    """Accuracy per arm, one row per model, ascending by size."""
    arms = [a for a in ARMS if any((m, task, a) in S["arm"] for m in S["models"])]
    rows = []
    for m in S["models"]:
        cells = []
        for a in arms:
            s = S["arm"].get((m, task, a))
            if not s:
                cells.append("<td class='na'>–</td>")
                continue
            # Shade by accuracy so the threshold in task 2 is visible without reading.
            # A cell that lost trials to truncation says so on its face: without it,
            # llama's 95-trial few-shot cell is indistinguishable from a complete one.
            note = " *" if s["n"] < 330 else ""
            if s["invalid"]:
                note += f", {s['invalid']} invalid"
            cells.append(f"<td class='num' style='background:{ramp(s['acc'])}'>{s['acc']:.3f}"
                         f"<span class='sub2'>n={s['valid_n']}{note}</span></td>")
        rows.append(f"<td>{model_cell(m)}</td><td class='num'>{MODEL_REGISTRY[m]['params']}</td>"
                    + "".join(cells))
    head = "".join(f"<th>{ARM_NAMES[a]}</th>" for a in arms)
    body = "".join(f"<tr>{r}</tr>" for r in rows)
    return (f"<div class='scroll'><table><tr><th>Model</th><th>Params</th>{head}</tr>"
            f"{body}</table></div>"
            "<p class='sub2'>Normalised accuracy over valid trials; n is the valid count. "
            "<span class='na'>*</span> marks an incomplete run with "
            "provisional results. <span class='na'>–</span> means the arm was not run.</p>")


def ramp(v: float) -> str:
    """The same red-to-green ramp the explorer grid uses, so the two pages agree."""
    return f"hsl({v * 130} 55% 50% / {0.10 + 0.45 * v:.2f})"


def spark(points: list[tuple[float, float]], top: float) -> str:
    """An 11-point accuracy-versus-temperature sparkline, scaled to its own maximum.

    Per-row scaling rather than a shared ceiling, because the claim being made is about
    the *shape* of each curve -- flat or not -- and a shared ceiling flattens every row
    below the best one into an unreadable line along the axis.
    """
    w, h = 132, 26
    x = lambda t: 1 + t * (w - 2)
    y = lambda v: h - 1 - (v / top if top else 0) * (h - 4)
    d = " ".join(("M" if i == 0 else "L") + f"{x(t):.1f},{y(v):.1f}"
                 for i, (t, v) in enumerate(points))
    return (f"<svg viewBox='0 0 {w} {h}' class='spark'>"
            f"<line x1='1' y1='{h-1}' x2='{w-1}' y2='{h-1}' stroke='currentColor' opacity='.2'/>"
            f"<path d='{d}' fill='none' stroke='currentColor' stroke-width='1.5' opacity='.85'/></svg>")


def spark_cell(points: list[tuple[float, float]]) -> str:
    """Sparkline plus the ceiling it is scaled to, so the shape cannot be misread."""
    top = max(v for _, v in points)
    if top == 0:
        return "<span class='na'>flat at 0.000</span>"
    return spark(points, top) + f"<span class='sub2'>peak {top:.3f}</span>"


def stability_table(S: dict) -> str:
    """Per-item outcome across the whole temperature grid -- the finding-1 evidence."""
    rows = []
    for task in ("task1", "task2"):
        for m in S["models"]:
            st, pts = S["stable"].get((m, task)), S["curve"].get((m, task))
            if not st:
                continue
            rows.append([{"task1": "Reversal", "task2": "Division"}[task], model_cell(m),
                         f"<span class='num'>{st['never']}</span>",
                         f"<span class='num'>{st['always']}</span>",
                         f"<span class='num'>{st['sometimes']}</span>",
                         spark_cell(pts) if pts else ""])
    return (table(["Task", "Model", "never right", "always right", "sometimes",
                   "accuracy across the sweep"], rows)
            + "<p class='sub2'>Counts cover the 10 zero-shot queries for each task. "
              "Each sparkline runs t=0.0 → 1.0 left to right and is scaled to its own peak, "
              "to show its shape. Heights cannot be compared across rows.</p>")


def taxonomy_table(S: dict, task: str, kinds: tuple) -> str:
    rows = []
    for m in S["models"]:
        c = S["tax"].get((m, task))
        if not c:
            continue
        total = sum(c.values())
        top = c.most_common(1)[0][0] if total else ""
        cells = [f"<span class='{'lead' if k == top else ''} num'>{c[k]}</span>" if c[k]
                 else "<span class='na'>·</span>" for k in kinds]
        rows.append([model_cell(m)] + cells)
    return table(["Model"] + [k.replace("_", " ") for k in kinds], rows)


def pattern_table(S: dict) -> str:
    """Task-1 accuracy per case pattern: ten strings, so 1.00 and 0.00 are single items."""
    pats = sorted({p for (_, p) in S["pattern"]})
    rows = []
    for m in S["models"]:
        cells = []
        for p in pats:
            hit, n = S["pattern"].get((m, p), [0, 0])
            cells.append(f"<td class='num' style='background:{ramp(hit / n if n else 0)}'>"
                         + (f"{hit / n:.2f}" if n else "·") + "</td>")
        rows.append(f"<td>{model_cell(m)}</td>" + "".join(cells))
    head = "".join(f"<th class='mono rot'>{esc(p)}</th>" for p in pats)
    body = "".join(f"<tr>{r}</tr>" for r in rows)
    return (f"<div class='scroll'><table><tr><th>Model</th>{head}</tr>{body}</table></div>")


def band_table(S: dict) -> str:
    """Zero-shot accuracy at each complexity band, both tasks."""
    rows = []
    for m in S["models"]:
        cells = []
        for task in ("task1", "task2"):
            for b in (5, 8):
                s = S["band"].get((m, task, b))
                cells.append(f"<td class='num' style='background:{ramp(s['acc'])}'>{s['acc']:.3f}</td>"
                             if s else "<td class='na'>–</td>")
        rows.append(f"<td>{model_cell(m)}</td>" + "".join(cells))
    return ("<div class='scroll'><table>"
            "<tr><th rowspan=2>Model</th><th colspan=2>Reversal (length)</th>"
            "<th colspan=2>Division (places)</th></tr>"
            "<tr><th>5</th><th>8</th><th>5</th><th>8</th></tr>"
            + "".join(f"<tr>{r}</tr>" for r in rows) + "</table></div>")


# --- prose ----------------------------------------------------------------------------
# Authored text. Numbers are {references}; nothing here is a typed-in result.

PROBLEM = """
<p>This study tests seven open-weight instruction-tuned language models on two tasks
with exact answers that can be computed with a calculator or a short Python program:</p>
<ol>
<li><b>Character-by-character reversal.</b> Given a mixed-case alphabetic string of length
5 or 8, return its characters in reverse order. An answer is <i>valid</i> if it has the
same length as the input, and <i>correct</i> if it matches the exact reversal.</li>
<li><b>Decimal division with rounding.</b> Given two integers, return their quotient to
exactly 5 or 8 decimal places, rounded half-up.</li>
</ol>
<p>Both tasks depend only on the input. They require no world knowledge or judgement,
and their answers can be generated and checked without a model. This gives us an unlimited
supply of test cases with independently computed ground truth, without relying on answers
a model may have seen during training. The tasks test whether models can carry out exact
operations. We examine the errors they make and whether model size, temperature, or
prompting changes those errors.</p>
<p>The experiments vary <b>model size</b> (1.54B to 32.8B, across four organisations),
<b>sampling temperature</b> ({n_temps} points from 0.0 to 1.0), and <b>prompting
strategy</b> (zero-shot, few-shot, chain-of-thought, and verbose versions of the latter
two). There are {n_trials} graded trials in total.</p>
"""

ASSUMPTIONS = """
<p>The following design choices were set before collecting the data.</p>
<dl>
<dt>Ground truth, grading, and statistics are computed independently of model output.</dt>
<dd>Queries and reference answers come from a committed seed. Division answers are computed
with both <code>decimal.Decimal</code> using <code>ROUND_HALF_UP</code> and
<code>fractions.Fraction</code>. The report build checks that the two answers agree and
stops if they do not. Only the answer cells contain model-generated values.</dd>

<dt>Truncated responses are excluded from accuracy calculations.</dt>
<dd>Responses cut off by the token budget and chain-of-thought responses without a
<code>FINAL:</code> marker are excluded from the denominator. Scoring them as wrong would
mix failures in the evaluation code with model errors. A stop sequence caused this problem
in one run, as described in <a href="#f-harness">finding 8</a>.</dd>

<dt>Answers are graded both strictly and after normalisation.</dt>
<dd>Strict grading uses the literal response. For example, a preamble makes a reversal
answer invalid because the response no longer matches the input length. Normalisation
removes code fences, quotes, markdown, and a leading "The answer is:". The main results use
normalised scores. Strict scores are retained to distinguish formatting errors from
computational errors.</dd>

<dt>Sampling settings are fixed across models, apart from temperature.</dt>
<dd><code>top_p</code>, <code>top_k</code>, <code>repeat_penalty</code>, and
<code>num_ctx</code> are set explicitly. Ollama's defaults vary by model, so using them
would have introduced two additional variables into the size comparison. The token budget
is a documented exception: it varies by task and prompting strategy because
chain-of-thought responses need more space to show their work.</dd>

<dt>Few-shot examples come from a separate pool.</dt>
<dd>The examples use a different seed, are checked for overlap with the test set, and match
the test item's complexity band. This prevents an example from supplying the test answer
or making the demonstrated task easier by using a shorter input.</dd>

<dt>Division problems exclude fractions that may be familiar from training.</dt>
<dd>Generation rejects candidates that reduce to well-known fractions such as 22/7,
355/113, and 1/7. Otherwise, a correct response could come from recalling a familiar
expansion rather than computing the quotient.</dd>

<dt>All models are self-hosted, with the backend recorded for each run.</dt>
<dd>Ollama runs either on the laptop or on a campus A100 reached through an SSH tunnel.
Both connections appear as <code>localhost</code> to the client, so each trace header
records the machine used. Accuracy is compared across backends; wall-clock timings are
not compared.</dd>
</dl>
"""

FINDINGS = [
("f-temp", "Accuracy depends more on the item than on temperature.",
 """
<p>Accuracy stays nearly flat for every model on both tasks across the {n_temps}
temperatures, from greedy decoding to 1.0. The individual query results explain this
pattern: most items are answered correctly at every temperature or incorrectly at every
temperature. Few fall between those groups.</p>
{T_STABILITY}
<p>The middle three columns show how often an item's outcome changes across the sweep.
For <span class="mono">qwen3-32b</span> on division,
{stab qwen3-32b task2 always} of 10 items are correct at all eleven temperatures,
{stab qwen3-32b task2 never} are wrong throughout, and
{stab qwen3-32b task2 sometimes} have mixed outcomes. These results suggest that accuracy
on this test set depends much more on the item than on the decoding temperature.</p>
<p>Temperature therefore offers little room for improvement here. An aggregate temperature
sweep alone would miss the differences between items. The exceptions occur among models
with accuracy just above zero. For example, <span class="mono">llama3.1-8b</span>'s
reversal accuracy falls from its greedy value towards zero as temperature rises. Sampling
appears to move it away from an answer it can occasionally produce, while models that
consistently fail show little change.</p>
"""),

("f-scale", "Larger models do better at division, but reversal is less consistent.",
 """
<p>Model size has a different relationship with accuracy on the two tasks.</p>
<h4>Division accuracy rises sharply above 7.25B</h4>
{T_TASK2}
<p>The {floor_models} models at or below 7.25B score <b>0.000</b> across
{floor_trials} trials covering every temperature and both prompting arms. Above that size,
accuracy increases monotonically, reaching {acc qwen3-32b task2 zeroshot} at 32.8B.
Within this set of models, division accuracy shows a sharp threshold followed by steady
improvement.</p>
<h4>Reversal accuracy does not follow model size</h4>
{T_TASK1}
<p>Below the largest model, size tells us little about reversal accuracy.
<span class="mono">gemma3-4b</span> ({acc gemma3-4b task1 zeroshot}) scores higher than
<span class="mono">mistral-7b</span> ({acc mistral-7b task1 zeroshot}) and
<span class="mono">llama3.1-8b</span> ({acc llama3.1-8b task1 zeroshot}). Meanwhile,
<span class="mono">qwen2.5-1.5b</span> and <span class="mono">mistral-7b</span> both score
zero despite a 5.7B parameter difference. The 32.8B model is clearly ahead, but even its
best reversal score, {acc qwen3-32b task1 cot}, is well below its division score.
The item-level results below also limit how much we can infer from the ranking of the
smaller models.</p>
"""),

("f-items", "Two strings account for a model's entire reversal score.",
 """
<p>With only ten test strings, a few items can determine a model's overall score. The table
below groups reversal accuracy by case pattern, which in this small sample is close to
grouping by individual string.</p>
{T_PATTERN}
<p><span class="mono">gemma3-4b</span>'s accuracy of
{acc gemma3-4b task1 zeroshot} comes from {stab gemma3-4b task1 always} string it always
gets right and {stab gemma3-4b task1 sometimes} it usually gets right. The other
{stab gemma3-4b task1 never} are never correct across the 550 trials. The models in the
middle of the size range follow a similar pattern: they succeed on a few strings and
consistently fail on the rest.</p>
<p>The higher score of the 4B model therefore depends on which strings entered the sample;
it does not establish better reversal ability in general. Only
<span class="mono">qwen3-32b</span>, with {stab qwen3-32b task1 always} consistently
correct items and {stab qwen3-32b task1 sometimes} partly correct items, shows success
across enough strings to suggest a broader ability to reverse them. At this sample size,
aggregate accuracy is insufficient on its own. The individual item results need to be
shown alongside it.</p>
"""),

("f-length", "Longer strings are harder for some models, but the sample is small.",
 """
{T_BAND}
<p>Both Gemma models lose most of their reversal accuracy when string length increases
from 5 to 8 characters: {band gemma3-4b task1 5} to {band gemma3-4b task1 8} for the 4B
model, and {band gemma3-12b task1 5} to {band gemma3-12b task1 8} for the 12B model.
This suggests that five characters may already be close to their limit on this task.</p>
<p>However, <span class="mono">qwen2.5-7b</span> and
<span class="mono">llama3.1-8b</span> score higher on the longer strings, while
<span class="mono">qwen3-32b</span>'s accuracy barely changes. With five items per band,
individual string difficulty is hard to separate from length. These are observations from
the current sample, not evidence of a general length effect. A follow-up should use at
least an order of magnitude more items per band.</p>
"""),

("f-arith", "Division errors mostly come from incorrect arithmetic.",
 """
<p>The error breakdown helps distinguish incorrect quotients from presentation problems,
such as the wrong number of decimal places, extra commas, or scientific notation.</p>
{T_TAX2}
<p><code>wrong digits</code> means that the quotient is incorrect beyond a difference in
rounding convention. This category accounts for
{tax_share qwen2.5-1.5b task2 wrong_digits} of <span class="mono">qwen2.5-1.5b</span>'s
errors and {tax_share mistral-7b task2 wrong_digits} of
<span class="mono">mistral-7b</span>'s errors. The models below the threshold fail to
compute the quotient itself. Strict and normalised scores are identical in every zero-shot
and few-shot division cell, so formatting changes do not affect any of those scores.</p>
<p><span class="mono">qwen2.5-7b</span>, the smallest model above the threshold, makes
{tax qwen2.5-7b task2 rounding_error} <code>rounding error</code>s. These answers have the
correct quotient but round the final digit incorrectly. This pattern suggests that the
model can perform the division and sometimes makes a mistake at the rounding step. It
appears at the same size where division accuracy first becomes nonzero.</p>
"""),

("f-chars", "Most reversal errors change the characters or the string length.",
 """
{T_TAX1}
<p>A <code>wrong order</code> error preserves the input characters but arranges them
incorrectly. Most reversal failures instead fall under <code>wrong length</code> or
<code>wrong chars</code>: the output changes the number or identity of the characters.
The models often produce a plausible-looking string without preserving the input's
character multiset. This is consistent with a difficulty in handling characters as separate
units when the input is represented through subword tokens.</p>
<p><span class="mono">gemma3-12b</span> is the only model whose most common failure is
<code>wrong order</code>, with {tax gemma3-12b task1 wrong_order} such errors. It more
often preserves the characters but places them incorrectly. That is a closer answer and
a different type of error from changing or dropping characters.</p>
"""),

("f-prompt", "Prompting helps some models and hurts others.",
 """
<p>Chain-of-thought produces the largest gain of any prompting strategy in the study.
For <span class="mono">qwen3-32b</span>, reversal accuracy rises from
{acc qwen3-32b task1 zeroshot} to {acc qwen3-32b task1 cot}, a change of
{delta qwen3-32b task1 cot zeroshot}. For <span class="mono">gemma3-4b</span>, it falls
from {acc gemma3-4b task1 zeroshot} to {acc gemma3-4b task1 cot}. The Gemma traces show
responses that list the characters in the correct reverse order, then put the original
string after <code>FINAL:</code>. The intermediate work is correct, but the final answer
does not carry it through.</p>
<p>Few-shot prompting also has mixed effects. It roughly doubles
<span class="mono">qwen2.5-7b</span>'s division accuracy, from
{acc qwen2.5-7b task2 zeroshot} to {acc qwen2.5-7b task2 fewshot}, while reducing
<span class="mono">gemma3-12b</span>'s by a third, from
{acc gemma3-12b task2 zeroshot} to {acc gemma3-12b task2 fewshot}. The verbose few-shot
prompt is the only strategy under which <span class="mono">gemma3-12b</span> exceeds
its zero-shot reversal score, reaching {acc gemma3-12b task1 fewshot_verbose}.
The examples, seeds, sampling settings, and token budget are unchanged. The same wording
change lowers <span class="mono">qwen3-32b</span>'s score from
{acc qwen3-32b task1 fewshot} to {acc qwen3-32b task1 fewshot_verbose}. That cell also
loses {invalid qwen3-32b task1 fewshot_verbose} of its 330 trials to truncation.
The evaluation bug described in <a href="#f-harness">finding 8</a> explains part of the
original drop, but the difference remains after the fix.</p>
<p>The effects are large and depend on the model. Each strategy helps some models and
hurts others, so a result such as "CoT improves task X by N%" needs to specify which model
was tested.</p>
"""),

("f-harness", "A stop-sequence bug was initially counted as model error.",
 """
<p>The non-CoT prompts request a single answer, so those runs stop generation at the first
newline. This works for most models, but <span class="mono">llama3.1-8b</span> sometimes
starts a few-shot reversal response with
<i>"To reverse the string <b>VAYCXPhA</b>, follow these steps:"</i>.
Generation then stops before the answer appears. These trials were initially scored as
wrong answers.</p>
<p>The problem affected 235 of 330 trials in that cell. A similar pattern appeared in
<span class="mono">qwen3-32b</span>'s verbose few-shot reversal responses. Although the
sampling settings, examples, seeds, and token budget matched the plain few-shot condition,
accuracy fell from {acc qwen3-32b task1 fewshot} to
{acc qwen3-32b task1 fewshot_verbose}. The size of the difference prompted a check of the
evaluation code, which explained part of the drop.</p>
<p>The fix classifies responses that become empty after normalisation as truncated, like
responses missing a <code>FINAL:</code> marker, and excludes them from the denominator.
Existing raw responses were re-graded without rerunning inference, which would have
produced different draws. Of 14,916 re-graded trials, 312 were reclassified as invalid,
with 0 changes to correctness verdicts. The wording effect on the 32B model became smaller
but remained after removing truncated responses. Its score now uses a smaller denominator.
The fix changes which trials count towards accuracy; it does not turn an incorrect answer
into a correct one.</p>
<p>Scoring truncated responses as wrong answers mixes evaluation failures with model
weaknesses. Checking the raw responses was necessary to separate the two.</p>
"""),
]

CONCLUSIONS = """
<ol>
<li>Reversal errors point to a problem with how models represent and preserve characters.
Most failures change the characters or their count, rather than just their order. Subword
representations offer a possible explanation for this pattern. Neither temperature changes
nor the prompts tested here reliably resolve it, and chain-of-thought makes reversal worse
for most models despite providing more room to work through the sequence.</li>

<li>The relationship between size and accuracy depends on the task. Division accuracy
becomes nonzero between 7.25B and 7.62B, then increases monotonically. Reversal has no useful
size ordering across a 20× parameter range until the largest model. The same seven models,
tested on the same day, therefore support different conclusions about scaling for the two
tasks.</li>

<li>Temperature has little effect across the eleven grid points and seven models tested.
The per-item breakdown explains why: an item's outcome usually stays the same throughout
the sweep. The full sweep supports this finding, while the item-level results show what
an aggregate comparison would miss.</li>

<li>Prompting effects depend on the model. Every strategy tested helps at least one model
and hurts at least one other, with changes larger than the differences between models.
Claims about a prompting technique should name the model on which the effect was measured.</li>

<li>Ten items per task are too few for aggregate accuracy to describe the behaviour well.
Two strings account for a mid-size model's entire reversal score. Individual responses and
error categories explain more than the average alone, which is why the explorer opens on
individual draws.</li>
</ol>
"""

LIMITATIONS = """
<ul>
<li>Each task has ten items, with five per complexity band. One item accounts for 10% of
the score, and finding 3 shows how strongly a few strings can affect the results.
Increasing the number of items is the most useful next step.</li>
<li>Most temperature points use three draws per item; the two reported temperatures use
ten. Self-consistency is computed alongside accuracy as supporting evidence, not as a
rule for selecting answers.</li>
<li>All models use Q4_K_M quantisation. Quantisation may affect character-level tasks,
but it was not varied here. The results compare these seven quantised checkpoints and
should not be extended to their model families as a whole.</li>
<li>This is not a controlled scaling study. The seven models come from four organisations
and two model generations. <span class="mono">qwen2.5-1.5b</span> to
<span class="mono">qwen2.5-7b</span> is the only clean size comparison within a family;
the other comparisons also differ in pretraining data, training recipe, and release date.</li>
<li>The 32B model runs with reasoning disabled so that its zero-shot answers, like those
of the other models, do not include intermediate work. With reasoning enabled, it produces
several hundred reasoning tokens, changing the comparison. That condition has not been
run.</li>
<li>Chain-of-thought division runs are incomplete for the largest model because the tunnel
to the GPU node dropped during the run. Cells marked <span class="na">*</span> have fewer
trials and remain provisional.</li>
<li>Runs use two backends, the laptop and the A100. Accuracy is compared across them;
wall-clock timings are not.</li>
</ul>
"""


# --- assembly -------------------------------------------------------------------------

SECTIONS = [("problem", "The problem"), ("assumptions", "Design and assumptions"),
            ("findings", "Findings"), ("conclusions", "Conclusions"),
            ("limits", "Limitations")]


def render(trials: list[dict]) -> str:
    """The analysis as one HTML block, with every figure resolved from the traces."""
    S = stats(trials)
    tables = {
        "{T_STABILITY}": stability_table(S),
        "{T_TASK1}": results_table(S, "task1"),
        "{T_TASK2}": results_table(S, "task2"),
        "{T_PATTERN}": pattern_table(S),
        "{T_BAND}": band_table(S),
        "{T_TAX1}": taxonomy_table(S, "task1", grade_kinds("task1")),
        "{T_TAX2}": taxonomy_table(S, "task2", grade_kinds("task2")),
    }

    def block(text: str) -> str:
        for k, v in tables.items():
            text = text.replace(k, v)
        return resolve(text, S)

    findings = "".join(
        f"<section id='{fid}' class='finding'><h3><span class='fnum'>{i}</span>{esc(title)}</h3>"
        f"{block(body)}</section>"
        for i, (fid, title, body) in enumerate(FINDINGS, 1))

    toc = "".join(f"<a href='#{fid}'>{i}. {esc(title)}</a>"
                  for i, (fid, title, _) in enumerate(FINDINGS, 1))

    return (
        f"<section id='problem'><h2>The problem</h2>{block(PROBLEM)}</section>"
        f"<section id='assumptions'><h2>Design and assumptions</h2>{block(ASSUMPTIONS)}</section>"
        f"<section id='findings'><h2>Findings</h2>"
        f"<nav class='toc'>{toc}</nav>{findings}</section>"
        f"<section id='conclusions'><h2>Conclusions</h2>{block(CONCLUSIONS)}</section>"
        f"<section id='limits'><h2>Limitations</h2>{block(LIMITATIONS)}"
        f"<p class='note'>Result placeholders are filled from the committed run files when "
        f"the report is built, so their values update after re-grading or adding trials. "
        f"Open the <b>Explorer</b> tab to read the individual responses behind the "
        f"results.</p></section>")


def grade_kinds(task: str) -> tuple:
    """The error types for a task, minus the ones that never occurred, so the table fits."""
    from src import grade as grading
    return grading.TASK1_ERRORS if task == "task1" else grading.TASK2_ERRORS
