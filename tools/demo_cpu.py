#!/usr/bin/env python3
"""Run the lab's whole tool chain on CPU with no accounts: `just demo-cpu`.

Seeded runs -> evidence check -> paper with a real plot -> integrity check -> envelope -> scorecard.
Agents and Slack aren't involved: this proves the tools a judge can run in minutes. Everything
goes in a fresh folder under build/demo-cpu, and the sealed claim is a toy written here.
"""
import json
import re
import shutil
import statistics
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build/demo-cpu"
RUNS = OUT / "runs"
PAPER = OUT / "paper"
BIN = Path(sys.executable).parent


def step(title):
    print(f"\n== {title}", flush=True)


def run(*cmd, stdin=None):
    r = subprocess.run([str(c) for c in cmd], text=True, input=stdin, capture_output=True, cwd=OUT)
    print(r.stdout.rstrip())
    if r.returncode != 0:
        print(r.stderr.rstrip())
        sys.exit(f"demo-cpu stopped: {' '.join(str(c) for c in cmd)} exited {r.returncode}")
    return r.stdout


def tool(name):
    found = BIN / name
    if found.exists():
        return found
    path = shutil.which(name)
    if not path:
        sys.exit(f"{name} isn't on PATH: run `just install-tools`")
    return path


shutil.rmtree(OUT, ignore_errors=True)
OUT.mkdir(parents=True)
exp = ROOT / "examples/demo-cpu/exp.py"
labrun, lab_paper, integrity, envelope = map(tool, ("labrun", "lab-paper", "lab-integrity", "lab-envelope"))

step("1. Seeded runs through labrun (the approval here is the person running this demo)")
means = {}
for batch, noise in (("B1", 0.0), ("B2", 0.2)):
    run(labrun, "exec", "--runs-dir", RUNS, "--batch", batch, "--seeds", "0,1,2",
        "--approved-by", "demo-cpu operator: ran just demo-cpu", "--", "uv", "run", "--no-project", "--with", "numpy", "python", exp, "--seed", "{seed}", "--noise", noise)
    run(labrun, "check", "--runs-dir", RUNS, "--batch", batch)
    logs = sorted((RUNS / batch).glob("seed-*.log"))
    means[batch] = [float(re.search(r"test_accuracy (\S+)", p.read_text()).group(1)) for p in logs]
    print(batch, means[batch])

step("2. Paper with a plot of those runs (first tectonic run downloads its bundle, and can take many minutes)")
run(lab_paper, "new", PAPER)
subprocess.run(["uv", "run", "--no-project", "--with", "matplotlib", "python", "-c", f"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.figure(figsize=(3.2, 2.2))
plt.scatter([0] * 3, {means['B1']}, label="no noise")
plt.scatter([1] * 3, {means['B2']}, label="20% noise")
plt.xticks([0, 1], ["clean", "noisy"]); plt.ylabel("test accuracy"); plt.legend(fontsize=6); plt.tight_layout()
plt.savefig("{PAPER}/figures/results.pdf")
"""], check=True, capture_output=True)
mean = {k: statistics.mean(v) for k, v in means.items()}
values = lambda b: ", ".join(f"{v:.4f}" for v in means[b])
tex = (PAPER / "main.tex").read_text()
for old, new in {
    "Paper Title": "Training-label noise on a toy classifier: a tool-chain demonstration",
    "Author names (students write this line)": "just demo-cpu",
    "One paragraph: the question, the method, the main result with its numbers.": "A tool-chain demonstration on synthetic data, not a research finding.",
    "The problem, the gap in prior work, and this paper's contributions.": "This script-filled paper exercises the tools.",
    "What is already known, synthesised across sources, and how this study differs.": "None: this is a demonstration.",
    "Describe the setup precisely enough to reproduce it.": "A softmax classifier on synthetic data, three seeds per condition.",
    "Report every condition with its spread, seed count and tests.":
        f"Test accuracy by seed without noise: {values('B1')}. With 20\\% label noise: {values('B2')}. "
        "\\begin{figure}[t]\\centering\\includegraphics[width=\\columnwidth]{figures/results.pdf}\\caption{Every seed of both conditions.}\\end{figure}",
    "What was found, and what should come next.": "The tools ran from seeded runs to a PDF.",
}.items():
    assert old in tex, old
    tex = tex.replace(old, new)
(PAPER / "main.tex").write_text(tex)
with (PAPER / "provenance.txt").open("a") as f:
    f.write("B1  no-noise condition\nB2  20% noise condition\n")
run(lab_paper, "build", PAPER)

step("3. Integrity check")
sources = OUT / "sources.jsonl"
bib = (PAPER / "refs.bib").read_text()
title = re.search(r"title\s*=\s*\{(.*?)\}", bib).group(1)
sources.write_text(json.dumps({"title": title, "abstract": ""}) + "\n")  # stands in for a lab-search result
run(integrity, "check", PAPER, "--runs-dir", RUNS, "--sources", sources)

step("4. Envelope: seal, fingerprint, wrong passphrase refused, right passphrase opens")
secret = OUT / "secret"
secret.mkdir()
(secret / "claims.md").write_text("C1: label noise lowers test accuracy on the toy task\nC2: a claim nobody tested\n")
enc = OUT / "sealed.enc"
run(envelope, "seal", secret, "--out", enc, "--passphrase-stdin", stdin="demo passphrase\n")
shutil.rmtree(secret)
bad = subprocess.run([str(envelope), "unseal", OUT / "x", "--in", enc, "--passphrase-stdin"], input="wrong\n", text=True, capture_output=True)
assert bad.returncode == 1, "a wrong passphrase must not open the envelope"
print("wrong passphrase refused")
run(envelope, "unseal", OUT / "opened", "--in", enc, "--passphrase-stdin", stdin="demo passphrase\n")

step("5. Scorecard")
verdict = "match" if mean["B2"] < mean["B1"] else "miss"
card = OUT / "scorecard.md"
card.write_text("| Claim | Paper says | We found | Batch | Verdict |\n|---|---|---|---|---|\n"
                f"| C1 | noise lowers accuracy | {mean['B1']:.4f} clean, {mean['B2']:.4f} noisy | B2 | {verdict} |\n"
                "| C2 | a claim nobody tested | - | - | not tested |\n")
run(envelope, "scorecard-check", card, "--claims", OUT / "opened/claims.md", "--runs-dir", RUNS)
print(card.read_text())
print(f"Done. PDF: {PAPER / 'main.pdf'}")
