"""lab-search: the only way lab agents look up literature."""
import hashlib
import json

import pytest

import lab_search as ls

ARXIV_XML = """<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
<entry><id>http://arxiv.org/abs/2401.00001v2</id><published>2024-01-02T00:00:00Z</published>
<title>Open Paper
  On Learning</title><summary> An open abstract. </summary>
<author><name>Ada Lovelace</name></author><author><name>Alan Turing</name></author></entry>
<entry><id>http://arxiv.org/abs/2599.12345v1</id><published>2025-09-01T00:00:00Z</published>
<title>Hidden Sealed Work</title><summary>Sealed abstract.</summary><author><name>S. Author</name></author></entry>
</feed>"""
CROSSREF = {"message": {"items": [
    {"DOI": "10.1/open", "title": ["A Journal Paper"], "author": [{"given": "Grace", "family": "Hopper"}], "issued": {"date-parts": [[2020]]}},
    {"DOI": "10.1/x", "title": ["Hidden: Sealed   WORK"], "issued": {"date-parts": [[2021]]}},
]}}


def digest(term):
    return hashlib.sha256(ls.normalise(term).encode()).hexdigest()


@pytest.fixture
def env(tmp_path, monkeypatch):
    block = tmp_path / "blocklist.sha256"
    block.write_text("\n".join([digest("2599.12345"), digest("Hidden Sealed Work")]) + "\n")
    monkeypatch.setattr(ls, "BLOCKLIST", block)
    monkeypatch.setattr(ls, "LOG", tmp_path / "log.jsonl")
    monkeypatch.setattr(ls, "SOURCES_LOG", tmp_path / "sources.jsonl")
    calls = []

    def fake_get(url):
        calls.append(url)
        if "arxiv" in url:
            return ARXIV_XML
        if "crossref" in url:
            return json.dumps(CROSSREF)
        raise OSError("HTTP 429")

    monkeypatch.setattr(ls, "http_get", fake_get)
    return tmp_path, calls


def logged(tmp):
    return [json.loads(x) for x in (tmp / "log.jsonl").read_text().splitlines()]


def test_normalise_ignores_case_spacing_and_punctuation():
    assert ls.normalise("Hidden: Sealed   WORK") == ls.normalise("hidden sealed-work")


def test_sealed_results_are_withheld_by_id_and_title(env, capsys):
    assert ls.main(["search", "learning", "--source", "all"]) == 0
    out = capsys.readouterr().out
    assert "Open Paper On Learning" in out and "A Journal Paper" in out
    assert "Hidden" not in out and "2599.12345" not in out
    assert "withheld: 2" in out


def test_version_suffix_does_not_defeat_the_id_block(env, capsys):
    assert ls.main(["read", "2599.12345v3"]) == 3
    assert "Sealed abstract" not in capsys.readouterr().out


def test_query_matching_a_sealed_item_is_refused_without_any_request(env, capsys):
    _, calls = env
    assert ls.main(["search", "hidden sealed WORK"]) == 3
    assert calls == []
    assert "refused" in capsys.readouterr().err


def test_query_containing_a_sealed_id_is_refused(env):
    _, calls = env
    assert ls.main(["search", "see arXiv:2599.12345v2 please"]) == 3
    assert calls == []


def test_every_query_is_logged_including_refusals(env):
    tmp, _ = env
    ls.main(["search", "learning", "--source", "arxiv"])
    ls.main(["search", "hidden sealed work"])
    entries = logged(tmp)
    assert [e["query"] for e in entries] == ["learning", "hidden sealed work"]
    assert entries[0]["withheld"] == 1 and entries[0]["refused"] is False
    assert entries[1]["refused"] is True


def test_source_failure_is_reported_and_others_still_answer(env, capsys):
    assert ls.main(["search", "learning", "--source", "all"]) == 0
    assert "s2 failed" in capsys.readouterr().out


def test_all_sources_failing_is_an_error(env, monkeypatch, capsys):
    def down(url):
        raise OSError("offline")

    monkeypatch.setattr(ls, "http_get", down)
    assert ls.main(["search", "learning"]) == 1
    assert "failed" in capsys.readouterr().out


def test_results_include_usable_bibtex(env, capsys):
    ls.main(["search", "learning", "--source", "arxiv"])
    out = capsys.readouterr().out
    assert "@misc{lovelace2024open," in out
    assert "author = {Ada Lovelace and Alan Turing}" in out
    assert "eprint = {2401.00001}" in out


def test_read_returns_the_abstract_of_an_open_paper(env, capsys):
    assert ls.main(["read", "2401.00001"]) == 0
    assert "An open abstract." in capsys.readouterr().out


def test_missing_blocklist_fails_closed(env, monkeypatch, capsys):
    tmp, calls = env
    monkeypatch.setattr(ls, "BLOCKLIST", tmp / "gone")
    assert ls.main(["search", "learning"]) == 1
    assert calls == []
    assert "blocklist" in capsys.readouterr().err


def test_subtitle_variant_of_a_sealed_title_is_withheld(env, monkeypatch, capsys):
    monkeypatch.setattr(ls, "search_arxiv", lambda q, n: [ls.paper("Hidden Sealed Work: A Longer Subtitle", [], "2025", "arxiv", "2501.00001", arxiv="2501.00001")])
    ls.main(["search", "x", "--source", "arxiv"])
    out = capsys.readouterr().out
    assert "Longer Subtitle" not in out and "withheld: 1" in out


def test_arxiv_search_requires_every_word(env):
    _, calls = env
    ls.main(["search", "modular arithmetic", "--source", "arxiv"])
    assert "all%3Amodular+AND+all%3Aarithmetic" in calls[0]


def test_results_are_remembered_for_the_integrity_check_but_sealed_ones_never(env):
    tmp, _ = env
    assert ls.main(["search", "open", "--source", "arxiv"]) == 0
    saved = (tmp / "sources.jsonl").read_text()
    assert "Open Paper" in saved and "Hidden" not in saved
