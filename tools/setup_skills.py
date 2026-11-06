#!/usr/bin/env python3
"""Install third-party research skills for the lab's agents: `just skills`.

The skills are licensed separately (academic-research-skills is CC BY-NC, the others MIT or similar), so they're cloned
outside this repo at pinned commits and linked into each agent's folder, never copied here.
Run after the template has created the agents.
"""
import subprocess
from pathlib import Path

HOME = Path.home() / ".local/share/raccoonlabs/skills"
REPOS = {
    "ars": ("https://github.com/Imbad0202/academic-research-skills.git", "6d9388674de1"),
    "ars-codex": ("https://github.com/Imbad0202/academic-research-skills-codex.git", "82725acb393c"),
    "opentikz": ("https://github.com/opentikz/opentikz.git", "359befbf8e8a"),
    "cvpr-figure": ("https://github.com/ChizkiyahuOhayon/CVPR-Figure.git", "8adb0d6b881e"),
    "kdense": ("https://github.com/K-Dense-AI/scientific-agent-skills.git", "a25cf9ec00e2"),
}
ARS = {name: f"ars/{name}" for name in ("deep-research", "academic-paper", "academic-paper-reviewer")}
KDENSE = {name: f"kdense/skills/{name}" for name in (
    "statistical-analysis", "statistical-power", "scientific-critical-thinking", "scientific-visualization", "hypothesis-generation")}
CLAUDE_SKILLS = {
    "ringtail": {k: ARS[k] for k in ARS} | {k: KDENSE[k] for k in ("scientific-critical-thinking", "hypothesis-generation")},
    "patch": {k: KDENSE[k] for k in ("statistical-analysis", "statistical-power")},
    "quill": {"academic-paper": ARS["academic-paper"], "using-opentikz": "opentikz/skills/using-opentikz", "cvpr-figure": "cvpr-figure",
              "scientific-visualization": KDENSE["scientific-visualization"]},
    "scout": {"deep-research": ARS["deep-research"]},  # OpenCode also reads .claude/skills
}
CODEX_SKILLS = {k: KDENSE[k] for k in ("statistical-analysis", "scientific-critical-thinking")}


def fetch(name, url, commit):
    target = HOME / name
    if not target.exists():
        subprocess.run(["git", "clone", "-q", "--filter=blob:none", url, str(target)], check=True)
    subprocess.run(["git", "-C", str(target), "fetch", "-q", "origin"], check=True)
    subprocess.run(["git", "-C", str(target), "checkout", "-q", commit], check=True)
    print(f"{name} at {commit}")


def link(folder, name, source):
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    if path.is_symlink() or path.exists():
        path.unlink()
    path.symlink_to(source)
    print(f"  {path} -> {source}")


HOME.mkdir(parents=True, exist_ok=True)
for name, (url, commit) in REPOS.items():
    fetch(name, url, commit)
servers = list((Path.home() / ".switch/agents").glob("*"))
if not servers:
    raise SystemExit("no agents yet: run the template in Switch first")
for server in servers:
    for agent, skills in CLAUDE_SKILLS.items():
        for name, rel in skills.items():
            link(server / agent / ".claude/skills", name, HOME / rel)
    for skill in sorted((HOME / "ars-codex/plugins/ars-codex/skills").iterdir()):
        if skill.is_dir():
            link(server / "reviewer-2/.agents/skills", skill.name, skill)
    for name, rel in CODEX_SKILLS.items():
        link(server / "reviewer-2/.agents/skills", name, HOME / rel)
