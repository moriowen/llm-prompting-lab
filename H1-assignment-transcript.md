# Transcript: 2026-ProgrammingAssignment-1.pdf

Faithful transcript of the assignment PDF. Whitespace from the PDF's text layer has
been normalised and page breaks marked; **wording is unchanged**, including the
handout's own typos and inconsistencies. The Task 1 specification on page 1 is an
embedded image, transcribed here from that image (rendered copy at
`tmp/pdfs/task1.png`).

---

## Page 1

CS6220 BDS 2026 Fall — Homework Assignment 1 (Programming Category)

Student Name: _______________________

Student Session: cs6220-A

Posting Date: Monday of week 2 (Aug 31).

Due Date: midnight on Friday of Week 3 (Sept 11), with no penalty extension to 9am
(morning) Saturday of Sept 12. It is a hard deadline. Late submission will not be
accepted.

### Problem 1: Hand-on Experience with Large Language Models (LLMs)

This problem is designed for students to learn how to use Pretrained LLMs such as
ChatGPT family of models, or any of your favorite GenAI models (LLM or VLM) through
learning the so-called contamination problems of LLMs.

Here is *A Comprehensive Survey of Contamination Detection Methods in Large Language
Models*. Here is the github repo for ACL 2024 Finding paper — *Unveiling the Spectrum
of Data Contamination in Language Model: A Survey from Detection to Remediation*.

You can find many pre-trained LLMs from Huggingface LLM leader board. Feel free to
choose your favorite LLMs for this problem. Hint: LLMs of three different parameter
sizes are recommended.

You are asked to design the following two learning tasks that can be solved by
leveraging pre-trained LLMs to generate your final solutions.

**Task 1: Character-By-Character Retrieval** with 5 different randomly generated
strings at two different string length settings, i.e., l=len(S):

> *[The following is transcribed from the embedded image that follows this line.]*
>
> - **Task Name:** Character-By-Character Reversal
> - **Input:** **s** := (s₁, s₂, ⋯ , s_l), a randomly generated string with fixed
>   character length *l*. sᵢ is the i-th character of input string **s**. The character
>   set is 52 uppercase and lowercase English alphabet letters, i.e. a-z and A-Z.
> - **Output:** **s**_out. We consider **s**_out as valid if it has the same length as
>   input string, i.e. len(**s**_out) = len(**s**). When **s**_out = (s_l, s_{l−1}, ⋯ ,
>   s₁), we consider **s**_out as correct.
> - **Hyperparameters:** *l*, the length of input string **s**.

---

## Page 2

### Task 2: Decimal Computation with Rounding

You are asked to design this second task as follows:

Task description: divide the first number A by the second number B and round the result
to {self.decimal_places} decimal places.

Requirement: Here A is not a factor of B. The answer is a decimal or a fraction, not a
whole number (non-integer result).

Example 1: You are asked to find two numbers, and the second number cannot be divided
by the first number and you are asked to round to 5 decimal places:

```
<input>10, 3</input> <output>3.33333</output>
```

You are asked to find two numbers, and the second number cannot be divided by the first
number and you are asked to round to 4 decimal places:

```
<input>1, 7</input> <output>0.1429</output>
```

For each of these two tasks, you will need to design at least 10 different queries,
using random string generator, 5 of them in the same length (say 5 characters or
rounding to 5 digits) and 5 of them in a longer length (say 8 characters or rounding to
8 digits). You are encouraged to leverage the prompt engineering techniques you learned
in class, such as CoT prompting, CoT-instruction following prompting, to name a few.

Plot your 10 queries on each row of the result table and you are asked to analyze the
results obtained independently from at least three independently pretrained LLMs.

For each of the 10 queries, and each of the chosen pre-trained LLMs, you are asked to
use at least 2 different LLM hyperparameter settings, such as 2 temperature settings, or
2 settings of presence-penalty, or 2 settings of two or more hyperparameter combos.

Now you have a result table of 10 rows (one query per row) and six columns, one LLM with
two columns (representing two hyperparameter settings), you are asked to compare the
results from the 10 queries across three LLMs, and elaborate the analysis of your
results with critique. If you are leveraging GenAI models to perform reasoning for your
results, then you are expected to provide your critique on the GenAI model reasoning
output.

---

## Page 3

**Hints:** This HW1 can be done with one query at a time or a group of queries at a time
with intelligent instruction in your prompt context.

### Deliverable

**(1)** For each of the two tasks, you are required to report each LLM you chose, with
detailed description of full name, incl version/series #, the company produced it, the #
parameters (size of the model), and the URL where you download the model or the URL for
the API you use to call the LLM). For each of three LLMs you choose, you also need to
provide the default settings of its hyperparameters.

**(2)** You are asked to provide the results for each of the two tasks in a table with
outputs in the cells and row name is the query and column name is the LLM name and the
hyperparameter setting). Name each of your two tables with the corresponding task name.
You are required to use red color font for all wrong answers from LLMs. Here is an
example template of the task output table:

|  | LLM-1 (setting 1) | LLM-1 (setting 2) | LLM-2 (setting 1) | LLM-2 (setting 2) | LLM-3 (setting 1) | LLM-3 (setting 2) |
|---|---|---|---|---|---|---|
| Q1 [...] | | | | | | |
| Q2 [...] | | | | | | |
| Q3 [...] | | | | | | |
| Q4 [...] | | | | | | |
| Q5 [...] | | | | | | |
| Q6 [...] | | | | | | |
| Q7 [...] | | | | | | |
| Q8 [...] | | | | | | |
| Q9 [...] | | | | | | |
| Q10 [...] | | | | | | |

**(3)** For each of the two tasks, compare the 10 queries and the results across all
three pretrained LLMs. Elaborate on your observations with respect to each LLM.

**(4)** For each of the three pretrained LLMs of your choice, compare the two learning
tasks, and any in-context text phrases you design. Discuss how this LLM works on these
two tasks, its pros and cons you have observed by working with the two tasks over two
sets of queries of different complexity.

**(5)** If you are leveraging an LLM to perform analysis and reasoning of your results
for all or a part of the above three items, then you are expected to provide your
critique on the LLM reasoning outputs.

---

## Page 4

### HW submission Requirement

For all of our HW assignment, you need to follow our naming convention:

> Programming HW should start with `HW1_P_<your last name>_<first name>`.

The grading scale is the scale of 100 points with pass (>60), pass- (<=60) or pass+
(>90).

**Attention:** You must read the update for fall semester about "leveraging AI to
enhance (not replace) your learning" available on Canvas course home page and following
the to do guideline.
