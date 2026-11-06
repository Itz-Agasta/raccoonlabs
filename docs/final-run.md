# Recording the final run

Humans make every approval in this run, and it's recorded end to end. The students and professor are role-played, and the video says so.

## Before the run

1. **Write the question.** The students write it in their own words and commit it to `missions/final/brief.md`. It must not hint at the sealed paper's findings. Commit before any agent sees it.
2. **Seal the envelope.** In a real terminal, run `just seal` and choose a passphrase. Never put it in chat. Commit `envelope/sealed.enc` and note the sha256 from `lab-envelope fingerprint`.
3. **Fresh rooms.** Rename the four test channels in Slack so their names are free, then run the template's rooms in Console.
4. **Fresh data.** Move `~/.local/share/raccoonlabs/runs`, `sources.jsonl` and `lab-search.jsonl` aside, and move `paper` out of Quill's folder. Batch IDs can't be reused.
5. **Remove build-only access.** Delete `dev-ops` (`!delete-agent dev-ops confirm`), remove `tools/dev/` from the working tree for the recording, and delete `~/.config/raccoonlabs/env`, because agents can read this user's files.
6. **Apply lockdown.** Run `just harden`, then probe Scout and Reviewer 2 once.
7. **Free memory.** Close the browser. Note the start time for `just audit --since`.

## During the run

Post the envelope's sha256 in `#lab-review` before the question goes in. Then follow the rooms: brainstorm, professor approval, bench, paper, integrity check, professor sign-off, unseal.

- Address agents with `@`. They only act on messages addressed to them.
- Don't remove an agent from a room. If an agent goes quiet, read `~/.config/switchdash/logs/switch-console.log`.
- Don't paste a sealed term, and don't mention the paper, until the unseal.
- Record one approval on a phone, and the professor's approval on a phone.

## After the run

1. Run `just audit --since START` and save the output with the mission.
2. Check every number in the PDF against the logs by hand.
3. Blur the passphrase in the video, and rotate the Slack tokens.
4. Show the real scorecard, whatever it says.
