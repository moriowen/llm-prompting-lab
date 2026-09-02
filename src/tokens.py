"""Per-model tokenization stats, measured through the model that will be tested."""

from src import generate, ollama
from src.utils import config
from src.utils.constants import MODEL_REGISTRY

# One token of prompt is not free to measure: ollama reports prompt_eval_count for the
# whole chat template, so the string's own token count is the difference between a
# prompt containing it and the identical prompt without it. That keeps the count in the
# model's real tokenizer without pulling a separate tokenizers dependency.
PROBE = "String: {}"


def count(model_tag: str, text: str) -> int:
    """Tokens the model's own tokenizer assigns to `text`, by difference."""
    opts = config.options(0.0, 0, "task1", "zeroshot") | {"num_predict": 1}
    with_text = ollama.chat(model_tag, PROBE.format(text), opts)["prompt_tokens"]
    without = ollama.chat(model_tag, PROBE.format(""), opts)["prompt_tokens"]
    return with_text - without


def measure(model_alias: str, ladder: bool = False) -> list[dict]:
    """n_tokens and chars_per_token for every task-1 string."""
    tag = MODEL_REGISTRY[model_alias]["ollama_tag"]
    items = generate.load("ladder_queries")["task1"] if ladder else generate.load("task1_queries")
    rows = []
    for item in items:
        n = count(tag, item["s"])
        rows.append({"model": model_alias, "qid": item["qid"], "s": item["s"],
                     "l": item["l"], "n_tokens": n,
                     "chars_per_token": round(item["l"] / n, 3) if n else None,
                     "case_pattern": item["case_pattern"]})
    return rows
