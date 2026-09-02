# CS6220 BDS HW1 — character reversal and decimal division on self-hosted LLMs

Two tasks from the handout, run against three locally hosted models across an 11-point
temperature sweep and three prompting arms, graded against ground truth computed
entirely in Python.

- `H1-assignment-transcript.md` — the handout, verbatim
- `H1-critique-and-build.md` — the analysis and plan
- `H1-data-guide.md` — project structure and result schemas, for anyone analysing the data
- `CLAUDE.md` — decisions log

## Setup

Requires Python 3.12+ and [Ollama](https://ollama.com). No pip install: the project has
no dependencies.

```sh
ollama serve                 # if it is not already running
ollama pull qwen2.5:1.5b     # small slot   (~1.0 GB)
ollama pull gemma3:4b        # mid slot     (~3.3 GB)
ollama pull mistral:7b       # large slot   (~4.1 GB)
export OLLAMA_MAX_LOADED_MODELS=1   # 8 GB machine: keep one model resident
```

Start with the 1.5B model only and add the larger slots once the pilot looks right.

## Commands

```sh
python3 -m src.main generate            # rebuild data/*.json from the committed seeds
python3 -m src.main verify              # check the ground-truth invariant
python3 -m src.main models              # capture digests + default hyperparameters -> R5

python3 -m src.main pilot               # 11-point sweep, 1.5B only, both tasks  (~20 min)
python3 -m src.main sweep               # build the curves, apply the decision rule

python3 -m src.main run --models qwen2.5-1.5b,gemma3-4b --temps grid --k 5
python3 -m src.main topup               # raise the two chosen temperatures to k=10
python3 -m src.main run --arms fewshot,cot --temps 0.0,1.0 --k 5
python3 -m src.main tokens              # per-model tokenization stats

python3 -m src.main ui                  # -> ui.html, interactive run explorer
python3 -m src.main report              # -> report.html, the deliverable
```

`ui` and `report` are different things on purpose. The report is the submission: fixed
tables at the two chosen temperatures, wrong answers in red. The explorer is for looking
at the data while it is still coming in — pick a model, task and prompt arm, read the
accuracy and self-consistency curves, and click any query-by-temperature cell to see the
raw responses behind it. Both are single self-contained files with no server and no
external assets; rebuild either at any time, including mid-run.

Every run is resumable: `run` skips any (query, seed) already present in the JSONL, so a
session killed by thermal throttling can be restarted with the same command.

## Layout

```
data/     committed queries, gold answers, few-shot pool, model metadata, sweep result
runs/     <model>/<task>.<arm>.t<temp>.jsonl — one line per trial, flushed as it goes
src/      generate verify experiment grade sweep tokens report main ollama
src/utils constants config prompts trace
```

## Ground truth

No LLM output enters the ground truth, the grading, or the statistics. Queries and gold
answers are generated from a committed seed; Task 2 answers are computed twice, by
`decimal.Decimal` with `ROUND_HALF_UP` and by `fractions.Fraction`, and asserted equal.
`report` refuses to build if `verify` fails.
