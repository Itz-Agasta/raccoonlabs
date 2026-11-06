#!/usr/bin/env python3
"""List what lab agents' session logs recorded that could have reached the web or a sealed path.

`just audit [--since ISO-TIME]` reads Switch's local session logs, and prints every matching
shell command by agent. It's evidence, not proof: it covers commands agents ran through their tools,
and Switch's logs shorten long commands.
"""
import argparse
import json
import re
from pathlib import Path

SESSIONS = Path.home() / ".local/state/switch/sdk-sessions"
RISKY = re.compile(r"\b(curl|wget|urllib|requests\.|httpx|aiohttp|socket|nc |ssh |scp |git clone|lynx|w3m|chrome|firefox)\b|https?://|notes/|sealed|\.enc\b|raccoonlabs/env", re.I)
ALLOWED = re.compile(r"^(?:\S*/)?(lab-search|lab-paper|lab-integrity|labrun)\b")
BUILD_ONLY = {"dev-ops", "switch-buddy-admin"}


def agent_of(config):
    found = re.search(r'agents/[^/"]+/([\w-]+)', config.read_text(errors="ignore"))
    return found.group(1) if found else None


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--since", default="", help="ignore events before this UTC time, such as 2026-11-07T04:00")
    p.add_argument("--sessions", type=Path, default=SESSIONS)
    args = p.parse_args()
    counts, hits = {}, []
    for session in sorted(args.sessions.glob("*")):
        config, events = session / "config.json", session / "events.jsonl"
        if not config.exists() or not events.exists():
            continue
        agent = agent_of(config)
        if not agent or agent in BUILD_ONLY:
            continue
        for line in events.read_text(errors="ignore").splitlines():
            event = json.loads(line)
            item = event["body"].get("item") or {}
            if item.get("kind") != "tool-activity" or item.get("status") not in ("completed", "failed"):
                continue
            if event["occurredAt"] < args.since:
                continue
            title = item.get("title", "")
            counts[agent] = counts.get(agent, 0) + 1
            if RISKY.search(title) and not ALLOWED.match(title):
                hits.append((event["occurredAt"][:19], agent, item["status"], title[:160]))
    print("Tool calls read, by agent:", ", ".join(f"{a} {n}" for a, n in sorted(counts.items())) or "none")
    for hit in sorted(hits):
        print(" | ".join(hit))
    print(f"{len(hits)} matching calls. Logs shorten long commands, so this is evidence, not proof.")


if __name__ == "__main__":
    main()
