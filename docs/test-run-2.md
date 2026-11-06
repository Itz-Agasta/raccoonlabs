# Second end-to-end run, with a paper

2026-11-06, across `#lab-brainstorm`, `#lab-bench`, `#lab-paper` and `#lab-review`, on one laptop. A test run on a neutral brief, not a blind run. A build-only tool posted the student and professor messages through one real Slack account, and it said so in the room. Models: Ringtail, Patch and Quill on Sonnet, Bandit on Haiku, Scout on a free OpenCode model, Reviewer 2 on Codex.

**Question:** does early stopping on a clean validation set win back what 20% label noise costs a small MLP on scikit-learn digits?

## Result against the rules set before the run

| Rule | Result | Evidence |
|---|---|---|
| (a) Ringtail pushes back at least once before a plan | Pass | Asked for a number for "completely", how the noise is made, and how to separate early stopping from clean data |
| (b) Scout logs at least 3 real sources, all through `lab-search` | Pass | Query log in `lab-search.jsonl`; `Library` room document |
| (c) Students approve the plan | Pass | One role-played reply |
| (d) Patch runs at least 3 seeds after approval | Pass | Batch `NOISE1`, 5 seeds, all clean exits. One timing seed ran before the request, and Patch said so |
| (e) Reviewer 2 accepts or rejects from logs | Pass | Rejected first, because the approver said "role-played"; accepted after a person ruled on it. Rejected the group's claim of full recovery |
| (f) Quill posts a PDF with a diagram and a plot | Pass | v3, 2 pages, TikZ method diagram, per-seed plot, 3 citations |
| (g) Every result number matches the logs, by hand | Pass | Recomputed from the seed logs: 0.9600, 0.9444, 0.9100, 1.56 pp, 3.44 pp |
| (h) Lowest available memory; no agent killed for memory | Pass, on spot readings | About 2,400 MB at the lowest reading, not continuously sampled |

The science result: A clean labels with early stopping 0.9600, B 20% noise with early stopping 0.9444, C 20% noise for the full 200 epochs 0.9100. Early stopping recovered 3.44 of the 5.00 points lost, and the group's claim of recovery within 1 point was rejected, at 1.56.

Also run: `lab-integrity` on the draft (0 failures, 5 flags, which Reviewer 2 and Ringtail recomputed), a role-played professor sign-off, and an unseal of a throwaway envelope with toy claims, whose scorecard passed `scorecard-check` with one match, one miss and one not tested.

## What the run changed

- **Bash deny rules:** a `Bash(curl:*)` entry in `disallowedTools` removed Bash altogether under Switch. Taken out.
- **Removing an agent from a room:** Bandit invited Patch to the wrong room and then removed it at a student's request, which stopped Patch posting anywhere. It took Console's log to find this, because Patch couldn't report it. Adding Patch back fixed it, and Bandit now never invites or removes agents across rooms.
- **Bandit on Haiku** renamed a room without being asked, and put documents in the wrong room. Its rules now forbid the first and pin documents to `#lab-bench`. It's cheap enough to keep, but it needs the closest watching.
- **Addressing:** Scout posted BibTeX without addressing Quill, so Quill never saw it until a student pointed it out. Scout's rules now say to address `@quill`.
- **`lab-integrity`** only recognised batch IDs starting with B, and didn't catch the template's author line. Both fixed.

## Not yet covered

A blind run, the real envelope, a separate professor account, and a phone approval.
