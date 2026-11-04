"""lab-paper: real PDFs from the template, or a clear failure."""
import base64

import lab_paper as lp

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M/wHwAEBgIApD5fRAAAAABJRU5ErkJggg==")


def fresh(tmp_path):
    d = tmp_path / "paper"
    assert lp.main(["new", str(d)]) == 0
    return d


def test_new_creates_the_template(tmp_path):
    d = fresh(tmp_path)
    assert (d / "main.tex").exists() and (d / "refs.bib").exists() and (d / "figures/method.tex").exists()


def test_new_refuses_to_overwrite(tmp_path):
    d = fresh(tmp_path)
    (d / "main.tex").write_text("mine")
    assert lp.main(["new", str(d)]) != 0
    assert (d / "main.tex").read_text() == "mine"


def test_template_builds_a_real_pdf_with_diagram(tmp_path):
    d = fresh(tmp_path)
    assert lp.main(["build", str(d)]) == 0
    assert (d / "main.pdf").read_bytes().startswith(b"%PDF")


def test_undefined_citation_fails_the_build(tmp_path, capsys):
    d = fresh(tmp_path)
    (d / "main.tex").write_text((d / "main.tex").read_text().replace(r"\section{Introduction}", r"\section{Introduction} \cite{nosuchkey}"))
    assert lp.main(["build", str(d)]) != 0
    assert "nosuchkey" in capsys.readouterr().err


def test_missing_figure_fails_the_build(tmp_path, capsys):
    d = fresh(tmp_path)
    (d / "main.tex").write_text((d / "main.tex").read_text().replace(r"\section{Results}", "\\section{Results}\n\\includegraphics{figures/gone.png}"))
    assert lp.main(["build", str(d)]) != 0


def test_png_figure_builds(tmp_path):
    d = fresh(tmp_path)
    (d / "figures/plot.png").write_bytes(PNG)
    (d / "main.tex").write_text((d / "main.tex").read_text().replace(r"\section{Results}", "\\section{Results}\n\\includegraphics[width=2cm]{figures/plot.png}"))
    assert lp.main(["build", str(d)]) == 0
