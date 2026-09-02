"""The five prompt arms. Frozen before the first run; version bumps on any edit."""

PROMPT_VERSION = "v2"

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


# --- verbose variants ----------------------------------------------------------------
# Same techniques as `fewshot` and `cot`, but with the rules and the answer format
# spelled out. The pair exists to separate "the technique does not help" from "the
# instruction was too terse", so the terse originals are left byte-identical.

T1_FEWSHOT_VERBOSE_HEAD = """Reverse the case-sensitive string character by character.

Rules:
1. Read the input from right to left.
2. Copy every character exactly once.
3. Preserve uppercase and lowercase exactly.
4. The output must have exactly the same number of characters as the input.
5. Output only the reversed string.

Examples:
"""

T1_FEWSHOT_VERBOSE_SHOT = """
Input: {s}
Characters from right to left: {spaced}
Output: {gold}
"""

T1_FEWSHOT_VERBOSE_TAIL = """
Now reverse this string.

Input: {s}
Output:"""

T1_COT_VERBOSE = """Reverse the string using the exact format below.

Rules:
1. Treat uppercase and lowercase as different characters.
2. Assign an index to every character from left to right.
3. Copy the characters in descending index order.
4. Use every character exactly once.
5. Check that the input and output both contain exactly {l} characters.
6. Always end with a line beginning "FINAL:".

Required format:

INDEX: 1=<character>, 2=<character>, ..., {l}=<character>
REVERSED INDEXES: {l}, ..., 2, 1
CANDIDATE: <reversed string>
CHECK: input length={l}, output length=<count>
FINAL: <reversed string>

String: {s}"""

T2_FEWSHOT_VERBOSE_HEAD = """Compute the first number divided by the second number: A / B.

Rules:
1. Do not reverse the operands.
2. Compute the quotient before rounding.
3. Round to exactly {places} digits after the decimal point.
4. Preserve trailing zeros.
5. Output only the final number.

Examples:
"""

T2_FEWSHOT_VERBOSE_SHOT = """
First number: {a}
Second number: {b}
Operation: {a} / {b}
Decimal places: {places}
Output: {gold}
"""

T2_FEWSHOT_VERBOSE_TAIL = """
Now solve:

First number: {a}
Second number: {b}
Operation: {a} / {b}
Decimal places: {places}
Output:"""

T2_COT_VERBOSE = """Calculate A divided by B using integer long division. Do not estimate or reverse the operands.

Produce exactly {places} decimal digits plus one guard digit.

For each digit:
1. x = 10 * remainder
2. digit = x // B
3. product = digit * B
4. new remainder = x - product
5. Verify that product <= x < product + B.
6. Verify that 0 <= new remainder < B.

Use the guard digit to round half up. Preserve trailing zeros.

Required format:

INTEGER: q=<value>, remainder=<value>
D1: x=<value>, digit=<value>, product=<value>, remainder=<value>
D2: x=<value>, digit=<value>, product=<value>, remainder=<value>
Continue for all required digits.
GUARD: <digit>
ROUNDED: <number with exactly {places} decimal digits>
FINAL: <same number>

A={a}
B={b}"""


# --- assembly ------------------------------------------------------------------------

def build(task: str, arm: str, item: dict, shots: list[dict] | None = None) -> str:
    """Return the full user message for one trial."""
    if task == "task1":
        if arm == "cot":
            return f"{T1_COT}\nString: {item['s']}"
        if arm == "cot_verbose":
            return T1_COT_VERBOSE.format(l=item["l"], s=item["s"])
        if arm == "fewshot_verbose":
            body = "".join(
                T1_FEWSHOT_VERBOSE_SHOT.format(
                    s=sh["s"], spaced=" ".join(sh["gold"]), gold=sh["gold"])
                for sh in shots)
            return (T1_FEWSHOT_VERBOSE_HEAD + body
                    + T1_FEWSHOT_VERBOSE_TAIL.format(s=item["s"]))
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
    if arm == "cot_verbose":
        return T2_COT_VERBOSE.format(places=places, a=item["a"], b=item["b"])
    if arm == "fewshot_verbose":
        body = "".join(
            T2_FEWSHOT_VERBOSE_SHOT.format(
                a=sh["a"], b=sh["b"], places=sh["places"], gold=sh["gold"])
            for sh in shots)
        return (T2_FEWSHOT_VERBOSE_HEAD.format(places=places) + body
                + T2_FEWSHOT_VERBOSE_TAIL.format(
                    a=item["a"], b=item["b"], places=places))
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
