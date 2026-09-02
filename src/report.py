"""Graded JSONL -> one self-contained HTML report. No external assets, no CDN."""

import html
import json
from collections import Counter, defaultdict
from pathlib import Path

from src import generate, grade as grading, sweep as sweep_mod
from src.utils import config, prompts, trace
from src.utils.constants import LADDER, MODEL_REGISTRY, TASK_NAMES, TASKS

CSS = """
:root{--bg:#fff;--fg:#1a1a1a;--muted:#666;--line:#ddd;--head:#f5f5f5;--bad:#c00;--ok:#0a7}
@media (prefers-color-scheme:dark){:root{--bg:#141414;--fg:#e8e8e8;--muted:#999;
 --line:#333;--head:#1e1e1e;--bad:#ff6b6b;--ok:#3ddc97}}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--fg);font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
 max-width:1100px;margin:0 auto;padding:2rem 1.25rem 6rem}
h1{font-size:1.9rem;margin:0 0 .3rem} h2{font-size:1.25rem;margin:2.5rem 0 .75rem;
 padding-bottom:.3rem;border-bottom:1px solid var(--line)} h3{font-size:1rem;margin:1.5rem 0 .5rem}
.sub{color:var(--muted);margin:0 0 2rem}
.scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:1rem 0}
table{border-collapse:collapse;font-size:13px;min-width:100%}
th,td{border:1px solid var(--line);padding:.4rem .55rem;text-align:left;white-space:nowrap}
th{background:var(--head);font-weight:600}
td.q{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;background:var(--head)}
td.cell{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.wrong{color:var(--bad)} .right{color:var(--ok)}
pre{background:var(--head);border:1px solid var(--line);border-radius:6px;padding:.75rem;
 overflow-x:auto;font-size:12.5px;white-space:pre-wrap}
.note{border-left:3px solid var(--line);padding:.1rem 0 .1rem .9rem;color:var(--muted)}
.todo{border-left:3px solid var(--bad);padding:.6rem .9rem;background:var(--head);border-radius:0 6px 6px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:1rem}
svg{max-width:100%;height:auto} .legend{font-size:12px;color:var(--muted)}
"""

W, H, PAD = 320, 190, 34


def esc(x) -> str:
    return html.escape(str(x))


def chart(series_map: dict, title: str) -> str:
    """A small multiple: temperature on x, 0..1 on y, one path per series."""
    colors = ["#2b7", "#37c", "#c53", "#93c", "#c93"]
    px = lambda t: PAD + t * (W - PAD - 10)
    py = lambda v: H - PAD - v * (H - PAD - 14)
    parts = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{esc(title)}">']
    parts.append(f'<line x1="{PAD}" y1="{py(0)}" x2="{W-10}" y2="{py(0)}" stroke="#888"/>'
                 f'<line x1="{PAD}" y1="{py(0)}" x2="{PAD}" y2="{py(1)}" stroke="#888"/>')
    for v in (0, 0.5, 1):
        parts.append(f'<text x="4" y="{py(v)+4}" font-size="9" fill="#888">{v:.1f}</text>')
    for t in (0.0, 0.5, 1.0):
        parts.append(f'<text x="{px(t)-7}" y="{H-14}" font-size="9" fill="#888">{t:.1f}</text>')
    for i, (label, points) in enumerate(series_map.items()):
        if not points:
            continue
        color = colors[i % len(colors)]
        d = " ".join(("M" if j == 0 else "L") + f"{px(t):.1f},{py(v):.1f}"
                     for j, (t, v) in enumerate(points))
        parts.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.8"/>')
        for t, v in points:
            parts.append(f'<circle cx="{px(t):.1f}" cy="{py(v):.1f}" r="2" fill="{color}"/>')
        parts.append(f'<text x="{PAD+4}" y="{12+i*11}" font-size="9" fill="{color}">{esc(label)}</text>')
    parts.append(f'<text x="{PAD}" y="{H-2}" font-size="9" fill="#888">temperature</text></svg>')
    return f'<figure style="margin:0"><figcaption class="legend">{esc(title)}</figcaption>{"".join(parts)}</figure>'


# --- data assembly --------------------------------------------------------------------

def modal_cell(trials) -> tuple[str, bool, int]:
    """(modal output, correct, n) for one table cell, per R6."""
    good = [t for t in trials if not t["invalid"]]
    if not good:
        return ("(no valid trial)", False, 0)
    modal, _ = Counter(t["normalized"] for t in good).most_common(1)[0]
    match = next(t for t in good if t["normalized"] == modal)
    return (modal or "(empty)", bool(match["correct_norm"]), len(good))


def table_html(task: str, trials, temps, models) -> str:
    """The 10 x 6 deliverable table. Red comes from the grade, never by hand."""
    items = generate.load(f"{task}_queries")
    by = defaultdict(list)
    for t in trials:
        if t["task"] == task and t["arm"] == "zeroshot" and not t.get("ladder"):
            by[(t["model"], t["temperature"], t["qid"])].append(t)

    head = "".join(f"<th>{esc(MODEL_REGISTRY[m]['full_name'])}<br><span class='legend'>t={t}</span></th>"
                   for m in models for t in temps)
    rows = []
    for item in items:
        if task == "task1":
            label = f"{item['qid']}: reverse {item['s']} (l={item['l']})"
        else:
            label = f"{item['qid']}: {item['a']} / {item['b']} @ {item['places']} dp"
        cells = []
        for m in models:
            for t in temps:
                text, ok, n = modal_cell(by.get((m, t, item["qid"]), []))
                klass = "right" if ok else "wrong"
                cells.append(f"<td class='cell {klass}' title='modal of {n} draws'>{esc(text)}</td>")
        rows.append(f"<tr><td class='q'>{esc(label)}</td>{''.join(cells)}"
                    f"<td class='cell'>{esc(item['gold'])}</td></tr>")
    return (f"<div class='scroll'><table><tr><th>Query</th>{head}<th>Gold</th></tr>"
            + "".join(rows) + "</table></div>")


def summary_html(trials, temps, models) -> str:
    """Accuracy, validity and self-consistency per model, task and band."""
    cell_map = sweep_mod.cells(trials)
    rows = []
    for m in models:
        for task in TASKS:
            for band in sorted({b for (mm, tk, b, _) in cell_map if mm == m and tk == task}):
                for t in temps:
                    s = cell_map.get((m, task, band, t))
                    if not s:
                        continue
                    rows.append(f"<tr><td>{esc(m)}</td><td>{esc(task)}</td><td>{band}</td>"
                                f"<td>{t}</td><td>{s['accuracy']:.2f}</td>"
                                f"<td>{s['self_consistency']:.2f}</td><td>{s['n']}</td>"
                                f"<td>{s['invalid']}</td></tr>")
    return ("<div class='scroll'><table><tr><th>Model</th><th>Task</th><th>Band</th>"
            "<th>Temp</th><th>Accuracy</th><th>Self-consistency</th><th>Valid trials</th>"
            "<th>Invalid</th></tr>" + "".join(rows) + "</table></div>")


def taxonomy_html(trials, models) -> str:
    """Error-type counts. The wrong_digits / rounding_error split is the interesting one."""
    out = []
    for task in TASKS:
        kinds = grading.TASK1_ERRORS if task == "task1" else grading.TASK2_ERRORS
        head = "".join(f"<th>{esc(k)}</th>" for k in kinds)
        rows = []
        for m in models:
            counts = Counter(t["error_type"] for t in trials
                             if t["model"] == m and t["task"] == task and t["arm"] == "zeroshot")
            rows.append(f"<tr><td>{esc(m)}</td>"
                        + "".join(f"<td>{counts.get(k, 0)}</td>" for k in kinds) + "</tr>")
        out.append(f"<h3>{esc(TASK_NAMES[task])}</h3><div class='scroll'><table>"
                   f"<tr><th>Model</th>{head}</tr>{''.join(rows)}</table></div>")
    return "".join(out)


def prompting_html(trials, models) -> str:
    """Zero-shot vs few-shot vs CoT, with the section 4.6 predictions stated up front."""
    rows = []
    for m in models:
        for task in TASKS:
            cells = []
            for arm in ("zeroshot", "fewshot", "cot"):
                group = [t for t in trials if t["model"] == m and t["task"] == task
                         and t["arm"] == arm]
                good = [t for t in group if not t["invalid"]]
                acc = sum(t["correct_norm"] for t in good) / len(good) if good else None
                val = sum(t["valid_norm"] for t in good) / len(good) if good else None
                cells.append(f"<td>{'-' if acc is None else f'{acc:.2f}'}</td>"
                             f"<td>{'-' if val is None else f'{val:.2f}'}</td>"
                             f"<td>{len(group) - len(good)}</td>")
            rows.append(f"<tr><td>{esc(m)}</td><td>{esc(task)}</td>{''.join(cells)}</tr>")
    return ("<div class='scroll'><table><tr><th rowspan=2>Model</th><th rowspan=2>Task</th>"
            "<th colspan=3>Zero-shot</th><th colspan=3>Few-shot</th><th colspan=3>CoT</th></tr>"
            "<tr>" + "<th>acc</th><th>valid</th><th>inv</th>" * 3 + "</tr>"
            + "".join(rows) + "</table></div>")


def tokens_html() -> str:
    """Section 4.3: error rate against token count, not just against length."""
    path = Path("data/tokens.json")
    if not path.exists():
        return "<p class='note'>Not measured yet — run <code>main.py tokens</code>.</p>"
    rows = json.loads(path.read_text())
    body = "".join(f"<tr><td>{esc(r['model'])}</td><td class='cell'>{esc(r['s'])}</td>"
                   f"<td>{r['l']}</td><td>{r['n_tokens']}</td><td>{r['chars_per_token']}</td>"
                   f"<td class='cell'>{esc(r['case_pattern'])}</td></tr>" for r in rows)
    return ("<div class='scroll'><table><tr><th>Model</th><th>String</th><th>l</th>"
            f"<th>Tokens</th><th>Chars/token</th><th>Case</th></tr>{body}</table></div>")


def models_html(models) -> str:
    """Deliverable (1), generated from the registry so it cannot drift from the runs."""
    try:
        info = json.loads(Path("data/models.json").read_text())
    except FileNotFoundError:
        info = {}
    rows = []
    for m in models:
        e = {**MODEL_REGISTRY[m], **info.get(m, {})}
        rows.append(
            f"<tr><td>{esc(e['full_name'])}</td><td>{esc(e['org'])}</td><td>{esc(e['params'])}</td>"
            f"<td>{esc(e['quantization'])}</td><td class='cell'>{esc(e['ollama_tag'])}</td>"
            f"<td class='cell' style='white-space:normal;word-break:break-all'>{esc((e.get('digest') or '')[:16])}</td>"
            f"<td><a href='{esc(e['url'])}'>model card</a></td></tr>")
    defaults = "".join(
        f"<h3>{esc(MODEL_REGISTRY[m]['full_name'])} — default hyperparameters</h3>"
        f"<pre>{esc(info.get(m, {}).get('defaults') or 'run main.py models to capture')}</pre>"
        for m in models)
    return ("<div class='scroll'><table><tr><th>Model</th><th>Organisation</th><th>Params</th>"
            "<th>Quantisation</th><th>Ollama tag</th><th>Digest</th><th>Source</th></tr>"
            + "".join(rows) + "</table></div>" + defaults)


def method_html() -> str:
    t1 = generate.load("task1_queries")[0]
    t2 = generate.load("task2_queries")[0]
    pool = generate.load("fewshot_pool")
    blocks = []
    for task, item in (("task1", t1), ("task2", t2)):
        for arm in ("zeroshot", "fewshot", "cot"):
            shots = prompts.shots_for(pool, task, item, config.N_SHOTS) if arm == "fewshot" else None
            blocks.append(f"<h3>{esc(TASK_NAMES[task])} — {arm}</h3>"
                          f"<pre>{esc(prompts.build(task, arm, item, shots))}</pre>")
    return (f"<pre>{esc(json.dumps(config.frozen(), indent=2))}</pre>" + "".join(blocks))


TODO = ("<div class='todo'><strong>Write this yourself.</strong> Deliverable (5) asks you "
        "to critique any LLM used to reason about your results; the cleanest way to satisfy "
        "it is not to have used one here. Read the tables above and write the observations "
        "in your own words.</div>")


def build(out_path="report.html") -> Path:
    headers, trials = trace.load_all()
    models = [m for m in LADDER if any(h["model"] == m for h in headers)] or list(LADDER)
    try:
        decision = json.loads(Path("data/sweep.json").read_text())["decision"]
        temps = tuple(decision["pair"])
    except FileNotFoundError:
        decision, temps = None, (config.TEMP_GRID[0], config.TEMP_GRID[-1])

    cell_map = sweep_mod.cells(trials)
    charts = []
    for m in models:
        for task in TASKS:
            bands = sorted({b for (mm, tk, b, _) in cell_map if mm == m and tk == task})
            series = {}
            for band in bands:
                pts = [(t, s["accuracy"]) for t, s in
                       sweep_mod.curve(cell_map, model=m, task=task, band=band)]
                if pts:
                    series[f"acc l={band}"] = pts
                pts = [(t, s["self_consistency"]) for t, s in
                       sweep_mod.curve(cell_map, model=m, task=task, band=band)]
                if pts:
                    series[f"cons l={band}"] = pts
            if series:
                charts.append(chart(series, f"{m} — {TASK_NAMES[task]}"))

    sweep_note = ("<p class='note'>No sweep data yet — run <code>main.py pilot</code>.</p>"
                  if decision is None else
                  f"<p>Pooled curve shape: <strong>{esc(decision['shape'])}</strong>"
                  + (f", knee between t={decision['knee'][0]} and t={decision['knee'][1]}"
                     if decision.get("knee") else "")
                  + f". The rule in <code>config.INFLECTION_CURVE</code> "
                    f"(<code>{esc(config.INFLECTION_CURVE)}</code>) selected "
                    f"<strong>t={temps[0]}</strong> and <strong>t={temps[1]}</strong> as the two "
                    f"reported settings, applied identically to all three models.</p>")

    sections = [
        ("1. Models", models_html(models)),
        ("2. Method", "<p class='note'><strong>Ground-truth invariant.</strong> No LLM output "
         "enters the ground truth, the grading, or the statistics at any point. Every query and "
         "every gold answer is generated by <code>src/generate.py</code> from a committed seed; "
         "Task 2 answers are computed twice, by <code>decimal.Decimal</code> and by "
         "<code>fractions.Fraction</code>, and asserted equal. The only LLM-produced values in "
         "this report are the cells of the two result tables.</p>" + method_html()),
        ("3. Temperature sweep", sweep_note + f"<div class='grid'>{''.join(charts)}</div>"),
        (f"4. Task 1: {TASK_NAMES['task1']}", table_html("task1", trials, temps, models)),
        (f"5. Task 2: {TASK_NAMES['task2']}", table_html("task2", trials, temps, models)),
        ("6. Accuracy, validity and self-consistency", summary_html(trials, temps, models)),
        ("7. Error taxonomy", taxonomy_html(trials, models)),
        ("8. Supplementary complexity ladder", "<p class='note'>Run "
         "<code>main.py run --ladder</code> to populate.</p>"),
        ("9. Tokenization", tokens_html()),
        ("10. Prompting comparison", "<p class='note'>Predictions registered before the run: "
         "(a) CoT helps Task 2 more than Task 1; (b) few-shot raises validity more than "
         "correctness on Task 1.</p>" + prompting_html(trials, models)),
        ("11. Cross-model analysis", TODO),
        ("12. Per-model cross-task analysis", TODO),
        ("13. Self-critique", TODO),
    ]
    body = "".join(f"<h2>{esc(t)}</h2>{c}" for t, c in sections)
    n_trials = len(trials)
    doc = (f"<!doctype html><html><head><meta charset='utf-8'>"
           f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
           f"<title>CS6220 HW1 — LLM Contamination Tasks</title><style>{CSS}</style></head><body>"
           f"<h1>CS6220 BDS HW1 — Character Reversal and Decimal Division</h1>"
           f"<p class='sub'>Three self-hosted models, {len(config.TEMP_GRID)}-point temperature "
           f"sweep, {n_trials} graded trials. Wrong answers in red.</p>{body}</body></html>")
    path = Path(out_path)
    path.write_text(doc)
    return path
