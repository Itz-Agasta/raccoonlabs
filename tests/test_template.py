"""The core template, read the way Switch reads it: as data."""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "switch/lab.template.yaml"
NAMES = ("ringtail", "bandit", "scout", "patch", "quill", "reviewer-2")
WEB_TOOLS = {"WebSearch", "WebFetch"}


@pytest.fixture(scope="module")
def doc():
    return yaml.safe_load(TEMPLATE.read_text())


@pytest.fixture(scope="module")
def agents(doc):
    return {a["name"]: a for a in doc["agents"]}


def test_agents_and_providers(agents):
    assert {n: a["provider"] for n, a in agents.items()} == {
        "ringtail": "claude", "bandit": "claude", "scout": "opencode",
        "patch": "claude", "quill": "claude", "reviewer-2": "codex",
    }


def test_anyone_in_the_room_can_address_them(agents):
    assert {a["addressing"] for a in agents.values()} == {"anyone"}


def test_web_settings_are_requested(agents):
    for name in ("ringtail", "bandit", "patch", "quill"):
        cfg = agents[name]["advanced_config"]
        assert {"Bash", "Read", "Write", "Edit", "Glob", "Grep", "Skill"} <= set(cfg["tools"])
        assert not any(t.startswith("Bash(") for t in cfg["disallowedTools"])
        assert WEB_TOOLS <= set(cfg["disallowedTools"])
    for name in ("reviewer-2", "scout"):
        assert agents[name]["advanced_config"]["webSearch"] == "false"


def test_agents_work_outside_the_repo(agents):
    # Written per agent: {agent} is only defined for single-agent templates.
    for name, agent in agents.items():
        assert agent["directory"] == f"{{$agents_dir}}/{name}"


def test_four_private_linked_rooms_with_the_right_members(doc):
    rooms = {r["name"]: r for r in doc["rooms"]}
    assert set(rooms) == {"lab-brainstorm", "lab-bench", "lab-paper", "lab-review"}
    assert all(r["channel_type"] == "channel_private" for r in rooms.values())
    # Only the agent that created a room document can edit it, so agents create their own.
    assert not any("docs" in r for r in rooms.values())
    assert {"patch", "reviewer-2", "bandit"} <= set(rooms["lab-bench"]["agents"])
    assert "quill" in rooms["lab-paper"]["agents"] and "quill" not in rooms["lab-review"]["agents"]
    assert {"ringtail", "reviewer-2"} <= set(rooms["lab-review"]["agents"])
    assert len(doc["links"]) == 3


def test_persona_text_matches_files(agents):
    for name, agent in agents.items():
        assert agent["instructions"].strip() == (ROOT / f"agents/{name}.md").read_text().strip()


def test_reviewer_web_access_is_really_closed():
    assert "**Open: search returned results**" not in (ROOT / "docs/agent-access.md").read_text()


def test_reviewer_verifies_approval_and_evidence():
    reviewer = (ROOT / "agents/reviewer-2.md").read_text()
    assert "approved_by" in reviewer and "sha256" in reviewer and "exact command" in reviewer


def test_patch_rules_for_timing_approval_and_evidence():
    patch = (ROOT / "agents/patch.md").read_text()
    assert "one timing seed" in patch and "timeout 120" in patch
    assert "Slack timestamp" in patch
    assert "Never delete or edit a batch" in patch
    assert "sha256" in patch


def test_bandit_escalates_when_a_peer_goes_quiet():
    assert "hasn't answered" in (ROOT / "agents/bandit.md").read_text()


def test_gate_rules_present():
    patch = (ROOT / "agents/patch.md").read_text()
    reviewer = (ROOT / "agents/reviewer-2.md").read_text()
    bandit = (ROOT / "agents/bandit.md").read_text()
    assert "--approved-by" in patch and "No approval, no run" in patch
    assert "labrun check" in reviewer and "3 seeds" in reviewer
    assert "Create the room documents `Tasks` and `Notebook` yourself" in bandit and "never run experiments" in bandit


def test_personas_have_no_template_placeholders():
    # Switch treats any {name} in a template as a placeholder and refuses unknown ones.
    for name in NAMES:
        assert "{" not in (ROOT / f"agents/{name}.md").read_text()


def test_new_persona_rules_present():
    ringtail = (ROOT / "agents/ringtail.md").read_text()
    scout = (ROOT / "agents/scout.md").read_text()
    quill = (ROOT / "agents/quill.md").read_text()
    assert "Push back first" in ringtail and "`Plan`" in ringtail
    assert "lab-search" in scout and "`Library`" in scout and "no browser" in scout
    assert "lab-paper build" in quill and "batch that Reviewer 2 accepted" in quill and "send_attachment" in quill
