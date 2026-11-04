# What lab agents can reach

Measured on 2026-11-04 by asking each deployed agent in `#lab-core` to try each action. This is what the demo may claim. Blocked means the attempt failed or the tool doesn't exist; it doesn't mean the agent chose not to.

| Check | Bandit, Patch (Claude Code) | Reviewer 2 (Codex) |
|---|---|---|
| Built-in web search | Blocked: no tool | **Open: search returned results** |
| Built-in web fetch | Blocked: no tool | **Open: fetched the page** |
| User's MCP servers (Exa, Chrome) | Blocked: not in the tool list | None offered, but `codex_apps` tools (such as Canva) are |
| Shell network (`curl`) | **Open: HTTP 200** | Blocked by Codex's sandbox (exit 6) |
| Read files outside own folder | **Open** | **Open** |
| `labrun` | Works | Works |
| Working folder | `~/.switch/agents/localhost-40401/<agent>` | Same pattern |

Settings used are in `switch/core.base.yaml`. Reviewer 2 has `webSearch: "false"`, which had no effect in this test.

## Memory

With the server, Console, a browser and all three agents working at once, available memory never fell below 3,023 MB of 7,579 MB. Each agent process used about 260-380 MB.

## What the demo may claim today

- Claude Code lab agents have no built-in web or MCP web tools.
- Nothing stops an agent with shell network access from reaching the web, or any agent from reading files this user can read.

Don't say the agents couldn't have looked anything up. See the project's open decision on hardening before a blind run.
