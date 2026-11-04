# RaccoonLabs

A research lab in Slack for **student research groups**: students do the work alongside AI lab members (Postdoc, Lab Manager, Scout, three Engineers, Scribe, Reviewer 2), and a human professor approves. Each student brings their own agent and subscription; **Switch** (github.com/sandbox-quantum/switch) pools them into one lab. Built for the WeMakeDevs "Flip the Switch" hackathon, Nov 4–7 2026 (submit by Nov 7, 18:00 IST).

## Start of every session

1. Read `notes/handover.md`: current state, next step, blockers.
2. Read `notes/plan.md` for the build plan and `notes/decisions.md` before changing anything a decision covers.
3. End the session by rewriting `notes/handover.md` (done / next / blockers / open questions).

## Where things live

- `notes/plan.md`: the live plan (architecture, agents, gates, schedule). Single source of truth for scope.
- `notes/decisions.md`: numbered decisions with the reason. Add a new entry when a decision changes; never edit history silently.
- `notes/pitch.md`: positioning and the 3-minute demo script. Read before touching README, video, or blog.
- `notes/research/`: hackathon rules and judging, Switch internals, chosen papers, third-party skills and tools. Read the relevant file before building against Switch or a tool.
- `notes/archive/`: superseded plans, prefixed with the date (`2026-11-04-plan.md`).

## Rules that bind the build

- **Hackathon rule:** the Switch setup and agent workflow are built from Nov 4 onward, in the public repo, with honest commit history. Before Nov 4 only planning, environment setup, and throwaway spikes happen (the spikes stay out of the repo).
- **Envelope integrity:** no agent, the Postdoc included, may see the sealed paper before a student posts `unseal`. Every search goes through `lab-search` with the blocklist; built-in web search/fetch stays disabled for lab agents.
- **Switch is central:** prefer Switch primitives (rooms, room documents, roles, targeted messages, attachments) over side channels for any lab state a judge should see.
- **Reproducible:** every feature works through `just` recipes and a CPU path (`just demo-cpu`) that needs no GPU account.
- **Honest results:** the demo shows whatever the real run produced. No faked numbers, no staged scorecards.
- Use `just`, `uv`, `tectonic`. Third-party skills (academic-research-skills is CC BY-NC) are installed as dependencies, never copied into the repo.
