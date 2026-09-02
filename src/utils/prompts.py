"""The three prompt arms. Frozen before the first run; version bumps on any edit."""

PROMPT_VERSION = "v1"

# --- task 1 --------------------------------------------------------------------------

T1_INSTRUCTION = "Reverse the following string. Output only the reversed string, nothing else."
T1_COT = (
    "Reverse the following string. Work through it one character at a time, listing the "
    'characters from last to first. Then give the final answer on a line beginning "FINAL: ".'
)

# --- task 2 --------------------------------------------------------------------------

def _t2_instruction(places: int) -> str:
    return (
        f"Divide the first number by the second number and round the result to {places} "
        "decimal places. Output only the final number, nothing else."
    )


def _t2_cot(places: int) -> str:
    return (
        f"Divide the first number by the second number and round the result to {places} "
        "decimal places. Work through the long division step by step, one digit at a "
        'time. Then give the final answer on a line beginning "FINAL: ".'
    )


def _t2_line(item: dict) -> str:
    return f"Numbers: {item['a']}, {item['b']}"


# --- assembly ------------------------------------------------------------------------

def build(task: str, arm: str, item: dict, shots: list[dict] | None = None) -> str:
    """Return the full user message for one trial."""
    if task == "task1":
        if arm == "cot":
            return f"{T1_COT}\nString: {item['s']}"
        head = T1_INSTRUCTION
        if arm == "fewshot":
            # Shots come from the same length band as the item, so the technique is not
            # confounded with a difficulty mismatch.
            lines = [f"String: {s['s']} -> {s['gold']}" for s in shots]
            return f"{head}\n" + "\n".join(lines) + f"\nString: {item['s']} ->"
        return f"{head}\nString: {item['s']}"

    places = item["places"]
    if arm == "cot":
        return f"{_t2_cot(places)}\n{_t2_line(item)}"
    head = _t2_instruction(places)
    if arm == "fewshot":
        lines = [f"Numbers: {s['a']}, {s['b']} -> {s['gold']}" for s in shots]
        return f"{head}\n" + "\n".join(lines) + f"\n{_t2_line(item)} ->"
    return f"{head}\n{_t2_line(item)}"


def band_of(task: str, item: dict) -> str:
    """The complexity band key a shot list is drawn from."""
    return str(item["l"] if task == "task1" else item["places"])


def shots_for(pool: dict, task: str, item: dict, n: int) -> list[dict]:
    """n held-out shots from the item's own complexity band."""
    return pool[task][band_of(task, item)][:n]
