# What lab agents can reach

Measured by asking each deployed agent to try each action: Bandit, Patch and Reviewer 2 on 2026-11-04 in `#lab-core`, Ringtail, Quill and Scout on 2026-11-04 and 2026-11-06 in the lab rooms. This is what the demo may claim. Blocked means the attempt failed or the tool doesn't exist; it doesn't mean the agent chose not to.

| Check | Ringtail, Bandit, Patch, Quill (Claude Code) | Reviewer 2 (Codex) | Scout (OpenCode) |
|---|---|---|---|
| Built-in web search | Blocked: no tool | Blocked: no tool since `just harden` | Reports no tool since `just harden`; declined to try |
| Built-in web fetch | Blocked: no tool | Blocked: no tool since `just harden` | Reports no tool since `just harden`; declined to try |
| User's MCP servers (Exa, Chrome) | Blocked: none callable | None offered | Reports none since `just harden` |
| Shell network (`curl`) | **Open: HTTP 200** | Blocked by Codex's sandbox (exit 6) | Denied in config, not proven: it declined to try. Other programs could still reach the network |
| Read files outside own folder | **Open** | **Open** | **Open** (counted `notes/`, read nothing) |
| Literature search | Not given | Not given | `lab-search`, every query logged |
| Working folder | `~/.switch/agents/localhost-40401/<agent>` | Same pattern | Same pattern |

`just harden` writes `agents/config/` into the agents' folders. Switch's `webSearch: "false"` alone had no effect on Reviewer 2 (web search returned results before), and Scout listed `websearch`, `webfetch` and Chrome tools before it. A `Bash(curl:*)` deny rule can't close the Claude agents' shell route under Switch, because it removes Bash altogether.

## Skills

`just skills` links the research skills into each agent's folder. Probed 2026-11-06: each agent loaded one. Agents also inherit this user's global skills, so the Claude agents list `exa:search`, `composio-cli` and browser skills, and Reviewer 2 lists `agent-reach`. A skill brings instructions, not tools: the browser and Exa tools aren't callable, but a skill that shells out to a CLI could use the Claude agents' open shell route. `just audit` looks for the commands that route would need.

## Gaps that follow from this

- **Evidence isn't tamper-proof.** Agents run as the same OS user as the run files. `labrun` refuses to overwrite and marks finished files read-only, which stops accidents, not deletion. The sha256 posted in the room is the anchor.
- **Approval rests on agent behaviour.** `labrun` records what it's given, so it can't tell a forged `--approved-by` from a real one. Reviewer 2 checks it against the room. Agents can also read files this user can, which would include any Slack token left on the machine, so `~/.config/raccoonlabs/env` must be removed before a recorded run.
- **Timing seeds run without a manifest.** Patch may run one under `timeout 120` before asking, and must say so.

## Memory

With the server, Console, a browser and three agents working at once (2026-11-04), the lowest `free -m` available reading was 3,023 MB of 7,579 MB, sampled about every 6 seconds through the access check. An idle baseline wasn't recorded. Each agent process used about 260-380 MB. With six agent sessions and a browser open, it fell to 1,165 MB. Close the browser for final runs.

## What the demo may claim today

- Claude Code and Codex lab agents have no built-in web or MCP web tools. Scout reports none.
- Reviewer 2's shell can't reach the network.
- Nothing stops a Claude agent's shell from reaching the web, or any agent from reading files this user can read.

Don't say the agents couldn't have looked anything up. Say what was blocked, and show the audit from `just audit`, which lists every network command and every access to a sealed path that the agents' session logs recorded.
