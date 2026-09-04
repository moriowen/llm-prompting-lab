"""CLI. Every stage of the experiment is a subcommand here."""

import argparse
import json
import sys

from src import experiment, generate, ollama, sweep as sweep_mod, tokens as tokens_mod, verify
from src.utils import config
from src.utils.constants import ARMS, BACKEND, LADDER, MODEL_REGISTRY, OLLAMA_HOST, TASKS


def _models(arg: str | None) -> list[str]:
    if not arg or arg == "ladder":
        return list(LADDER)
    if arg == "all":
        return list(MODEL_REGISTRY)
    aliases = [a.strip() for a in arg.split(",")]
    unknown = [a for a in aliases if a not in MODEL_REGISTRY]
    if unknown:
        raise SystemExit(f"unknown model alias(es): {unknown}\nknown: {list(MODEL_REGISTRY)}")
    return aliases


def _temps(arg: str | None) -> list[float]:
    if not arg or arg == "grid":
        return config.TEMP_GRID
    return [round(float(t), 3) for t in arg.split(",")]


def _csv(arg: str | None, allowed: tuple[str, ...]) -> list[str]:
    if not arg or arg == "all":
        return list(allowed)
    values = [v.strip() for v in arg.split(",")]
    unknown = [v for v in values if v not in allowed]
    if unknown:
        raise SystemExit(f"unknown value(s): {unknown}\nknown: {list(allowed)}")
    return values


def cmd_generate(args):
    """Regenerate data/*.json from the committed seeds."""
    rejected = generate.write()
    print("wrote data/*.json; candidates rejected during generation:", rejected)
    problems = verify.run()
    print("verify:", "clean" if not problems else problems)


def cmd_verify(args):
    """Re-derive everything from the seed and diff against committed data/."""
    problems = verify.run()
    if problems:
        print("\n".join(problems), file=sys.stderr)
        raise SystemExit(f"{len(problems)} ground-truth problem(s)")
    print("ground truth verified: seeds, gold answers (Decimal vs Fraction), "
          "few-shot disjointness, and committed data all agree")


def cmd_models(args):
    """Record digests and default hyperparameters for deliverable (1)."""
    try:
        present = ollama.installed()
    except Exception as e:
        raise SystemExit(f"cannot reach ollama: {e}")
    out = {}
    for alias, entry in MODEL_REGISTRY.items():
        tag = entry["ollama_tag"]
        here = tag in present
        row = {**entry, "installed": here, "digest": present.get(tag)}
        if here:
            info = ollama.show(tag)
            row["defaults"] = info.get("parameters", "")
            row["details"] = info.get("details", {})
        out[alias] = row
        mark = "installed" if here else "NOT PULLED"
        print(f"{alias:16} {tag:16} {mark:12} {row['digest'] or ''}")
    with open("data/models.json", "w") as f:
        json.dump(out, f, indent=2)
    print("\nwrote data/models.json (this file is deliverable (1)'s model table)")


def cmd_ping(args):
    """Check the configured ollama is reachable -- the tunnel is the usual thing broken."""
    print(f"backend={BACKEND}  host={OLLAMA_HOST}")
    try:
        present = ollama.installed()
    except Exception as e:
        raise SystemExit(f"unreachable: {e}\n"
                         "if this is PACE ICE: is the salloc still alive, is `ollama serve` "
                         "running on the compute node, and is the ssh -L tunnel open?")
    print(f"reachable; {len(present)} model(s) pulled there:")
    for tag, digest in sorted(present.items()):
        here = " <- in the ladder" if any(
            e["ollama_tag"] == tag and a in LADDER for a, e in MODEL_REGISTRY.items()) else ""
        print(f"  {tag:20} {digest[:19]}{here}")
    missing = [MODEL_REGISTRY[a]["ollama_tag"] for a in LADDER
               if MODEL_REGISTRY[a]["ollama_tag"] not in present]
    if missing:
        print("\nnot pulled on this backend: " + ", ".join(missing)
              + "\n  run on whichever machine serves this host: "
              + "; ".join(f"ollama pull {t}" for t in missing))


def cmd_run(args):
    """The experiment loop."""
    print(f"backend={BACKEND}  host={OLLAMA_HOST}")
    experiment.run(_models(args.models), _csv(args.tasks, TASKS), _csv(args.arms, ARMS),
                   _temps(args.temps), args.k, resume=not args.no_resume, ladder=args.ladder)


def cmd_pilot(args):
    """The day-2 pilot: full 11-point sweep, smallest model only, zero-shot."""
    print("pilot: qwen2.5-1.5b, both tasks, zero-shot, 11 temperatures, "
          f"k={args.k} -> {2 * 10 * 11 * args.k} calls")
    experiment.run(["qwen2.5-1.5b"], list(TASKS), ["zeroshot"], config.TEMP_GRID,
                   args.k, resume=not args.no_resume)
    cmd_sweep(args)


def cmd_sweep(args):
    """Build the curves and apply the decision rule."""
    r = sweep_mod.report(arm=getattr(args, "arm", "zeroshot"))
    if not r["pooled"]:
        raise SystemExit("no runs yet -- nothing to sweep")
    print(f"pooled curve ({r['decision']['curve']}), selection rule = {config.INFLECTION_CURVE}:")
    for temp, stats in r["pooled"]:
        bar = "#" * round(stats["accuracy"] * 40)
        print(f"  t={temp:<4} acc={stats['accuracy']:.3f} cons={stats['self_consistency']:.3f} "
              f"n={stats['n']:<5} {bar}")
    d = r["decision"]
    print(f"\nshape: {d['shape']}  range={d.get('range', 0):.3f}"
          + (f"  knee between {d['knee'][0]} and {d['knee'][1]} (drop {d['drop']:.3f})"
             if d.get("knee") else ""))
    print(f"chosen table temperatures: {d['pair'][0]} and {d['pair'][1]}")
    print("\nper (model, task, band):")
    for key, info in r["per_model"].items():
        print(f"  {key:34} {info['shape']:16} range={info['range']:.3f}"
              + (f" knee@{info['knee']}" if info["knee"] else ""))
    with open("data/sweep.json", "w") as f:
        json.dump({"pooled": r["pooled"], "decision": d,
                   "per_model": {k: v for k, v in r["per_model"].items()}}, f, indent=2)
    print("\nwrote data/sweep.json")


def cmd_topup(args):
    """Raise the two chosen table temperatures to k=10."""
    chosen = json.load(open("data/sweep.json"))["decision"]["pair"]
    print(f"topping up t={chosen[0]} and t={chosen[1]} to k={config.K_TABLE}")
    experiment.run(_models(args.models), list(TASKS), ["zeroshot"], list(chosen),
                   config.K_TABLE, resume=True)


def cmd_tokens(args):
    """Tokenization stats for section 4.3."""
    rows = []
    for alias in _models(args.models):
        rows += tokens_mod.measure(alias, ladder=args.ladder)
        print(f"{alias}: measured {len(rows)} strings")
    with open("data/tokens.json", "w") as f:
        json.dump(rows, f, indent=2)
    print("wrote data/tokens.json")


def cmd_ui(args):
    """Build the run explorer, or serve it live while a run is going."""
    from src import ui as ui_mod
    if args.serve:
        ui_mod.serve(args.port)
        return
    path = ui_mod.build(args.out)
    print(f"wrote {path} -- open it in a browser (no server needed); "
          f"it is a snapshot, so re-run this to pick up new trials")


def cmd_report(args):
    """Build the HTML report. Refuses to run on unverified ground truth."""
    from src import report as report_mod
    problems = verify.run()
    if problems:
        print("\n".join(problems), file=sys.stderr)
        raise SystemExit("ground truth failed verification -- refusing to build a report")
    path = report_mod.build(args.out)
    print(f"wrote {path}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="bds-hw1", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("generate", help="regenerate data/*.json from the seeds").set_defaults(fn=cmd_generate)
    sub.add_parser("verify", help="check the ground-truth invariant").set_defaults(fn=cmd_verify)
    sub.add_parser("ping", help="check the configured ollama backend is reachable").set_defaults(fn=cmd_ping)
    sub.add_parser("models", help="record digests and default hyperparameters").set_defaults(fn=cmd_models)

    r = sub.add_parser("run", help="run experiment cells")
    r.add_argument("--models", default="ladder")
    r.add_argument("--tasks", default="all")
    r.add_argument("--arms", default="zeroshot")
    r.add_argument("--temps", default="grid")
    r.add_argument("--k", type=int, default=config.K_SWEEP)
    r.add_argument("--ladder", action="store_true", help="use the supplementary query ladder")
    r.add_argument("--no-resume", action="store_true")
    r.set_defaults(fn=cmd_run)

    pl = sub.add_parser("pilot", help="11-point sweep on the 1.5B model only")
    pl.add_argument("--k", type=int, default=config.K_SWEEP)
    pl.add_argument("--no-resume", action="store_true")
    pl.set_defaults(fn=cmd_pilot, arm="zeroshot")

    sw = sub.add_parser("sweep", help="build curves and choose the table temperatures")
    sw.add_argument("--arm", default="zeroshot")
    sw.set_defaults(fn=cmd_sweep)

    tu = sub.add_parser("topup", help="raise the chosen temperatures to k=10")
    tu.add_argument("--models", default="ladder")
    tu.set_defaults(fn=cmd_topup)

    tk = sub.add_parser("tokens", help="per-model tokenization stats")
    tk.add_argument("--models", default="ladder")
    tk.add_argument("--ladder", action="store_true")
    tk.set_defaults(fn=cmd_tokens)

    ui = sub.add_parser("ui", help="build the interactive run explorer")
    ui.add_argument("--out", default="public/index.html")
    ui.add_argument("--serve", action="store_true", help="live mode: reread runs/ on every request")
    ui.add_argument("--port", type=int, default=8765)
    ui.set_defaults(fn=cmd_ui)

    rp = sub.add_parser("report", help="build the HTML report")
    rp.add_argument("--out", default="report.html")
    rp.set_defaults(fn=cmd_report)

    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
