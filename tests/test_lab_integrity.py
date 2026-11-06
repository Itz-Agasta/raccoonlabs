"""The integrity check: what stops a draft, and what only asks a person to look."""
import json

import pytest

import lab_integrity as li

TEX = r"""\title{A real title}
\begin{document}
\section{Results}
Batch B1 reached 0.91 over 3 seeds~\cite{ada2024open}.
\section*{AI use disclosure}
Quill drafted Method. Students wrote Results.
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
    batch = tmp_path / "runs/B1"
    batch.mkdir(parents=True)
    (batch / "manifest.json").write_text(json.dumps({
        "batch": "B1", "seeds_requested": [0, 1, 2], "finished_at": "x", "seeds": [{"exit_code": 0}] * 3}))
    (batch / "seed-0.log").write_text("accuracy 0.91\n")
    (tmp_path / "sources.jsonl").write_text(json.dumps({"title": "Open Paper", "arxiv": "2401.00001", "doi": "", "abstract": "short text"}) + "\n")
    return tmp_path


def run(lab, capsys):
    code = li.main(["check", str(lab / "paper"), "--runs-dir", str(lab / "runs"), "--sources", str(lab / "sources.jsonl")])
    return code, capsys.readouterr().out


def edit(lab, old, new):
    p = lab / "paper/main.tex"
    p.write_text(p.read_text().replace(old, new))


def test_clean_paper_passes(lab, capsys):
    code, out = run(lab, capsys)
    assert code == 0, out
    assert "FLAG" not in out


def test_citation_lab_search_never_returned_fails(lab, capsys):
    (lab / "sources.jsonl").write_text("")
    code, out = run(lab, capsys)
    assert code == 1 and "never returned" in out


def test_batch_failing_labrun_check_fails(lab, capsys):
    edit(lab, "Batch B1", "Batch B7")
    code, out = run(lab, capsys)
    assert code == 1 and "B7" in out


def test_results_without_a_batch_fails(lab, capsys):
    edit(lab, "Batch B1 reached", "We reached")
    code, out = run(lab, capsys)
    assert code == 1 and "names no batch" in out


def test_missing_disclosure_fails(lab, capsys):
    edit(lab, "Quill drafted Method. Students wrote Results.", "")
    code, out = run(lab, capsys)
    assert code == 1 and "disclosure" in out


def test_template_text_fails(lab, capsys):
    edit(lab, "Quill drafted Method.", "State which sections the students wrote and which")
    code, out = run(lab, capsys)
    assert code == 1 and "template text" in out


def test_number_not_in_logs_is_flagged(lab, capsys):
    edit(lab, "0.91", "0.99")
    code, out = run(lab, capsys)
    assert code == 0 and "FLAG number 0.99" in out


def test_overlap_with_a_source_is_flagged(lab, capsys):
    phrase = "the quick brown fox jumps over the lazy dog again"
    (lab / "sources.jsonl").write_text(json.dumps({"title": "Open Paper", "arxiv": "2401.00001", "abstract": phrase}) + "\n")
    edit(lab, "Quill drafted Method.", phrase + ".")
    code, out = run(lab, capsys)
    assert code == 0 and "overlap" in out


def test_any_batch_name_counts(lab, capsys):
    (lab / "runs/B1").rename(lab / "runs/NOISE1")
    edit(lab, "Batch B1", "Batch NOISE1")
    code, out = run(lab, capsys)
    assert code == 0 and "NOISE1" in out


def test_unfilled_author_line_fails(lab, capsys):
    edit(lab, r"\title{A real title}", r"\title{A real title}\author{Author names (students write this line)}")
    code, out = run(lab, capsys)
    assert code == 1 and "template text" in out
