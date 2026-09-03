"""Model provenance. This dict is deliverable (1) -- the report table is generated from it."""

import os

# alias -> everything R5 asks for, plus the ollama tag used to reach it. `digest` is
# filled in by `main.py models`, which reads it back from the local ollama install:
# a tag is mutable, a digest is not, and the run is only reproducible against a digest.
MODEL_REGISTRY = {
    "qwen2.5-1.5b": {
        "slot": "small",
        "ollama_tag": "qwen2.5:1.5b",
        "full_name": "Qwen2.5-1.5B-Instruct",
        "org": "Alibaba Cloud (Qwen team)",
        "params": "1.54B",
        "quantization": "Q4_K_M",
        "url": "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct",
        "ollama_url": "https://ollama.com/library/qwen2.5:1.5b",
        "digest": None,
        "local": True,
    },
    "gemma3-4b": {
        "slot": "mid",
        "ollama_tag": "gemma3:4b",
        "full_name": "Gemma 3 4B Instruction-Tuned",
        "org": "Google DeepMind",
        "params": "4.30B",
        "quantization": "Q4_K_M",
        "url": "https://huggingface.co/google/gemma-3-4b-it",
        "ollama_url": "https://ollama.com/library/gemma3:4b",
        "digest": None,
        "local": True,
    },
    # Large slot. NOT pulled yet -- 4.1 GB is the largest thing that fits comfortably
    # beside a desktop on 8 GB, which is why this is mistral rather than qwen2.5:7b
    # (4.7 GB). It also makes the ladder three different organisations, which R5 wants.
    "mistral-7b": {
        "slot": "large",
        "ollama_tag": "mistral:7b",
        "full_name": "Mistral-7B-Instruct-v0.3",
        "org": "Mistral AI",
        "params": "7.25B",
        "quantization": "Q4_K_M",
        "url": "https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3",
        "ollama_url": "https://ollama.com/library/mistral:7b",
        "digest": None,
        "local": False,
    },
    # Alternate large slot: keeps the family constant against qwen2.5-1.5b, so the size
    # gradient is not confounded by a change of pretraining corpus. Costs 0.6 GB more.
    "qwen2.5-7b": {
        "slot": "large-alt",
        "ollama_tag": "qwen2.5:7b",
        "full_name": "Qwen2.5-7B-Instruct",
        "org": "Alibaba Cloud (Qwen team)",
        "params": "7.62B",
        "quantization": "Q4_K_M",
        "url": "https://huggingface.co/Qwen/Qwen2.5-7B-Instruct",
        "ollama_url": "https://ollama.com/library/qwen2.5:7b",
        "digest": None,
        "local": False,
    },
}

# The three that go in the six-column tables. Ordered small -> large.
LADDER = ("qwen2.5-1.5b", "gemma3-4b", "mistral-7b")

# Inference backend. Experiment code never runs on the GPU box: PACE ICE only serves
# ollama, while prompts, grading and traces stay on the laptop. An
# `ssh -L 11434:<compute-node>:11434 amohite8@login-ice.pace.gatech.edu` tunnel makes the
# remote server appear on this same local port, so the default is right for both
# backends; BDS_OLLAMA_HOST (or ollama's own OLLAMA_HOST) overrides it.
def _host(raw: str | None) -> str:
    if not raw:
        return "http://localhost:11434"
    raw = raw.strip().rstrip("/")
    # Ollama's convention is a bare host:port; urllib needs the scheme.
    return raw if raw.startswith(("http://", "https://")) else f"http://{raw}"


OLLAMA_HOST = _host(os.environ.get("BDS_OLLAMA_HOST") or os.environ.get("OLLAMA_HOST"))

# Which machine actually decoded a cell. A tunnel hides this -- the URL is localhost
# either way -- so it is declared, not inferred, and written into every trace header:
# wall_ms from an A100 and wall_ms from an 8 GB laptop are not the same measurement.
BACKEND = os.environ.get("BDS_BACKEND", "local-m2-air")

TASKS = ("task1", "task2")
ARMS = ("zeroshot", "fewshot", "cot", "fewshot_verbose", "cot_verbose")

TASK_NAMES = {
    "task1": "Character-By-Character Reversal",
    "task2": "Decimal Computation with Rounding",
}

# Fractions whose decimal expansions are memorable enough that a correct answer is
# plausibly recall rather than arithmetic. Stored reduced; generation rejects any
# candidate that reduces into this set. This is the contamination control.
FAMOUS_FRACTIONS = {
    (355, 113), (22, 7), (1, 7), (1, 3), (2, 3), (1, 6), (1, 9), (1, 11),
    (1, 13), (3, 7), (2, 7), (1, 17), (1, 19), (99, 70), (577, 408),
    (1, 81), (10, 3), (100, 3), (1, 12), (5, 3),
}
