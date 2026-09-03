"""Frozen experiment controls, written verbatim into every trace header."""

SEED = 6220
# A different seed for the few-shot pool, so a shot can never be a test item.
# generate.py asserts the two sets are disjoint rather than trusting the seed gap.
FEWSHOT_SEED = 916220
LADDER_SEED = 226220

# The handout's "say 5 / say 8", run as specified.
TASK1_LENGTHS = (5, 8)
TASK2_PLACES = (5, 8)
QUERIES_PER_BAND = 5
N_SHOTS = 3

# 0.0 -> 1.0 in 0.1 steps: N=10 intervals, 11 grid points.
TEMP_GRID = [round(i / 10, 1) for i in range(11)]

K_SWEEP = 3        # every grid point
K_TABLE = 10       # top-up, only the two temperatures that reach the deliverable table
K_DETERMINISM = 3  # temp 0.0, to check greedy decoding is actually deterministic here

# Pinned identically at every grid point, for every model and every prompt arm.
# Note the deliberate deviation from "leave at model default": ollama's defaults are
# per-Modelfile, so leaving them alone would let top_k and repeat_penalty vary across
# the three models and silently confound the size comparison. They are pinned to
# ollama's documented defaults instead, and the per-model defaults are still reported
# separately for R5 via `main.py models`.
TOP_P = 1.0
TOP_K = 40
REPEAT_PENALTY = 1.1
NUM_CTX = 2048
NUM_THREAD = 4

# CoT needs room to externalise the work. A harness necessity, not a variable -- it is
# reported as a stated deviation so the arms are otherwise identical. Keyed by
# (task, arm): eight-place long division runs far longer than listing eight characters
# backwards, and a response cut off at the cap is our bug, not the model's answer
# (section 4.7). Measured on qwen2.5-1.5b, which is the most verbose of the three.
NUM_PREDICT = {
    ("task1", "zeroshot"): 128, ("task1", "fewshot"): 128, ("task1", "cot"): 640,
    ("task2", "zeroshot"): 128, ("task2", "fewshot"): 128, ("task2", "cot"): 1536,
    # The verbose arms differ only in prompt wording, so they inherit the budget of
    # the arm they are a variant of; changing it would confound wording with length.
    ("task1", "fewshot_verbose"): 128, ("task1", "cot_verbose"): 640,
    ("task2", "fewshot_verbose"): 128, ("task2", "cot_verbose"): 1536,
}

# Where a completion must stop. Keyed by (task, arm) for the same reason num_predict is:
# the continuation a model invents depends on the shape of the prompt it was given.
# Without this, a model that never emits a stop token keeps going and writes its own
# few-shot examples after the answer -- mistral:7b truncated 52% of task1 fewshot at the
# 128-token cap, and the runaway text then failed the length rule. These six arms all
# instruct "output only the answer, nothing else", so the answer is one line and the
# first newline ends it. A marker keyed to the prompt's own label ("\nString:") was
# tried first and leaked -- the continuation does not always reproduce the label. No
# response among the 8137 collected before this change began with a newline, so this
# cannot truncate an answer to empty. The CoT arms get no stop: their reasoning spans
# many lines by design and ends at "FINAL:", so any marker would cut the work short.
STOP = {
    ("task1", "zeroshot"): ["\n"],
    ("task1", "fewshot"): ["\n"],
    ("task1", "fewshot_verbose"): ["\n"],
    ("task1", "cot"): [],
    ("task1", "cot_verbose"): [],
    ("task2", "zeroshot"): ["\n"],
    ("task2", "fewshot"): ["\n"],
    ("task2", "fewshot_verbose"): ["\n"],
    ("task2", "cot"): [],
    ("task2", "cot_verbose"): [],
}

REQUEST_TIMEOUT = 600

# --- sweep decision rule, fixed before any 7B data exists (plan section 3.2) ---------
# Selection is on accuracy: it is the quantity the deliverable tables report.
# Self-consistency is computed alongside as corroboration, never as the selector.
INFLECTION_CURVE = "accuracy"
# A single step down this large counts as a knee.
KNEE_DROP = 0.15
# A curve whose whole range is inside this band is called flat, and the null reported.
FLAT_RANGE = 0.10


def options(temperature: float, seed: int, task: str, arm: str) -> dict:
    """The ollama options dict. One variable moves; everything else is pinned here."""
    return {
        "temperature": temperature,
        "seed": seed,
        "top_p": TOP_P,
        "top_k": TOP_K,
        "repeat_penalty": REPEAT_PENALTY,
        "num_ctx": NUM_CTX,
        "num_thread": NUM_THREAD,
        "num_predict": NUM_PREDICT[(task, arm)],
        # ollama drops an empty list, so only send it where there is one.
        **({"stop": STOP[(task, arm)]} if STOP[(task, arm)] else {}),
    }


def frozen() -> dict:
    """Everything a trace header must carry to make its runs reproducible."""
    return {
        "seed": SEED, "fewshot_seed": FEWSHOT_SEED, "top_p": TOP_P, "top_k": TOP_K,
        "repeat_penalty": REPEAT_PENALTY, "num_ctx": NUM_CTX,
        "num_thread": NUM_THREAD,
        "num_predict": {f"{k[0]}.{k[1]}": v for k, v in NUM_PREDICT.items()},
        "stop": {f"{k[0]}.{k[1]}": v for k, v in STOP.items()},
        "n_shots": N_SHOTS,
        "temp_grid": TEMP_GRID, "inflection_curve": INFLECTION_CURVE,
    }
