# Third run: a full study, written with the skills

2026-11-07, in all four rooms. A rehearsal on a topic unrelated to the sealed paper, not a blind run. A build-only tool role-played the students through one real Slack account, and it said so in the room. Models: Ringtail and Quill on Opus, Bandit and Patch on Sonnet, Scout on a free OpenCode model, Reviewer 2 on Codex.

**Question:** how much does early stopping depend on clean validation labels, across noise rates and noise types?

## What ran

Batches `S2-SMALL`, `S2-D64` and `S2-D256`: 55 conditions over 30 seeds, 1,650 training runs, all clean exits, about 1 hour 15 minutes of compute with 2 jobs. `lab-integrity` on the last draft: 0 failures, 8 flags, which Reviewer 2 settled by hand.

The paper is 9 pages, with an OpenTikZ-based method figure, multi-panel plots, full tables and 16 references. Its code and data availability statement is still waiting on the students, and it has not been through a professor sign-off.

## What the agents caught

- **Reviewer 2** rejected two drafts: an abstract that said "because" where the data only supports "consistent with", a bound applied beyond what it covers, and an untested interaction claim. All 55 table rows matched its own recomputation.
- **Ringtail** sent v4 back for major revision: stopping on random labels also beats the epoch budget, so much of the benefit comes from stopping at all, and the pair-flip headline loses significance under corrected variance.
- **Patch** flagged that its 200-epoch control disagrees with the earlier pilot (81.29 against 91.00). The cause is unresolved, and the paper says so.

## What went wrong

- **Reviewer 2 reached the web** in its `#lab-bench` session, using a built-in search and fetch despite `just harden`. See `docs/agent-access.md`.
- **A 5-seat review panel ran out the shared Claude 5-hour limit**, and the room only saw "Worked for 1m 3s". Ringtail and Quill now work in one pass without subagents, unless a student asks for a panel.
- **Reviewer 2 didn't address Ringtail by name**, so Ringtail waited. Its rules now say to.
- **Quill waited for Scout's sources** before drafting, and it didn't invent any.

## Timing

About 3 hours of active work from the first question to the first accepted draft, not counting a pause of about 3 hours in the middle when the usage limit stopped the work. The final mission should be smaller.
