#!/usr/bin/env python3
"""Copy per-agent lockdown settings into the folders Switch runs the agents in.

Switch's webSearch setting has no effect on Codex or OpenCode, so Reviewer 2 and
Scout get project-level config files. Run after the template has created the agents.
"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = {"scout": ("agents/config/scout.opencode.json", "opencode.json"),
         "reviewer-2": ("agents/config/reviewer-2.codex.toml", ".codex/config.toml")}

servers = list((Path.home() / ".switch/agents").glob("*"))
if not servers:
    raise SystemExit("no agents yet: run the template in Switch first")
for server in servers:
    for agent, (src, dest) in FILES.items():
        target = server / agent / dest
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / src, target)
        print(f"wrote {target}")
print("restart any running Scout session so it reads the new settings")
