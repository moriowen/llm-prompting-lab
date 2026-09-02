"""Runs -> one self-contained interactive page. Open it in a browser; no server needed."""

import json
from pathlib import Path

from src import generate
from src.utils import trace
from src.utils.constants import MODEL_REGISTRY, TASK_NAMES

# Raw responses are the interesting part of a failed trial, but a CoT trace can run to
# thousands of characters and there are thousands of trials. 600 is enough to see how a
# response went wrong without the page growing to tens of megabytes.
RAW_CHARS = 600


def collect() -> dict:
    """Everything the page needs, with short keys because this is embedded verbatim."""
    _, trials = trace.load_all()
    # The ladder reuses qids for different queries, so it cannot share a key with the
    # main set. Treating it as its own "task" keeps every downstream view -- bands,
    # curves, grid, inspector -- working unchanged, with the ladder lengths as bands.
    queries = {}
    ladder = generate.load("ladder_queries")
    sets = {"task1": generate.load("task1_queries"), "task2": generate.load("task2_queries"),
            "task1@ladder": ladder["task1"], "task2@ladder": ladder["task2"]}
    for key, items in sets.items():
        task = key.split("@")[0]
        queries[key] = {
            q["qid"]: {
                "label": (f"reverse {q['s']}" if task == "task1"
                          else f"{q['a']} / {q['b']}"),
                "gold": q["gold"],
                "band": q["l"] if task == "task1" else q["places"],
                "meta": (q["case_pattern"] if task == "task1"
                         else f"{q['expansion']}, {q['magnitude']}, period {q['period']}"),
            }
            for q in items
        }
    rows = []
    for t in trials:
        key = t["task"] + ("@ladder" if t.get("ladder") else "")
        if t["qid"] not in queries.get(key, {}):
            continue
        raw = t.get("raw", "")
        rows.append({
            "m": t["model"], "k": key, "a": t["arm"], "T": t["temperature"],
            "q": t["qid"], "s": t["seed"], "o": t.get("normalized", ""),
            "c": int(bool(t.get("correct_norm"))), "cs": int(bool(t.get("correct"))),
            "e": t.get("error_type", ""), "v": int(bool(t.get("invalid"))),
            "r": raw[:RAW_CHARS] + ("…" if len(raw) > RAW_CHARS else ""),
        })
    names = {a: e["full_name"] for a, e in MODEL_REGISTRY.items()}
    labels = {**TASK_NAMES, **{f"{k}@ladder": f"{v} — ladder" for k, v in TASK_NAMES.items()}}
    return {"trials": rows, "queries": queries, "names": names, "tasks": labels}


PAGE = r"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>HW1 run explorer</title><style>
:root{--bg:#fff;--fg:#1a1a1a;--muted:#777;--line:#e0e0e0;--head:#f6f6f6;--bad:#c62828;--ok:#1b7f5a;--accent:#37c}
@media (prefers-color-scheme:dark){:root{--bg:#141414;--fg:#e9e9e9;--muted:#8d8d8d;--line:#2e2e2e;--head:#1c1c1c;--bad:#ff6b6b;--ok:#3ddc97;--accent:#6aa9ff}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
header{padding:1.2rem 1.5rem .8rem;border-bottom:1px solid var(--line)}
h1{margin:0;font-size:1.15rem;font-weight:600}
.sub{color:var(--muted);font-size:.82rem;margin-top:.2rem}
main{padding:1.2rem 1.5rem 5rem;max-width:1200px;margin:0 auto}
.bar{display:flex;flex-wrap:wrap;gap:.55rem;align-items:center;margin:.9rem 0 1.3rem}
select,button{font:inherit;background:var(--bg);color:var(--fg);border:1px solid var(--line);
 border-radius:6px;padding:.32rem .5rem}
button.tab{cursor:pointer}
button.tab[aria-pressed=true]{background:var(--fg);color:var(--bg);border-color:var(--fg)}
label{color:var(--muted);font-size:.8rem;margin-right:.15rem}
.stats{display:flex;flex-wrap:wrap;gap:1.6rem;margin:0 0 1.4rem;padding:.85rem 1rem;
 background:var(--head);border:1px solid var(--line);border-radius:8px}
.stat b{display:block;font-size:1.35rem;font-weight:600;line-height:1.2}
.stat span{color:var(--muted);font-size:.74rem;text-transform:uppercase;letter-spacing:.04em}
h2{font-size:.95rem;margin:1.8rem 0 .6rem;font-weight:600}
.hint{color:var(--muted);font-size:.8rem;margin:-.3rem 0 .7rem}
.scroll{overflow-x:auto}
table{border-collapse:collapse;font-size:12.5px}
th,td{border:1px solid var(--line);padding:.3rem .45rem;text-align:center;white-space:nowrap}
th{background:var(--head);font-weight:600}
td.q{text-align:left;font-family:ui-monospace,Menlo,monospace;background:var(--head);position:sticky;left:0}
td.cell{cursor:pointer;font-variant-numeric:tabular-nums;min-width:38px}
td.cell:hover{outline:2px solid var(--accent);outline-offset:-2px}
td.sel{outline:2px solid var(--accent);outline-offset:-2px}
.mono{font-family:ui-monospace,Menlo,monospace}
.wrong{color:var(--bad)}.right{color:var(--ok)}
#panel{margin-top:1rem;border:1px solid var(--line);border-radius:8px;padding:.9rem 1rem;background:var(--head)}
#panel h3{margin:0 0 .5rem;font-size:.86rem}
.draw{border-top:1px solid var(--line);padding:.5rem 0;font-size:12.5px}
.draw:first-of-type{border-top:0}
pre{margin:.35rem 0 0;white-space:pre-wrap;word-break:break-word;font-size:11.5px;
 color:var(--muted);max-height:12rem;overflow:auto}
.pill{display:inline-block;padding:.05rem .4rem;border:1px solid var(--line);border-radius:99px;
 font-size:11px;color:var(--muted);margin-left:.35rem}
.tax{display:flex;flex-wrap:wrap;gap:.4rem}
.tax div{border:1px solid var(--line);border-radius:6px;padding:.3rem .55rem;font-size:12px}
.tax b{font-variant-numeric:tabular-nums}
svg{max-width:100%;height:auto;overflow:visible}
.empty{color:var(--muted);padding:2rem 0}
</style></head><body>
<header><h1>HW1 run explorer</h1>
<div class="sub" id="sub"></div></header>
<main>
<div class="bar">
  <label>model</label><select id="m"></select>
  <label>task</label><select id="k"></select>
  <label>arm</label><select id="a"></select>
  <label>grading</label>
  <button class="tab" id="gn" aria-pressed="true">normalised</button>
  <button class="tab" id="gs" aria-pressed="false">strict</button>
</div>
<div class="stats" id="stats"></div>
<h2>Accuracy and self-consistency across temperature</h2>
<div class="hint">One colour per complexity band — <b>solid = accuracy</b>, <b>dashed = self-consistency</b> (the share of the k draws matching the modal draw).</div>
<div id="chart"></div>
<h2>Query × temperature</h2>
<div class="hint">Each cell is one query at one temperature, shaded by the share of its k draws that were correct. Click a cell to read the raw responses.</div>
<div class="scroll" id="grid"></div>
<div id="panel"><h3>Click a cell to inspect its draws</h3></div>
<h2>Error taxonomy</h2>
<div class="tax" id="tax"></div>
</main>
<script id="data" type="application/json">__DATA__</script>
<script>
const D = JSON.parse(document.getElementById('data').textContent);
const $ = id => document.getElementById(id);
let normalised = true, sel = null;

const uniq = (f) => [...new Set(D.trials.map(f))];
const temps = uniq(t => t.T).sort((a, b) => a - b);
const shownTemps = rows => [...new Set(rows.map(t => t.T))].sort((a, b) => a - b);
const KEY = 'hw1-ui-state';
// Keep filters and the selected cell when the user reloads to fetch fresh data.
// Anything no longer present in the data is dropped rather than restored blindly.
function save() {
  try { sessionStorage.setItem(KEY, JSON.stringify(
    {m: $('m').value, k: $('k').value, a: $('a').value, n: normalised, sel})); } catch (e) {}
}
function restore() {
  let s = null;
  try { s = JSON.parse(sessionStorage.getItem(KEY) || 'null'); } catch (e) {}
  if (!s) return;
  ['m', 'k', 'a'].forEach(id => { $(id).value = s[id]; });
  options();  // drops anything the restored model no longer offers
  normalised = s.n !== false;
  $('gn').ariaPressed = String(normalised); $('gs').ariaPressed = String(!normalised);
  if (s.sel && (D.queries[$('k').value] || {})[s.sel.split('|')[0]]) sel = s.sel;
}

function fill(el, values, counts, labels) {
  const keep = el.value;
  el.innerHTML = values.map(v => `<option value="${v}">${labels ? labels[v] || v : v}`
    + ` (${counts[v]})</option>`).join('');
  // Keep the current choice when it survives the new filter, so changing model does
  // not silently throw away the task and arm you were looking at.
  el.value = values.includes(keep) ? keep : (values[0] ?? '');
}
function tally(rows, f) {
  const c = {};
  rows.forEach(t => c[f(t)] = (c[f(t)] || 0) + 1);
  return c;
}
// The three selectors are dependent: a model that was only ever run zero-shot has no
// CoT arm to offer. Each list is rebuilt from the trials that survive the choices to
// its left, so every combination the page offers has data behind it.
function options() {
  const byModel = tally(D.trials, t => t.m);
  fill($('m'), Object.keys(byModel).sort(), byModel, D.names);
  const forModel = D.trials.filter(t => t.m === $('m').value);
  const byTask = tally(forModel, t => t.k);
  fill($('k'), Object.keys(byTask).sort(), byTask, D.tasks);
  const forTask = forModel.filter(t => t.k === $('k').value);
  const byArm = tally(forTask, t => t.a);
  fill($('a'), Object.keys(byArm).sort(), byArm);
}
options();

const ok = t => (normalised ? t.c : t.cs) === 1;
function view() {
  return D.trials.filter(t => t.m === $('m').value && t.k === $('k').value && t.a === $('a').value);
}
// Invalid trials (truncated, or a CoT answer with no FINAL: marker) are harness
// failures, not wrong answers, so they stay out of every denominator.
const valid = rows => rows.filter(t => !t.v);

function consistency(rows) {
  const byQ = {};
  valid(rows).forEach(t => (byQ[t.q] = byQ[t.q] || []).push(t.o));
  const each = Object.values(byQ).map(os => {
    const c = {}; os.forEach(o => c[o] = (c[o] || 0) + 1);
    return Math.max(...Object.values(c)) / os.length;
  });
  return each.length ? each.reduce((a, b) => a + b, 0) / each.length : 0;
}
const accuracy = rows => { const v = valid(rows); return v.length ? v.filter(ok).length / v.length : 0; };

function stats() {
  const rows = view(), v = valid(rows);
  const cells = [
    ['trials', rows.length], ['valid', v.length],
    ['accuracy', (accuracy(rows) * 100).toFixed(1) + '%'],
    ['self-consistency', (consistency(rows) * 100).toFixed(1) + '%'],
    ['invalid', rows.length - v.length],
    ['temperatures', new Set(rows.map(t => t.T)).size],
  ];
  $('stats').innerHTML = cells.map(([l, x]) => `<div class="stat"><b>${x}</b><span>${l}</span></div>`).join('');
}

const W = 620, H = 230, P = 40;
function chart() {
  const rows = view(), meta = D.queries[$('k').value] || {};
  const bands = [...new Set(rows.map(t => meta[t.q].band))].sort((a, b) => a - b);
  if (!rows.length) { $('chart').innerHTML = '<div class="empty">No runs for this combination yet.</div>'; return; }
  const cols = shownTemps(rows);
  const px = t => P + (t / 1) * (W - P - 20), py = v => H - P - v * (H - P - 20);
  const colors = ['#37c', '#c53', '#2b7', '#93c'];
  let out = `<svg viewBox="0 0 ${W} ${H}">`;
  out += `<line x1="${P}" y1="${py(0)}" x2="${W - 20}" y2="${py(0)}" stroke="currentColor" opacity=".3"/>`;
  out += `<line x1="${P}" y1="${py(0)}" x2="${P}" y2="${py(1)}" stroke="currentColor" opacity=".3"/>`;
  [0, .5, 1].forEach(v => out += `<text x="8" y="${py(v) + 4}" font-size="10" fill="currentColor" opacity=".5">${v.toFixed(1)}</text>`);
  cols.forEach(t => out += `<text x="${px(t) - 8}" y="${H - 18}" font-size="10" fill="currentColor" opacity=".5">${t}</text>`);
  bands.forEach((band, i) => {
    const col = colors[i % colors.length];
    [['accuracy', accuracy, 'none'], ['consistency', consistency, '4 3']].forEach(([name, fn, dash]) => {
      const pts = cols.map(T => {
        const r = rows.filter(t => t.T === T && meta[t.q].band === band);
        return r.length ? [T, fn(r)] : null;
      }).filter(Boolean);
      if (!pts.length) return;
      const d = pts.map(([t, v], j) => (j ? 'L' : 'M') + px(t).toFixed(1) + ',' + py(v).toFixed(1)).join(' ');
      out += `<path d="${d}" fill="none" stroke="${col}" stroke-width="1.8" stroke-dasharray="${dash}"/>`;
      pts.forEach(([t, v]) => out += `<circle cx="${px(t).toFixed(1)}" cy="${py(v).toFixed(1)}" r="2.5" fill="${col}"/>`);
      if (dash === 'none') out += `<text x="${P + 6}" y="${13 + i * 11}" font-size="10" fill="${col}">band ${band}</text>`;
    });
  });
  out += `<text x="${W - 90}" y="${H - 2}" font-size="10" fill="currentColor" opacity=".5">temperature</text></svg>`;
  $('chart').innerHTML = out;
}

function shade(frac, n) {
  if (!n) return 'transparent';
  // A muted red-to-green ramp: the eye should find the cliff, not read exact values.
  const h = frac * 130;
  return `hsl(${h} 55% 50% / ${0.14 + 0.5 * Math.abs(frac - 0.5) * 2 * 0.7})`;
}
function grid() {
  const rows = view(), task = $('k').value, qs = Object.keys(D.queries[task] || {});
  if (!rows.length || !qs.length) {
    $('grid').innerHTML = `<div class="empty">No trials for ${$('m').value} · ${task} · ${$('a').value}.</div>`;
    return;
  }
  const cols = shownTemps(rows);
  let out = '<table><tr><th>Query</th>' + cols.map(t => `<th>${t}</th>`).join('') + '<th>Gold</th></tr>';
  qs.forEach(q => {
    const meta = D.queries[task][q];
    out += `<tr><td class="q" title="${meta.meta}">${q} · ${meta.label} <span class="pill">${meta.band}</span></td>`;
    cols.forEach(T => {
      const cell = rows.filter(t => t.q === q && t.T === T), v = valid(cell);
      const frac = v.length ? v.filter(ok).length / v.length : 0;
      const key = q + '|' + T;
      out += `<td class="cell ${sel === key ? 'sel' : ''}" data-k="${key}" style="background:${shade(frac, v.length)}">`
           + (v.length ? Math.round(frac * 100) + '' : '·') + '</td>';
    });
    out += `<td class="mono">${meta.gold}</td></tr>`;
  });
  $('grid').innerHTML = out + '</table>';
  $('grid').querySelectorAll('td.cell').forEach(td =>
    td.onclick = () => { sel = td.dataset.k; grid(); panel(); });
}

function panel() {
  const task = $('k').value, meta = sel && (D.queries[task] || {})[sel.split('|')[0]];
  if (!meta) { $('panel').innerHTML = '<h3>Click a cell to inspect its draws</h3>'; return; }
  const [q, T] = sel.split('|');
  const draws = view().filter(t => t.q === q && t.T === +T).sort((a, b) => a.s - b.s);
  $('panel').innerHTML = `<h3>${q} · ${meta.label} · t=${T} <span class="pill">gold ${meta.gold}</span>`
    + `<span class="pill">${meta.meta}</span></h3>`
    + (draws.length ? draws.map(t => `<div class="draw">
        <span class="mono ${ok(t) ? 'right' : 'wrong'}">${t.o || '(empty)'}</span>
        <span class="pill">seed ${t.s}</span><span class="pill">${t.e}</span>
        ${t.v ? '<span class="pill">invalid trial</span>' : ''}
        <pre>${t.r.replace(/[<&]/g, c => ({ '<': '&lt;', '&': '&amp;' }[c]))}</pre></div>`).join('')
      : '<div class="empty">No draws here.</div>');
}

function tax() {
  const counts = {};
  view().forEach(t => counts[t.e] = (counts[t.e] || 0) + 1);
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  $('tax').innerHTML = entries.length
    ? entries.map(([e, n]) => `<div>${e} <b>${n}</b></div>`).join('')
    : '<div class="empty">No trials.</div>';
}

function render() {
  if (!D.trials.length) {
    $('stats').innerHTML = '<div class="empty">No runs yet — run <code>main.py pilot</code>, then rebuild this page.</div>';
    ['chart', 'grid', 'tax', 'panel'].forEach(id => $(id).innerHTML = '');
    return;
  }
  stats(); chart(); grid(); panel(); tax(); save();
}
['m', 'k', 'a'].forEach(id => $(id).onchange = () => { sel = null; options(); render(); });
$('gn').onclick = () => { normalised = true; $('gn').ariaPressed = 'true'; $('gs').ariaPressed = 'false'; render(); };
$('gs').onclick = () => { normalised = false; $('gs').ariaPressed = 'true'; $('gn').ariaPressed = 'false'; render(); };
restore();
$('sub').textContent = `${D.trials.length} graded trials · ${uniq(t => t.m).length} model(s) · `
  + `${temps.length} temperatures · each selector shows its trial count, and only `
  + `combinations that have data`;
render();
</script></body></html>"""


def render() -> str:
    """The page as a string, with the current runs embedded."""
    # </script> inside a raw response would close the data block early.
    payload = json.dumps(collect(), separators=(",", ":")).replace("</", "<\\/")
    return PAGE.replace("__DATA__", payload)


def build(out_path="ui.html") -> Path:
    """Write the explorer with its data embedded."""
    path = Path(out_path)
    path.write_text(render())
    return path


def serve(port: int = 8765) -> None:
    """Serve the explorer, rebuilding from runs/ on every request."""
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = render().encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            # The point of this mode is freshness; a cached page defeats it.
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    print(f"serving http://localhost:{port} — reload the page to refresh data "
          "(ctrl-c to stop)")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
