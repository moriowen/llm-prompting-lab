# HW1: problem analysis and plan of action

Source of truth is `H1-assignment-transcript.md` (verbatim transcript of
`2026-ProgrammingAssignment-1.pdf`). This document is my own reading of the assignment
and the build plan that follows from it.

**Constraints this plan is written against:**
- Self-hosted models only. No hosted APIs.
- MacBook Air M2, 8 GB unified memory.
- Due Fri 11 Sep 2026 midnight, hard grace to Sat 12 Sep 09:00. Nine days from today.
- Grading is 100 points on a coarse scale: pass+ (>90), pass (>60), pass- (≤60).

---

## 1. What the assignment actually asks for

### 1.1 The framing is contamination, not arithmetic

The opening paragraph states the purpose: learn to use pretrained LLMs *"through
learning the so-called contamination problems of LLMs,"* and it links a contamination
detection survey and the ACL 2024 Findings repo. The two tasks are instruments for that
lesson, not the lesson itself.

This matters for the write-up. Both tasks are built on **freshly randomised inputs** —
"randomly generated string" for Task 1, "using random string generator" for Task 2. The
reason is that a random string generated today cannot appear in any model's training
corpus, so a correct answer cannot come from memorisation of that instance. The tasks
therefore probe procedural capability rather than recall.

The report should say this explicitly and should carry the corollary: this is a
*contamination control*, not a contamination *study*. The task type (reversal, division)
is certainly in training data even though the instances are not. Overclaiming here is
exactly the sort of thing deliverable (5) asks you to catch.

### 1.2 Hard requirements, extracted

| # | Requirement | Handout wording |
|---|---|---|
| R1 | ≥3 **independently pretrained** LLMs | "at least three independently pretrained LLMs" |
| R2 | Three different **parameter sizes** recommended | "Hint: LLMs of three different parameter sizes are recommended" |
| R3 | ≥10 queries per task; 5 at one complexity, 5 at a longer one | "at least 10 different queries ... 5 of them in the same length ... 5 of them in a longer length" |
| R4 | ≥2 LLM hyperparameter settings per model per query | "at least 2 different LLM hyperparameter settings" |
| R5 | Model description table: full name + version/series #, company, # parameters, download or API URL, **and default hyperparameter settings** | Deliverable (1) |
| R6 | Two result tables, one per task, named after the task; 10 rows × 6 columns; **wrong answers in red font** | Deliverable (2) |
| R7 | Per-task comparison across the three LLMs, with per-LLM observations | Deliverable (3) |
| R8 | Per-LLM comparison **across the two tasks**, including the in-context phrases you designed, with pros/cons across the two complexity levels | Deliverable (4) |
| R9 | Critique of any LLM-generated analysis you used | Deliverable (5) |
| R10 | Filename starts `HW1_P_<last>_<first>` | Page 4 |

R1 and R2 together are the model-selection constraint: three *different families* at
three *different sizes*. A single family's size ladder (e.g. Qwen 1.5B / 7B / 32B)
satisfies R2 but violates R1 — those are one pretraining recipe at three scales.

R8 is the one most likely to be under-served. It is not "describe each model"; it is
"for each model, compare its behaviour on Task 1 versus Task 2, and discuss the prompts
you wrote." That requires the prompt to be a thing you actually varied and have data on.

### 1.3 Task 1, precisely as specified

The formal spec is an image on page 1. Read carefully, it defines **two separate
criteria**:

- **Valid**: `len(s_out) == len(s)`
- **Correct**: `s_out == (s_l, s_{l-1}, ..., s_1)`

Correctness implies validity, but validity does not imply correctness. This is a free
gift for the analysis and should be a first-class metric, not folded into a single
boolean. Three distinguishable outcomes:

| Outcome | Meaning |
|---|---|
| correct | exact reversal |
| valid but incorrect | right length, wrong order or wrong characters — the model understood the output contract but failed the operation |
| invalid | wrong length — usually dropped/duplicated characters, or preamble text leaking in |

A model that is mostly *invalid* has an instruction-following problem. A model that is
mostly *valid but incorrect* has a capability problem. Those are different findings and
the handout's own definitions hand you the distinction.

Character set is fixed at 52 letters, a–z and A–Z. Note the handout says "Retrieval" in
the page-1 heading and "Reversal" in the spec image; the spec image is operative.

The handout calls `l` a **hyperparameter of the task**. So the word "hyperparameter" is
used in two senses in this assignment — task complexity (`l`, decimal places) and LLM
sampling settings (temperature, presence penalty). Keep the two vocabularies separate in
the report or the reader will conflate R3 and R4.

### 1.4 Task 2, and its contradictory wording

The requirement paragraph says *"Here A is not a factor of B"* and the examples say
*"the second number cannot be divided by the first number."* Both readings are muddled,
but the sentence *"The answer is a decimal or a fraction, not a whole number
(non-integer result)"* is unambiguous, and both worked examples confirm it:

- `<input>10, 3</input> → <output>3.33333</output>` — that is A/B with A=10, B=3
- `<input>1, 7</input> → <output>0.1429</output>` — A=1, B=7

**Operative rule: compute A ÷ B, require `A mod B != 0`.** State this resolution
explicitly in the report — noticing and resolving an ambiguity in the spec is worth more
than silently picking one.

Two further observations from the examples:

- The second example rounds to **4** decimal places, not 5 or 8. So the decimal-place
  count is genuinely a free parameter; the "say 5 / say 8" in the body is illustrative.
- One example has A > B (result `3.33333`), the other A < B (result `0.1429`). Different
  output shapes — leading `0.` versus a leading integer digit. Both should appear in the
  query set.

The task description also contains an unrendered Python template artifact —
`round the result to {self.decimal_places} decimal places` — which tells you the handout
was machine-generated from a parameterised generator. Harmless, but it confirms that the
decimal-place count is the intended complexity knob.

### 1.5 What "say 5 / say 8" means for design risk

R3's numbers are hedged with "say," so 5 and 8 are examples. But deviating carries
rubric risk for zero upside when compute is free. **Run the handout's 5 and 8 as the
required tables**, and run a wider complexity ladder as a supplementary figure. Locally
hosted models cost nothing per token, so the supplementary run is free — this is a
material advantage of the self-hosted approach and should be used.

---

## 2. The hardware constraint is an experimental advantage

An M2 Air with 8 GB cannot run a frontier model. That sounds like a limitation. For
*this* assignment it is close to ideal, and the report should say so.

The central design risk in this assignment is a **ceiling effect**: reversing an 8-letter
string and rounding a quotient to 8 places are easy for large models. Run three frontier
models and you plausibly get 60/60 correct, no variation between hyperparameter
settings, and nothing to analyse for deliverables (3), (4) and (7).

A 1B / 3–4B / 7B ladder does not ceiling. Small models fail character reversal
reliably and fail long-precision division badly. You will get a genuine accuracy
gradient across model size **at the handout's own complexity settings**, which is
precisely what R2 is fishing for. The constraint produces the result the assignment
wants.

Three further advantages of self-hosting that are worth a paragraph in the write-up:

1. **Default hyperparameters are inspectable.** R5 requires reporting each model's
   default settings. For a hosted API that is often undocumented or unstable. With
   Ollama, `ollama show <model> --parameters` and `--modelfile` print the temperature,
   top_p, top_k, repeat_penalty and stop tokens the model ships with. R5 becomes a
   command, not a literature search.
2. **Seeds are settable.** Local inference exposes `seed`. Temperature-1 sampling
   becomes reproducible, so the grader can re-run your exact experiment. Hosted APIs
   mostly cannot offer this.
3. **Compute is free**, so k-sampling, complexity ladders, and prompt side-experiments
   cost only wall-clock time.

### 2.1 Memory budget

macOS plus a browser takes roughly 3 GB. Budget **≈4.5 GB** for a model, and never load
two at once. Q4_K_M quantisation, one model resident at a time, `ollama stop` between
models.

| Params | Q4_K_M on disk/RAM | Verdict on 8 GB |
|---|---|---|
| ~1 B | ~0.8–1.3 GB | comfortable |
| ~2–4 B | ~1.6–3.3 GB | comfortable |
| ~7 B | ~4.1–4.7 GB | works, tight, close other apps |
| ~13 B | ~7.5 GB | swap thrash, do not |

Also set `OLLAMA_MAX_LOADED_MODELS=1` and a short `OLLAMA_KEEP_ALIVE` so a finished
model is evicted rather than lingering.

**Thermal throttling is real** on a fanless M2 Air over an hour of sustained 7B
inference. The harness must therefore be **resumable** — see §5.

---

## 3. Model selection

Three families, three organisations, three sizes. All dense (no MoE, so "# parameters"
in R5 is unambiguous — an MoE model would force you to report total *and* active
parameters or the size-comparison axis becomes misleading).

**Proposed set:**

| Slot | Model | Org | Params | ~Q4 size | Status |
|---|---|---|---|---|---|
| Small | Qwen2.5 1.5B Instruct | Alibaba Cloud | 1.54 B | ~1.0 GB | already local |
| Mid | Gemma 3 4B IT | Google DeepMind | 4.30 B | ~3.3 GB | already local |
| Large | Mistral 7B Instruct v0.3 | Mistral AI | 7.25 B | ~4.1 GB | not pulled |

The small and mid slots are what is already on the machine, which is the right reason to
pick them — nothing about the experiment improves by swapping the 1.5B for a 1B. The
large slot is Mistral rather than Qwen2.5 7B for two reasons: 4.1 GB versus 4.7 GB is a
real difference on an 8 GB laptop, and it makes the ladder three organisations, which is
what R5's "three independently pretrained LLMs" is asking for.

Registered as an alternate: **Qwen2.5 7B Instruct** (Alibaba, 7.6 B, ~4.7 GB). It holds
the pretraining family constant against the 1.5B, so the size gradient is not confounded
by a change of corpus. If the 7B slot has to be dropped entirely for memory, the honest
fallback is to report a two-model ladder and say so — not to substitute a hosted API.

> **Verify before running.** My model knowledge has a cutoff and it is now September
> 2026. Check `ollama.com/library` for current tags and newer small models before
> committing. Do not trust the version numbers above as final.

**Record for R5, per model:** exact HF repo name and revision, org, parameter count from
the model card, model-card URL, the Ollama tag **and its digest** (`ollama show
<model> --modelfile`), quantisation level, and the full default parameter dump. Pin the
digest — a moving tag makes the run irreproducible.

### 3.1 Which API to call

Ollama exposes an OpenAI-compatible endpoint at `http://localhost:11434/v1`, which is
the tidiest option and needs no API key (pass a dummy string). But it does **not**
expose `num_ctx`, `top_k`, or `repeat_penalty`.

Since R5 requires reporting defaults and the whole experiment is about pinning
everything except one variable, use the **native `/api/chat` endpoint** with an explicit
`options` dict. It exposes `seed`, `num_ctx`, `top_k`, `repeat_penalty`, `num_predict`
and `stop`. Every one of those gets pinned, logged into the trace header, and reported.

### 3.2 The hyperparameter axis: an 11-point temperature sweep (R4)

R4 requires *at least* two settings and R6 fixes the table at six columns. Rather than
picking two temperatures by assertion, **sweep the full range and choose the two from
the measured curve.**

Grid: **0.0 → 1.0 in steps of 0.1** — that is N=10 intervals, 11 grid points
(0.0, 0.1, …, 1.0). Everything else pinned and identical at every point: `top_p = 1.0`,
`top_k` at model default, `repeat_penalty` at default, `num_ctx` and `num_predict`
fixed, same prompt, same seeds. One variable moves; everything else is reported.

The required table is then a **slice of the sweep**, not a separate run — you already
have every temperature, so selecting two costs nothing extra. The table stays exactly
10 rows × 6 columns as R6 specifies; the sweep is supplementary evidence that justifies
which two columns you chose.

#### Why this is the strongest version of the experiment

"We used 0.0 and 1.0 because the handout suggested it" is a weak methods paragraph.
"We measured accuracy across the full temperature range, located each model's
degradation point, and selected the two settings that straddle it" is a strong one — and
it directly answers *where does the model start to fail*, which single-point comparisons
cannot.

It also produces a second-order finding that is more interesting than the first-order
one: **does the inflection temperature move with model size?** A 7B model plausibly
holds accuracy further up the range before collapsing than a 1B model does. If that
shows up, it is a genuine result about capability headroom, and it is exactly the kind
of size-comparison observation R2 and R7 are fishing for.

#### The curve may not have a knee — plan for all three shapes

Do not assume a sigmoid. Three outcomes are realistic and all three are reportable:

| Shape | What it means | How to pick the two table settings |
|---|---|---|
| **Knee** — flat, then a sharp drop | there is a usable operating range and a cliff | one point clearly below the knee, one clearly above — maximises the contrast the table shows |
| **Monotone decline**, no sharp knee | degradation is gradual | the endpoints, 0.0 and 1.0 — maximum separation |
| **Flat** — at ceiling or at floor across the whole range | temperature has no measurable effect at this difficulty | the endpoints, and report the null result explicitly |

The flat-at-floor case is likely for the 1B model on Task 1 at *l*=8: it may score ~0%
at every temperature, because there is no accuracy to degrade. That is not a failed
experiment — it is a floor effect, and saying so plainly is worth more than manufacturing
a trend. Expect the sweep to be most informative on the *easier* complexity band for
small models and the *harder* band for the 7B.

#### Choose one global pair, not per-model pairs

If each model gets its own two temperatures, the six columns stop being comparable and
the cross-model comparison R7 asks for becomes meaningless. **Pick one pair of
temperatures, applied identically to all three models**, chosen from the pooled curves.
Report each model's individual inflection separately in the analysis — that is where the
per-model observation belongs.

#### Resolution honesty

With k samples per (query, temperature) and 10 queries per task, each curve point rests
on 10×k trials. At k=5 that is 50 trials per point, roughly ±7pp resolution. That is
adequate to see a trend across 11 points but **not** to locate an inflection more
precisely than ±0.1 on the temperature axis. Read the curve as a shape, not as
individual points, and do not claim precision the sampling does not support.

#### Temperature 0 is a determinism control, not a sample

At temperature 0 sampling is greedy, so with a fixed seed output should be deterministic
and k>1 buys nothing statistically. But **verify it empirically** rather than assuming —
Metal kernels and batching can introduce float non-determinism. Run each temp-0 query
3× and report whether outputs were identical. If they are, that is a reportable control
that strengthens every other claim in the report.

---

## 4. Design decisions and the traps behind them

### 4.1 n=1 per cell would make the temperature comparison meaningless

Temperature is a property of a *distribution*. A single draw at temperature 1.0 tells
you what one sample happened to be, not whether the model is less reliable there. If
temp-0 and temp-1 agree on all ten queries you cannot distinguish "temperature does not
matter" from "you got lucky."

**Plan, staged so the sweep stays affordable:**

| Stage | Coverage | k | Calls |
|---|---|---:|---:|
| Determinism control | temp 0.0, all models/tasks/queries | 3 | 180 |
| **Sweep** | temps 0.1–1.0, all models/tasks/queries | 5 | 3,000 |
| **Top-up** | only the two chosen table temperatures | +5 → k=10 | 600 |
| | | | **≈3,780** |

Seeds are `0..k-1`, fixed and logged, so every sample is reproducible.

The sweep runs at k=5 because 11 grid points × k=10 would be ~6,600 calls and most of
that precision is spent on curve points that never appear in a deliverable. Once the
inflection is located and the two table temperatures are chosen, **top those two
temperatures up to k=10** — precision where it is reported, economy where it is
exploratory.

The required table cell shows the modal output — which is what R6 asks for — and the
analysis gets the two statistics that actually answer the question:

- **accuracy** = correct / k
- **self-consistency** = fraction of the k draws identical to the modal draw

Self-consistency *is* the temperature effect, and plotted across the 11-point grid it is
the cleaner of the two curves: accuracy is bounded by capability and can sit on the floor,
but consistency starts at 1.0 for every model and has room to fall. **Expect the
consistency curve to show the inflection more sharply than the accuracy curve**, and
expect the two to separate — a model can stay self-consistent while being consistently
wrong. That gap is worth a paragraph.

Wall clock: ~3,780 calls at a blended ~4 s/call is roughly **4 hours**, plus the prompt
experiment in §4.6. Split across two overnight runs. This is why `--resume` in §5 is
mandatory rather than nice-to-have.

**Pilot on the 1B model first.** It is ~4× faster than the 7B, so a full sweep on it
costs well under an hour and tells you the curve shape, whether the inflection is
visible, and whether k=5 is enough — before you commit ten hours of the two larger
models. If the 1B curve is flat at floor, that is information: raise it by running the
sweep on the *easier* complexity band.

### 4.2 Ten queries gives 10-point accuracy resolution

Per the table format, each cell is one query, so a per-model accuracy moves in steps of
10 points. A 7/10 versus 8/10 gap is one query and is indistinguishable from noise.
Writing "Model A outperforms Model B" on that basis is precisely the error deliverable
(5) exists to catch.

State the resolution limit explicitly once. The staged sampling in §4.1 mitigates it:
the two reported table temperatures carry k=10, giving 50 trials per model per
complexity band instead of 5, and the sweep points carry k=5.

### 4.3 Task 1's real mechanism is tokenization — and it is measurable

Character reversal is hard for LLMs because of **BPE tokenization**. A string like
`qWnTbLxrEc` is split into a handful of multi-character subword tokens; nothing in the
input exposes character boundaries directly. The model must recover character identity
from token identity before it can reverse anything. Small models are worse at this
because they have less capacity to spare for that decomposition.

This is testable, and locally you have each model's actual tokenizer:

- tokenize every input with each model's own tokenizer; record `n_tokens` and
  `chars_per_token`
- correlate error rate against `n_tokens`, not just against `l`
- prediction: at equal character length, strings that fragment into more, shorter tokens
  are reversed more accurately

If the correlation holds you have an explanation rather than a description, which is
what deliverable (3) is asking for. If it does not hold, report that — a clean negative
is still a finding.

Related: generate genuinely mixed case. `abcdefgh` and `aBcDeFgH` tokenize very
differently, and the handout's character set explicitly permits both cases. Log the case
pattern per query so you can say whether it mattered.

### 4.4 Task 2 needs stratification and an error taxonomy

`A mod B != 0` is too weak a constraint on its own. These are not the same task:

| Query | Character |
|---|---|
| `1 / 3` to 5 dp | period-1 repeating, trivially memorable |
| `355 / 113` to 8 dp | famous π approximation — contamination risk, exclude |
| `7 / 128` to 8 dp | terminating, exact, but many digits |
| `47 / 83` to 8 dp | period-41 repeating, no shortcut, must actually divide |

**Stratify deliberately** and record the stratum per query: terminating vs repeating,
short-period vs long-period, and A>B vs A<B. **Exclude fractions with famous decimal
expansions** (π approximations, 1/7, 22/7) — a correct answer there is recall, not
computation, which is exactly the contamination confound the assignment is about.

**Grade with a taxonomy, not a boolean.** Every wrong answer is one of:

1. **wrong digits** — the quotient itself is wrong
2. **rounding error** — correct quotient, rounded wrong (truncation instead of
   round-half-up is the classic)
3. **precision error** — right value, wrong number of decimal places
4. **format-only** — right value, but scientific notation, missing trailing zeros, or
   thousands separators

Types 1 and 2 are the interesting split: a model that divides correctly but rounds
wrong has a completely different failure from one that cannot divide. Type 4 should
probably score as correct after normalisation. **Decide the strict-vs-normalised
question before any data exists**, write it in the repo, and report both numbers.

### 4.5 Ground truth is pure Python — a hard invariant

**No LLM output enters the ground-truth, grading, or statistics pipeline at any point.**
This is the load-bearing invariant of the whole project, and it should be stated as such
in the report.

The only LLM-produced values anywhere in the deliverable are the **cells of the two
result tables**. Everything else — the queries, the correct answers, the pass/fail
judgement, the error classification, the accuracy and consistency figures, the curves —
is computed deterministically by committed Python from a committed seed.

Three reasons this matters more than it might look:

1. **It is the only defensible way to grade.** An LLM-as-judge on an exact-string task
   would introduce a fourth model whose errors are indistinguishable from the three
   models under test.
2. **It makes the experiment reproducible.** Seed + script → identical queries and
   identical gold answers on any machine. The grader can re-derive your ground truth
   without trusting you.
3. **It disposes of R9 honestly.** Deliverable (5) asks you to critique any LLM used to
   reason about your results. The cleanest answer is a stated invariant: no LLM produced
   or reasoned about the ground truth, the grading, or the statistics — and here is the
   script that did. R9 becomes a short, verifiable paragraph instead of an awkward one.

#### Verify the ground truth against itself

A single implementation of the gold answers is an assertion, not a verification. Cheap
cross-checks that turn it into one:

- **Task 1:** assert `reverse(reverse(s)) == s` and `sorted(gold) == sorted(s)` for every
  generated item. Both are trivially true if the code is right and loudly false if it is
  not.
- **Task 2:** compute every answer **twice, by two independent routes** — once with
  `decimal.Decimal` at high precision, once with `fractions.Fraction` — and assert they
  agree. Two independent implementations agreeing is real verification; one
  implementation running successfully is not.
- Emit a `verify.py` that re-derives everything from the seed and diffs it against the
  committed `data/*.json`. Run it in the same command as the report build so a silent
  drift in the data files cannot reach the tables.

#### Two arithmetic traps in the Task 2 gold answers

- **Never use float division.** `round(a/b, 8)` accumulates float error, and Python's
  built-in `round` uses banker's rounding (round-half-to-even), not the round-half-up a
  human — or a model — will produce. Use `decimal.Decimal` with `getcontext().prec` set
  well above the target, and an explicit `ROUND_HALF_UP`.
- **Filter out ties at generation time.** If the digit immediately after the rounding
  position is exactly 5 and nothing follows it, the "correct" answer depends on an
  unstated rounding convention. Grading that penalises the model for your ambiguity
  rather than its arithmetic. Reject those candidates during generation and record how
  many were rejected.

### 4.6 Three prompting techniques: zero-shot, few-shot, chain-of-thought

These are the three techniques covered in class and the handout explicitly encourages
them ("CoT prompting, CoT-instruction following prompting"). All three get run. But the
prompt must be a **control** for the main tables, or the six columns are not comparable.

Two-tier resolution:

- **Main tables (required, R6):** **zero-shot only**, one frozen prompt per task,
  written before the first run and never touched afterwards. Zero-shot is the right
  control because it isolates the model's own capability with no in-context scaffolding.
- **Prompt experiment (R8):** all three techniques, all three models, both tasks.

#### The three arms

**Zero-shot** — instruction plus the item, no examples, no reasoning invitation.

```
Reverse the following string. Output only the reversed string, nothing else.
String: aBcDeFgH
```

**Few-shot** — the same instruction with 3 solved examples prepended. Fix the shot
count at 3 and report it.

```
Reverse the following string. Output only the reversed string, nothing else.
String: kQmZrT   ->  TrZmQk
String: bNvXpL   ->  LpXvNb
String: wYtGuJ   ->  JuGtYw
String: aBcDeFgH ->
```

**Chain-of-thought** — invite explicit intermediate work, then anchor the answer.

```
Reverse the following string. Work through it one character at a time,
listing the characters from last to first. Then give the final answer on a
line beginning "FINAL: ".
String: aBcDeFgH
```

#### Design rules that keep the arms honest

- **Few-shot examples must come from a held-out set.** Generate them with a *different
  seed* from the test queries, and assert no overlap. Reusing a test item as a shot
  contaminates your own experiment — the exact failure mode this assignment is about.
- **Shots are drawn from the same complexity band as the test item** (length-5 shots for
  length-5 items). Otherwise you confound the prompting technique with a difficulty
  mismatch.
- **Watch the context budget.** With `num_ctx` at 2048 and a 1B model, three long
  few-shot examples plus a CoT preamble is not free. Log prompt token counts per arm and
  confirm nothing is being silently truncated at the front.
- **CoT needs a larger `num_predict`.** Raising the output cap for the CoT arm is a
  harness necessity, not an experimental variable — document it as a deliberate, stated
  deviation so the arms remain otherwise identical.
- **Log the raw response and the extracted answer separately.** For CoT you must parse
  the answer out of the reasoning; the `FINAL:` marker anchors it. A missing marker is an
  **invalid trial**, not a wrong answer (§4.7).

#### Budget

Run the prompt experiment at **two fixed temperatures**: 0.0 (greedy, so the prompting
effect is uncontaminated by sampling noise) and the high table temperature (to test
whether CoT helps *more* under sampling pressure — a real interaction worth having data
on). Zero-shot at both is already in the sweep, so only the two new arms cost anything:

3 models × 2 tasks × 10 queries × 2 new arms × (1 at temp 0 + 5 at high temp) = **720
calls**, plus longer generations on the CoT arm. Call it 1–1.5 hours.

#### Two predictions worth stating before you look

Writing these down in advance makes the analysis a test rather than a narration.

1. **CoT should help Task 2 more than Task 1.** Long division is a serial algorithm the
   model can genuinely externalise into tokens — CoT gives it scratch space it does not
   otherwise have. Reversal is bottlenecked on *character-level access* (§4.3), and no
   amount of externalised reasoning grants a model visibility into the characters inside
   a BPE token. If the data shows CoT lifting Task 2 while barely moving Task 1, that is
   a clean mechanistic result and the strongest paragraph available for R8.
2. **Few-shot should raise validity more than correctness** on Task 1. Examples
   demonstrate the *output contract* (bare string, right length, no preamble) far more
   directly than they demonstrate *how to reverse*. This maps exactly onto the
   validity/correctness split the handout itself defines in §1.3 — so few-shot fixing
   format while leaving capability untouched is both predictable and precisely
   measurable with the metrics you are already computing.

A third, less certain one: CoT may help the 1B model *least*, not most. A model that
cannot sustain a coherent chain will produce plausible-looking reasoning and then
transcribe the wrong answer — reasoning correctly and copying badly is a distinct
failure, and logging raw-vs-extracted separately is what lets you tell the two apart.

Excluded deliberately: few-shot + CoT combined. It is a fourth arm that doubles the
design without answering a question the other three leave open. Note the exclusion.

### 4.7 Truncation and refusal are harness bugs, not wrong answers

If a response hits `num_predict` and is cut off, that is not a model error, it is your
error. Log the stop reason on every call. A truncated or unparseable response is an
**invalid trial to be re-run**, not a data point. Report the invalid-trial count so the
denominators are honest.

Small models will also sometimes emit chatter, restate the question, or loop. Decide
in advance whether "preamble + correct answer" counts as valid for Task 1 (per §1.3 it
is *invalid* under the handout's length rule) and normalise consistently.

---

## 5. Repo and harness

Mirroring the `dbagent` project's conventions: `uv` + `pyproject.toml`, one-line
docstrings, load-bearing "why" comments beside the line they explain, no abstraction for
a second caller that does not exist, runs committed as JSONL, a `CLAUDE.md` recording
decisions.

```
bds-hw1/
├── CLAUDE.md                 working agreement + decisions log
├── README.md                 setup, commands, model table, results
├── pyproject.toml            deps: httpx, tokenizers  (no API keys, no dotenv)
├── .python-version
├── data/
│   ├── task1_queries.json    10 strings + gold reversals + length/case metadata
│   ├── task2_queries.json    10 divisions + gold answers + stratum labels
│   ├── fewshot_pool.json     held-out shots, DIFFERENT seed, asserted disjoint
│   └── ladder_queries.json   supplementary complexity ladder
├── src/
│   ├── main.py               CLI: --task --model --temps --prompt --k --resume
│   ├── generate.py           seeded generation + Decimal gold answers + tie filter
│   ├── verify.py             re-derive from seed, cross-check, diff vs data/
│   ├── experiment.py         model × temp × prompt × query × k loop, resumable
│   ├── grade.py              normalisation, validity/correctness, error taxonomy
│   ├── sweep.py              build the 11-point curves, locate the inflection
│   ├── tokens.py             per-model tokenization stats for §4.3
│   ├── report.py             graded JSONL -> self-contained HTML
│   └── utils/
│       ├── constants.py      MODEL_REGISTRY: alias -> ollama tag + digest + metadata
│       ├── config.py         frozen NUM_CTX / NUM_PREDICT / TOP_P / TEMP_GRID / K
│       ├── prompts.py        zero-shot / few-shot / CoT templates, versioned
│       └── trace.py          JSONL writer, per-line flush, full config header
└── runs/
    └── <model-alias>/
        └── task1.zeroshot.t0.3.jsonl   one file per (task, prompt, temp)
```

Points that matter:

- **No `.env`.** Everything is localhost. One less moving part than dbagent.
- **`constants.py` records provenance.** Ollama tag, digest, HF repo, org, parameter
  count, quantisation, model-card URL. This dict *is* deliverable (1); generate the
  report's model table from it rather than typing it twice.
- **`config.py` holds the controls**, written verbatim into every trace header, so the
  claim "held fixed across all models, prompts and temperatures" is verifiable by
  reading a run file. `TEMP_GRID = [round(i/10, 1) for i in range(11)]` lives here.
- **`verify.py` enforces §4.5.** Re-derives every query and gold answer from the seed,
  runs the Task 1 involution check and the Task 2 `Decimal`-vs-`Fraction` cross-check,
  and diffs against the committed `data/*.json`. Wire it into the report build so drift
  cannot silently reach the tables.
- **`experiment.py` must be resumable.** `--resume` skips (model, task, prompt, query,
  temp, seed) tuples already present in the JSONL. With ~4,500 calls across two
  overnight runs on a fanless throttling laptop, this is load-bearing.
- **Filename encodes the cell.** `task1.zeroshot.t0.3.jsonl` — with 11 temperatures ×
  3 prompt arms, a flat naming scheme stops being navigable fast.
- **`grade.py` returns a record, not a bool** — `{valid, correct, error_type,
  normalized, raw, extracted}`. Task 1 taxonomy: `wrong_length` / `wrong_order` /
  `wrong_chars` / `extra_text`. Task 2 taxonomy: §4.4. `raw` and `extracted` differ only
  on the CoT arm and the gap between them is itself a finding.
- **`sweep.py` owns the inflection.** It builds accuracy and self-consistency curves per
  (model, task, complexity band), applies the §3.2 decision rule, and emits the chosen
  temperature pair. The choice is made by committed code from committed data, not by eye
  — so it is reproducible and defensible.
- **`report.py` generates the red.** R6 requires wrong answers in red font. Derive the
  colour from the grade in code. Never hand-colour a cell — hand-marking *will* drift
  from the data across revisions, and a red cell that disagrees with your own accuracy
  table is the worst possible finding for a grader to make.

### 5.1 The HTML report

One self-contained HTML file, no external assets, section order tracking the
deliverables:

1. Model table — full name + version, org, parameter count, HF/Ollama URL, quantisation,
   **and the default hyperparameter dump** → R5
2. Method — seed, all three prompt templates verbatim, pinned settings, temperature
   grid, k per stage, grading rules, **and the ground-truth invariant from §4.5**
3. **Temperature sweep** — accuracy and self-consistency curves across the 11 grid
   points, per model, per complexity band; the located inflections; and the decision rule
   that selected the two table temperatures → justifies §3
4. **Task 1: Character-By-Character Reversal** — 10 × 6, wrong cells red → R6
5. **Task 2: Decimal Computation with Rounding** — 10 × 6, wrong cells red → R6
6. Accuracy, validity, and self-consistency summary
7. Error taxonomy breakdown
8. Supplementary complexity ladder
9. Tokenization analysis → §4.3
10. Prompting comparison — zero-shot vs few-shot vs CoT, both tasks, all models, with
    the §4.6 predictions stated and then tested → R8
11. Cross-model analysis → R7
12. Per-model cross-task analysis → R8
13. Self-critique, opening with the §4.5 invariant → R9

The sweep section is the one that makes this report better than a competent minimum.
Plot it as small multiples — one panel per model, accuracy and consistency on the same
axes, complexity bands as separate series — rather than one crowded chart.

Once graded JSONL exists I can build this and publish it as a shareable artifact
alongside the local file.

---

## 6. Order of work

| Day | Work |
|---|---|
| 1 | Install Ollama, pull the three models, confirm each loads under 8 GB and responds; capture `--modelfile` dumps for R5 |
| 1 | `generate.py` + `verify.py`: seeded inputs, `Decimal` gold answers, `Fraction` cross-check, tie filter, strata, held-out few-shot pool; commit `data/*.json` |
| 2 | `experiment.py` + `trace.py` + `grade.py`; determinism check at temp 0; **pilot the full 11-point sweep on the 1B model only** (~1 h) and inspect the curve shape |
| 2 | Decide k from the pilot; if the curve is flat at floor, shift the sweep to the easier complexity band before committing the big runs |
| 3 | Sweep run, overnight: 4B and 7B, 11 temperatures, k=5. `--resume` after throttling |
| 4 | `sweep.py`: build curves, locate inflections, apply the decision rule, fix the two table temperatures. Top those two up to k=10 |
| 5 | Prompting experiment: few-shot + CoT arms, all models, both tasks, two temperatures (~720 calls, overnight) |
| 5 | `tokens.py` + supplementary complexity ladder |
| 6–7 | `report.py`; **write the analysis yourself** |
| 8 | Buffer |

Two scheduling notes. The day-2 pilot is the highest-value hour in the plan — it is what
stops you discovering on day 4 that ten hours of 7B inference produced a flat line. And
the sweep and the prompting experiment are independent, so if throttling costs you a
night, run them in either order rather than serialising on a blocked step.

On day 6–7: R9 requires critiquing any LLM-generated analysis you use. The cleanest way
to satisfy it is to not generate the analysis with an LLM in the first place — write the
observations from your own tables. If you do use one, keep its output verbatim and
critique it explicitly; that is a deliverable, not an admission.

---

## 7. Decisions to make before any data exists

1. ~~**Mid-slot model**~~ — **settled: Gemma 3 4B**, already on the machine. The
   ladder is 1.5B / 4B / 7B.
2. **Strict vs normalised grading for Task 2 format errors** — my recommendation is to
   report both, with normalised as the headline and strict in an appendix.
3. ~~**k on the sweep**~~ — **settled: k=5**, `config.K_SWEEP`. The pilot still tells
   you whether the curve is legible at that resolution; raising it later is a re-run with
   a larger `--k` and `--resume`, which costs only the new draws.
4. **Does preamble text count as invalid for Task 1?** Per §1.3 the handout's length rule
   says yes. Confirm you are comfortable with that, since it will make small models look
   worse for an instruction-following reason rather than a capability reason — which is
   itself a legitimate finding, provided you say so.
5. ~~**Which curve selects the inflection?**~~ — **settled: accuracy**, encoded as
   `config.INFLECTION_CURVE` before any data existed, and applied by `sweep.py`. Original
   reasoning: **accuracy or self-consistency?** They can
   disagree, and §4.1 expects consistency to show the knee more sharply. My
   recommendation is to select on **accuracy** (it is the quantity the tables report) and
   show the consistency curve alongside as corroboration. Whichever you choose, encode it
   in `sweep.py` before you look at the 7B data, so the rule is not fitted to the result.
6. **Grid endpoints** — 0.0–1.0 in 0.1 steps is 11 points (N=10 intervals). If you want
   exactly 10 runs per cell, drop 0.0 from the sweep and keep it only as the determinism
   control. I would keep all 11; 0.0 is the greedy baseline every other point is measured
   against.
7. ~~**Shot count for few-shot**~~ — **settled: 3**, `config.N_SHOTS`. Measured on the
   1.5B model, a 3-shot length-8 Task 1 prompt is well inside `num_ctx = 2048`.

**Two decisions the build forced that were not in the original list:**

8. **`num_predict` is keyed by (task, arm), not by arm alone.** At 640 the 1.5B model
   truncated 5 of 10 Task 2 CoT responses; long division to 8 places simply runs longer
   than listing 8 characters backwards. Task 2 CoT is 1536, everything else unchanged.
   Per §4.7 a truncated response is a harness bug, so this is a fix, not a variable —
   but it is a stated deviation and belongs in the report.
9. **`top_k` and `repeat_penalty` are pinned rather than left at model default.** The
   plan said "at model default", but ollama defaults are per-Modelfile and would
   therefore vary across the three models — silently confounding the size comparison
   with a sampling difference. They are pinned to 40 and 1.1 for every model, and each
   model's own defaults are still captured by `main.py models` and reported for R5.
