"""The envelope: sealed contents stay closed without the passphrase, and scorecards name evidence."""
import io
import json

import pytest

import lab_envelope as le


def seal(tmp_path, monkeypatch, phrase="pw one"):
    src = tmp_path / "src"
    src.mkdir()
    (src / "claims.md").write_text("C1: secret claim\n")
    monkeypatch.setattr("sys.stdin", io.StringIO(phrase + "\n"))
    out = tmp_path / "sealed.enc"
    assert le.main(["seal", str(src), "--out", str(out), "--passphrase-stdin"]) == 0
    return out


def unseal(out, target, monkeypatch, phrase):
    monkeypatch.setattr("sys.stdin", io.StringIO(phrase + "\n"))
    return le.main(["unseal", str(target), "--in", str(out), "--passphrase-stdin"])


def test_right_passphrase_opens_it(tmp_path, monkeypatch):
    out = seal(tmp_path, monkeypatch)
    assert b"secret claim" not in out.read_bytes()
    assert unseal(out, tmp_path / "open", monkeypatch, "pw one") == 0
    assert (tmp_path / "open/claims.md").read_text() == "C1: secret claim\n"


def test_wrong_passphrase_opens_nothing(tmp_path, monkeypatch):
    out = seal(tmp_path, monkeypatch)
    assert unseal(out, tmp_path / "open", monkeypatch, "wrong") == 1
    assert not (tmp_path / "open").exists()


def test_changed_envelope_is_refused(tmp_path, monkeypatch):
    out = seal(tmp_path, monkeypatch)
    blob = bytearray(out.read_bytes())
    blob[-1] ^= 1
    out.write_bytes(blob)
    assert unseal(out, tmp_path / "open", monkeypatch, "pw one") == 1


def test_empty_passphrase_refused(tmp_path, monkeypatch):
    src = tmp_path / "f"
    src.write_text("x")
    monkeypatch.setattr("sys.stdin", io.StringIO("\n"))
    assert le.main(["seal", str(src), "--out", str(tmp_path / "o"), "--passphrase-stdin"]) == 1


@pytest.fixture
def card(tmp_path):
    (tmp_path / "claims.md").write_text("C1: a\nC2: b\n")
    runs = tmp_path / "runs/B1"
    runs.mkdir(parents=True)
    (runs / "manifest.json").write_text(json.dumps({
        "batch": "B1", "seeds_requested": [0, 1, 2], "finished_at": "x", "seeds": [{"exit_code": 0}] * 3}))
    return tmp_path


def check(card, text):
    (card / "card.md").write_text(text)
    return le.main(["scorecard-check", str(card / "card.md"), "--claims", str(card / "claims.md"), "--runs-dir", str(card / "runs")])


def test_good_scorecard_passes(card):
    assert check(card, "| C1 | a | B1 | match |\n| C2 | b | - | not tested |\n") == 0


def test_missing_claim_fails(card):
    assert check(card, "| C1 | a | B1 | match |\n") == 1


def test_verdict_without_real_batch_fails(card):
    assert check(card, "| C1 | a | B9 | match |\n| C2 | b | - | not tested |\n") == 1


def test_unknown_verdict_fails(card):
    assert check(card, "| C1 | a | B1 | proven |\n| C2 | b | - | not tested |\n") == 1
