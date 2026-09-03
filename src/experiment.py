"""The model x temperature x prompt x query x seed loop. Resumable by construction."""

import sys
import time

from src import generate, grade as grading, ollama
from src.utils import config, prompts, trace
from src.utils.constants import BACKEND, MODEL_REGISTRY, OLLAMA_HOST, TASK_NAMES


def load_queries(task: str, ladder: bool = False):
    """The 10 committed queries for a task, or the supplementary ladder."""
    if ladder:
        return generate.load("ladder_queries")[task]
    return generate.load(f"{task}_queries")


def run_cell(model_alias: str, task: str, arm: str, temp: float, k: int,
             resume: bool = True, ladder: bool = False, verbose: bool = True) -> dict:
    """One (model, task, arm, temperature) cell: every query x every seed."""
    entry = MODEL_REGISTRY[model_alias]
    items = load_queries(task, ladder)
    pool = generate.load("fewshot_pool") if arm.startswith("fewshot") else None

    tr = trace.Trace(model_alias, task, arm, temp, resume=resume,
                     ollama_tag=entry["ollama_tag"], digest=entry.get("digest"),
                     prompt_version=prompts.PROMPT_VERSION, k=k, ladder=ladder,
                     task_name=TASK_NAMES[task], backend=BACKEND, host=OLLAMA_HOST,
                     **config.frozen())

    counts = {"done": 0, "skipped": 0, "correct": 0, "invalid": 0}
    for item in items:
        shots = prompts.shots_for(pool, task, item, config.N_SHOTS) if pool else None
        prompt = prompts.build(task, arm, item, shots)
        for seed in range(k):
            if (item["qid"], seed) in tr.done:
                counts["skipped"] += 1
                continue
            try:
                out = ollama.chat(entry["ollama_tag"], prompt, config.options(temp, seed, task, arm))
            except ollama.OllamaError as e:
                tr.close()
                raise SystemExit(f"\n{e}\n(progress is saved; re-run with --resume)")

            g = grading.grade(task, item, out["text"], arm)
            # A response cut off at num_predict is our bug, not the model's answer.
            truncated = out["done_reason"] == "length"
            invalid = truncated or not g["extraction_ok"]
            tr.trial(qid=item["qid"], seed=seed, prompt=prompt, raw=out["text"],
                     truncated=truncated, invalid=invalid, **g,
                     **{k2: out[k2] for k2 in ("done_reason", "prompt_tokens",
                                               "output_tokens", "wall_ms")})
            counts["done"] += 1
            counts["correct"] += g["correct_norm"]
            counts["invalid"] += invalid
            if verbose:
                mark = "." if g["correct_norm"] else ("!" if invalid else "x")
                print(mark, end="", flush=True)
    tr.close()
    if verbose:
        print(f"  {model_alias} {task} {arm} t={temp}: "
              f"{counts['correct']}/{counts['done']} correct, "
              f"{counts['invalid']} invalid, {counts['skipped']} skipped")
    return counts


def run(models, tasks, arms, temps, k, resume=True, ladder=False) -> None:
    """Sweep driver. Ordered model-outermost so ollama loads each model once."""
    started = time.monotonic()
    total = {"done": 0, "skipped": 0, "correct": 0, "invalid": 0}
    for model_alias in models:
        for task in tasks:
            for arm in arms:
                for temp in temps:
                    counts = run_cell(model_alias, task, arm, temp, k, resume, ladder)
                    for key in total:
                        total[key] += counts[key]
    mins = (time.monotonic() - started) / 60
    print(f"\n{total['done']} calls in {mins:.1f} min "
          f"({total['skipped']} skipped, {total['invalid']} invalid trials)",
          file=sys.stderr)
