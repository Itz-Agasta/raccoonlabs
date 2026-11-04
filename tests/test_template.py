"""The core template, read the way Switch reads it: as data."""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "switch/core.template.yaml"
WEB_TOOLS = {"WebSearch", "WebFetch"}


@pytest.fixture(scope="module")
def doc():
    return yaml.safe_load(TEMPLATE.read_text())


@pytest.fixture(scope="module")
def agents(doc):
    return {a["name"]: a for a in doc["agents"]}


def test_agents_and_providers(agents):
    assert {n: a["provider"] for n, a in agents.items()} == {"bandit": "claude", "patch": "claude", "reviewer-2": "codex"}


def test_anyone_in_the_room_can_address_them(agents):
    assert {a["addressing"] for a in agents.values()} == {"anyone"}


def test_web_access_is_off(agents):
    for name in ("bandit", "patch"):
        cfg = agents[name]["advanced_config"]
        assert set(cfg["tools"]) == {"Bash", "Read", "Write", "Edit", "Glob", "Grep"}
        assert WEB_TOOLS <= set(cfg["disallowedTools"])
    assert agents["reviewer-2"]["advanced_config"]["webSearch"] == "false"


def test_agents_work_outside_the_repo(agents):
    # Written per agent: {agent} is only defined for single-agent templates.
    for name, agent in agents.items():
        assert agent["directory"] == f"{{$agents_dir}}/{name}"


def test_room_is_private_with_docs(doc):
    room = doc["room"]
    assert room["channel_type"] == "channel_private"
    assert room["name"] == "lab-core"
    assert {d["name"] for d in room["docs"]} == {"Tasks", "Notebook"}
    assert set(room["agents"]) == {"bandit", "patch", "reviewer-2"}


def test_persona_text_matches_files(agents):
    for name, agent in agents.items():
        assert agent["instructions"].strip() == (ROOT / f"agents/{name}.md").read_text().strip()


def test_gate_rules_present():
    patch = (ROOT / "agents/patch.md").read_text()
    reviewer = (ROOT / "agents/reviewer-2.md").read_text()
    bandit = (ROOT / "agents/bandit.md").read_text()
    assert "--approved-by" in patch and "No approval, no run" in patch
    assert "labrun check" in reviewer and "3 seeds" in reviewer
    assert "Tasks" in bandit and "Notebook" in bandit and "never run experiments" in bandit


def test_personas_have_no_template_placeholders():
    # Switch treats any {name} in a template as a placeholder and refuses unknown ones.
    for name in ("bandit", "patch", "reviewer-2"):
        assert "{" not in (ROOT / f"agents/{name}.md").read_text()
