# Mission brief: final

Written by the students before the run. No agent has seen it before this commit.

## Question

We keep reading that small networks trained on modular arithmetic memorise the training set first, and then, long after, suddenly generalise ("grokking"). We want to find out for ourselves, on a model small enough to train on one laptop CPU: **which training choices decide whether a tiny network groks modular arithmetic, and how sure can we be of each answer?**

You pick the task, the model and the settings to vary, and tell us why. Push back if the question is too broad for the budget.

## Limits

- CPU only, on this laptop. One training run should take about a minute.
- At most 2 batches and 40 training runs in total, with 2 parallel jobs. Each batch needs a student's approval before it starts.
- Every claim needs more than one seed. Report what didn't work too.
- Work in one pass: no review panels or subagents unless a student asks.

## Output

- A short paper (about 4 pages) with a method figure, plots and a results table, built in `#lab-paper`.
- Every number in the paper traces back to a logged batch.
- We are the authors. Reviewer 2 runs the integrity check before the professor sees it.
