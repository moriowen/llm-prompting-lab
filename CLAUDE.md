# Working agreement

CS6220 BDS HW1. Two tasks (character reversal, decimal division with rounding) run
against three self-hosted models across an 11-point temperature sweep and three
prompting arms. `H1-critique-and-build.md` is the plan; `H1-assignment-transcript.md` is
the handout, verbatim. This file records decisions so they are not re-litigated.

## The invariant

**No LLM output enters the ground truth, the grading, or the statistics.** Queries and
gold answers come from `src/generate.py` and a committed seed. Task 2 answers are
computed twice — `decimal.Decimal` with `ROUND_HALF_UP`, and `fractions.Fraction` — and
asserted equal. The only LLM-produced values in the deliverable are the cells of the two
result tables. `main.py report` runs `verify.py` first and refuses to build if it fails.

## Decisions

- **Self-hosted only.** Ollama on localhost, native `/api/chat`, no hosted APIs, no
  API keys, no `.env`. The `/v1` OpenAI-compatible endpoint is not used because it hides
  `num_ctx`, `top_k` and `seed`.
- **Zero dependencies.** `urllib` for HTTP, `decimal`/`fractions` for arithmetic. The
  tokenizer count in `tokens.py` is measured through ollama's own `prompt_eval_count`
  rather than by adding a `tokenizers` dependency.
- **Model ladder** — `qwen2.5:1.5b` (small), `gemma3:4b` (mid), `mistral:7b` (large).
  The first two are already pulled. Mistral rather than `qwen2.5:7b` for the large slot:
  4.1 GB versus 4.7 GB matters on 8 GB, and it makes the ladder three organisations,
  which R5 wants. `qwen2.5-7b` stays registered as the alternate if the family-constant
  comparison turns out to matter more.
- **top_k and repeat_penalty are pinned, not left at model default.** Ollama defaults
  are per-Modelfile, so leaving them alone would let them vary across the three models
  and confound the size comparison. Each model's own defaults are still captured by
  `main.py models` and reported for R5.
- **`num_predict` is keyed by (task, arm).** Task 2 CoT needs 1536; at 640 the 1.5B
  model truncated 5 of 10 long divisions, and a truncated response is a harness bug, not
  a wrong answer (plan §4.7).
- **Selection rule fixed before the data exists.** `config.INFLECTION_CURVE = "accuracy"`
  — it is what the tables report. Self-consistency is computed alongside as
  corroboration, never as the selector. `sweep.py` applies the rule; the pair is never
  chosen by eye.
- **One global temperature pair for all three models**, so the six columns stay
  comparable. Per-model inflections belong in the analysis text.
- **Grading is strict and normalised, both reported.** Strict is the handout's literal
  length rule (a preamble makes a Task 1 answer invalid); normalised strips wrapping.
  The report headlines normalised.
- **Three few-shot shots**, drawn from a held-out pool generated with a different seed,
  asserted disjoint from the test set, and taken from the item's own complexity band.

- **Two output surfaces.** `report.py` builds the graded deliverable; `ui.py` builds an
  explorer for inspecting runs in progress. Both embed their data and open from the
  filesystem — no server, no CDN. The explorer truncates raw responses to 600 characters
  so a full CoT sweep does not produce a 40 MB page.

## Conventions

One-line docstrings. Comments explain *why*, next to the line they explain. No
abstraction for a second caller that does not exist. Runs are committed JSONL, one file
per (model, task, arm, temperature), flushed per line so a throttled laptop still leaves
an analysable prefix.
