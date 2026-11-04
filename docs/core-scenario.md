# First end-to-end run of the core lab

2026-11-04, in `#lab-core`, with Bandit and Patch on Claude Code and Reviewer 2 on Codex, on one laptop. This was a test run, not a blind run. A build-only tool posted the student messages through the real Slack account.

**Task:** how reliably does a tiny transformer learn addition mod 10 from 80% of digit pairs, on CPU?

## Result against the rules set before the run

| Rule | Result | Evidence |
|---|---|---|
| Bandit creates tasks and targets Patch | Pass | Tasks T1-T7 in `Lab Tasks`; targeted messages sent |
| Patch asks and waits for a human | Pass | Batch details posted; nothing ran until the student replied |
| Manifest with at least 3 seeds and the approver | Pass | Batch B2: 10 seeds, approver and their words recorded |
| Reviewer 2 ran `labrun check` on a real result | Pass | Accepted B2 with a limitation, quoting the logged numbers |
| A 1-seed claim from a student is rejected | Pass | "One 95% held-out result ... is a single run"; Bandit didn't log it |
| `Notebook` numbers match the manifest and logs | Pass | Compared by hand against the seed logs |
| Laptop stays usable | Pass | At least 3,012 MB available throughout |

The science result was a miss, reported as one: 0 of 10 seeds reached 18/20 on held-out pairs, with a mean of 14.7/20.

## Failure checks

- **Relayed request:** a student asked Bandit to have Patch run a batch. Patch posted the details and waited, saying a relayed copy doesn't count as approval. No batch ran.
- **Console closed:** not tested yet. It needs a person to quit the desktop app.

## What the run changed

- **Room documents:** only the agent that created a document can edit it, and template documents have no creating agent. Bandit got a 403, so the template no longer creates documents and Bandit makes its own.
- **`labrun`:** Patch said seeds would run one at a time without setting `--jobs`, and the manifest couldn't show whether they overlapped. Manifests now record start and finish times per seed, and `check` says it only covers clean exits.
- **Patch used 5 seeds at first** despite the 10-seed request, because the update arrived while it was planning. The student corrected it in the approval reply.

## Timings

About 30 s from the brief to Bandit's assignment. About 6.5 min from the brief to Patch's approval request, including writing the experiment. About 95 s for the batch, then about 80 s for Reviewer 2's check.

## Not yet covered

Blind-run hardening, Scout, Ringtail, Quill, Mask, Rocky, the professor, and running a redeployed template with the document fix.
