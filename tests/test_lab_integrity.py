"""The integrity check: what stops a draft, and what only asks a person to look."""
import json

import pytest

import lab_integrity as li

TEX = r"""\title{A real title}
\begin{document}
\section{Results}
The model reached 0.91 over 3 seeds~\cite{ada2024open}.
\section{Conclusion}
It worked.
\bibliography{refs}
\end{document}
"""
BIB = "@misc{ada2024open,\n  title = {Open Paper},\n  author = {Ada},\n  year = {2024},\n  eprint = {2401.00001},\n}\n"


@pytest.fixture
def lab(tmp_path):
    paper = tmp_path / "paper"
    paper.mkdir()
    (paper / "main.tex").write_text(TEX)
    (paper / "refs.bib").write_text(BIB)
    (paper / "provenance.txt").write_text("# a comment\nNOISE1  the main result\n")
    batch = tmp_path / "runs/NOISE1"
    batch.mkdir(parents=True)
    (batch / "manifest.json").write_text(json.dumps({
        "batch": "NOISE1", "seeds_requested": [0, 1, 2], "finished_at": "x", "seeds": [{"exit_code": 0}] * 3}))
    (batch / "seed-0.log").write_text("accuracy 0.9100\n")
    (tmp_path / "sources.jsonl").write_text(json.dumps({"title": "Open Paper", "arxiv": "2401.00001", "doi": "", "abstract": "short text"}) + "\n")
    return tmp_path


def run(lab, capsys):
    code = li.main(["check", str(lab / "paper"), "--runs-dir", str(lab / "runs"), "--sources", str(lab / "sources.jsonl")])
    return code, capsys.readouterr().out


def edit(lab, old, new):
    p = lab / "paper/main.tex"
    p.write_text(p.read_text().replace(old, new))


def test_clean_paper_passes_with_no_disclosure_section(lab, capsys):
    code, out = run(lab, capsys)
    assert code == 0, out
    assert "FLAG" not in out


def test_citation_lab_search_never_returned_fails(lab, capsys):
    (lab / "sources.jsonl").write_text("")
    code, out = run(lab, capsys)
    assert code == 1 and "never returned" in out


def test_batch_failing_labrun_check_fails(lab, capsys):
    (lab / "paper/provenance.txt").write_text("MISSING7  a result\n")
    code, out = run(lab, capsys)
    assert code == 1 and "MISSING7" in out


def test_no_provenance_fails(lab, capsys):
    (lab / "paper/provenance.txt").unlink()
    code, out = run(lab, capsys)
    assert code == 1 and "lists no batch" in out


@pytest.mark.parametrize("word", ["NOISE1", "Quill", "Slack", "laptop", "RAM", "labrun"])
def test_lab_machinery_in_the_paper_fails(lab, capsys, word):
    edit(lab, "It worked.", f"It worked with {word}.")
    code, out = run(lab, capsys)
    assert code == 1 and f"machinery: {word}" in out


def test_ordinary_words_are_not_machinery(lab, capsys):
    edit(lab, "It worked.", "A random patch of the framework ran.")
    code, _ = run(lab, capsys)
    assert code == 0


def test_template_text_fails(lab, capsys):
    edit(lab, "It worked.", "What was found, and what should come next.")
    code, out = run(lab, capsys)
    assert code == 1 and "template text" in out


def test_number_not_in_logs_is_flagged(lab, capsys):
    edit(lab, "0.91", "0.99")
    code, out = run(lab, capsys)
    assert code == 0 and "FLAG number 0.99" in out


def test_overlap_with_a_source_is_flagged(lab, capsys):
    phrase = "the quick brown fox jumps over the lazy dog again"
    (lab / "sources.jsonl").write_text(json.dumps({"title": "Open Paper", "arxiv": "2401.00001", "abstract": phrase}) + "\n")
    edit(lab, "It worked.", phrase + ".")
    code, out = run(lab, capsys)
    assert code == 0 and "overlap" in out


def test_numbers_in_a_named_analysis_file_are_not_flagged(lab, capsys):
    edit(lab, "0.91", "0.99")
    (lab / "table.csv").write_text("mean,0.99\n")
    with (lab / "paper/provenance.txt").open("a") as f:
        f.write(f"FILE {lab / 'table.csv'}\n")
    code, out = run(lab, capsys)
    assert code == 0 and "FLAG number" not in out


def test_missing_analysis_file_fails(lab, capsys):
    with (lab / "paper/provenance.txt").open("a") as f:
        f.write("FILE /no/such/file\n")
    code, out = run(lab, capsys)
    assert code == 1 and "missing file" in out
