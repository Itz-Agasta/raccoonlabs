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

## Demo video

- The edit is a HyperFrames project at `~/Videos/raccoonlabs/edit`, outside the repo. Voiceover lines live in `~/Videos/raccoonlabs/vo/` (`<line>.mp3` plus `<line>.json` with text and word timings); copy changed lines into `edit/assets/vo/`.
- Voices are ElevenLabs clones of the team. The key is in `~/.config/elevenlabs/key` (mode 600), never in chat or the repo.

| Speaker | Voice ID | Carries |
|---|---|---|
| Agasta | `WNhmuqjWsBbPdaUGY58q` | the build, Switch, the proof |
| Sherry | `DVAU9WJ5v1YfHSI20HNM` | the student's view |

- Settings the user approved: model `eleven_v4`, stability 0.6, similarity 0.9, style 0, speaker boost on, speed 0.92. Regenerate a line with `python3 -I ~/Videos/raccoonlabs/vo/tts.py <line-id> <agasta|sherry> "<text>"`. Send requests one at a time, since parallel calls hit 429.

## Rules that bind the build

- **Hackathon rule:** the Switch setup and agent workflow are built from Nov 4 onward with honest commit history. The repo stays private until submission day, then goes public (decision 36). Spikes stay out of the repo.
- **Keep the sealed paper out of git:** `notes/` is excluded through `.git/info/exclude`. Never name the sealed papers or their findings in tracked files, commits or Switch rooms.
- **Envelope integrity:** no agent, the Postdoc included, may see the sealed paper before a student posts `unseal`. Every search goes through `lab-search` with the blocklist; built-in web search/fetch stays disabled for lab agents. Agents inherit the user's global provider setup and MCP servers, so lab agents run outside this folder and get probed for web access. Claim only what the probes prove.
- **`dev-ops` and `tools/dev/` are build-only:** they know the sealed paper, so they stay out of rooms during blind runs and are removed before the final recording. Humans make every approval in the recorded run, and `~/.config/raccoonlabs/env` is removed first, because agents can read this user's files.
- **Pre-register spikes:** write the go/no-go rule before seeing the result.
- **Secrets:** they live in `~/.config/raccoonlabs/env` (mode 600), never in chat or the repo.
- **Prefer CLIs** or small shell wrappers over adding MCP servers.
- **One laptop, 7.5 GB RAM:** everything runs here; measure memory as agents are added. Students are role-played, and the video says so. Launch Console with `~/Applications/switch-console.AppImage --password-store=gnome-libsecret`. Modal: `chimera2` for development, `okc` for final runs.
- **Switch is central:** prefer Switch primitives (rooms, room documents, roles, targeted messages, attachments) over side channels for any lab state a judge should see.
- **Reproducible:** every feature works through `just` recipes and a CPU path (`just demo-cpu`) that needs no GPU account.
- **Honest results:** the demo shows whatever the real run produced. No faked numbers, no staged scorecards.
- Use `just`, `uv`, `tectonic`. Third-party skills (academic-research-skills is CC BY-NC) are installed as dependencies, never copied into the repo.
- **Upstream issues:** when you find a bug or an improvement worth suggesting in Switch or any other upstream project, tell the user as you find it, so they can file it on GitHub. Include the repo, repro steps, expected and actual behaviour, any workaround, and whether an open issue already covers it. Don't file it yourself.
