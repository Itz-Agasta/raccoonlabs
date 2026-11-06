#!/usr/bin/env python3
"""Check a paper before the professor sees it.

  lab-integrity check PAPER_DIR [--runs-dir DIR] [--sources FILE]

FAIL stops the draft: a cited source lab-search never returned, a batch ID that
fails `labrun check`, a results section naming no batch, a missing or unedited
disclosure, or a template placeholder left in.
FLAG needs a person to look: a results number found in no log of the named
batches (it may be a fair average), or text overlapping a collected source.
This is an integrity check, not plagiarism detection.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_RUNS = Path.home() / ".local/share/raccoonlabs/runs"
DEFAULT_SOURCES = Path.home() / ".local/share/raccoonlabs/sources.jsonl"
BATCH_WORD = re.compile(r"\b[A-Z][A-Za-z_-]*\d+[A-Za-z0-9_-]*\b")
NAMED_BATCH = re.compile(r"\bbatch(?:es)?\s+\\?(?:texttt\{)?([A-Za-z][\w-]*\d[\w-]*)", re.I)
NUMBER = re.compile(r"(?<![\w.])\d+(?:\.\d+)?(?![\w])")
PLACEHOLDERS = ("Paper Title", "One paragraph: the question", "State which sections the students wrote", "Author names (students write this line)")
SHINGLE = 8


def normalise(text):
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def words(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def strip_comments(tex):
    return re.sub(r"(?<!\\)%.*", "", tex)


def section(tex, name):
    found = re.search(r"\\section\*?\{" + re.escape(name) + r"\}(.*?)(?=\\section\*?\{|\\bibliography|\\end\{document\})", tex, re.S | re.I)
    return found.group(1) if found else ""


def bib_entries(text):
    out = {}
    for m in re.finditer(r"@\w+\s*\{\s*([^,\s]+)\s*,(.*?)(?=\n@|\Z)", text, re.S):
        fields = {k.lower(): " ".join(v.split()) for k, v in re.findall(r"(\w+)\s*=\s*[{\"](.*?)[}\"]\s*,?\s*(?:\n|$)", m.group(2), re.S)}
        out[m.group(1)] = fields
    return out


def load_sources(path):
    if not Path(path).exists():
        return []
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def check_citations(tex, bib, sources):
    keys = {k.strip() for group in re.findall(r"\\(?:no)?cite\w*\{([^}]*)\}", tex) for k in group.split(",")}
    known = {(s.get("arxiv") or "").lower() for s in sources} | {(s.get("doi") or "").lower() for s in sources}
    known.discard("")
    titles = {normalise(s.get("title", "")) for s in sources}
    problems = []
    for key in sorted(keys):
        entry = bib.get(key)
        if entry is None:
            problems.append(f"\\cite{{{key}}} has no entry in refs.bib")
            continue
        ids = {entry.get("eprint", "").lower(), entry.get("doi", "").lower()} - {""}
        if not ids & known and normalise(entry.get("title", "")) not in titles:
            problems.append(f"{key}: lab-search never returned this source")
    return keys, problems


def run_numbers(batch, runs_dir):
    folder = Path(runs_dir) / batch
    text = "".join(p.read_text(errors="ignore") + "\n" for p in folder.glob("seed-*.log"))
    manifest = json.loads((folder / "manifest.json").read_text())
    numbers = {float(n) for n in NUMBER.findall(text)}
    numbers |= {float(len(manifest["seeds_requested"]))} | {float(s) for s in manifest["seeds_requested"]}
    return numbers


def check_results(tex, runs_dir):
    results = section(tex, "Results")
    # A batch is any word the text calls a batch, or any ID-shaped word with a folder in the runs directory.
    batches = sorted(set(NAMED_BATCH.findall(results)) | {w for w in BATCH_WORD.findall(results) if (Path(runs_dir) / w / "manifest.json").exists()})
    fails, flags = [], []
    if not batches:
        return batches, ["the Results section names no batch ID"], flags
    logged = set()
    for batch in batches:
        r = subprocess.run(["labrun", "check", "--batch", batch, "--runs-dir", str(runs_dir)], capture_output=True, text=True)
        if r.returncode != 0:
            fails.append(f"batch {batch}: {(r.stdout + r.stderr).strip()}")
            continue
        logged |= run_numbers(batch, runs_dir)
    plain = re.sub(r"\\(?:ref|label|cite\w*|includegraphics|input)(?:\[[^\]]*\])?\{[^}]*\}", " ", re.sub("|".join(map(re.escape, batches)), " ", results))
    plain = re.sub(r"\\begin\{\w+\}(?:\[[^\]]*\])?|\\end\{\w+\}", " ", plain)
    for n in sorted(set(NUMBER.findall(plain)), key=float):
        tolerance = 0.5 * 10 ** -len(n.partition(".")[2])
        if not any(abs(float(n) - value) <= tolerance for value in logged):
            flags.append(f"number {n} in Results isn't in the logs of {', '.join(batches)}: confirm it's derived fairly")
    return batches, fails, flags


def check_overlap(tex, sources):
    body = words(re.sub(r"\\[a-zA-Z]+\*?", " ", tex))
    mine = {" ".join(body[i:i + SHINGLE]) for i in range(len(body) - SHINGLE + 1)}
    flags = []
    seen = set()
    for s in sources:
        name = s.get("title", "untitled")
        if name in seen:
            continue
        seen.add(name)
        theirs = words(s.get("abstract", ""))
        shared = sum(" ".join(theirs[i:i + SHINGLE]) in mine for i in range(len(theirs) - SHINGLE + 1))
        if shared:
            flags.append(f"{shared} {SHINGLE}-word runs overlap the abstract of {name!r}: quote and cite, or reword")
    return flags


def cmd_check(args):
    paper = Path(args.paper_dir)
    if not (paper / "main.tex").exists():
        print(f"lab-integrity: no main.tex in {paper}", file=sys.stderr)
        return 2
    tex = strip_comments((paper / "main.tex").read_text())
    bib_path = paper / "refs.bib"
    bib = bib_entries(bib_path.read_text()) if bib_path.exists() else {}
    sources = load_sources(args.sources)
    keys, fails = check_citations(tex, bib, sources)
    batches, more, flags = check_results(tex, args.runs_dir)
    fails += more
    flags += check_overlap(tex, sources)
    disclosure = section(tex, "AI use disclosure")
    if not disclosure.strip():
        fails.append("no AI use disclosure")
    if not keys:
        flags.append("the paper cites nothing")
    fails += [f"template text left in: {p!r}" for p in PLACEHOLDERS if p in tex]
    print(f"citations checked: {len(keys)}; batches named: {', '.join(batches) or 'none'}; sources on file: {len(sources)}")
    for f in fails:
        print(f"FAIL {f}")
    for f in flags:
        print(f"FLAG {f}")
    print(f"integrity: {'FAIL' if fails else 'PASS'} ({len(fails)} failures, {len(flags)} flags)")
    return 1 if fails else 0


def main(argv):
    p = argparse.ArgumentParser(prog="lab-integrity", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="action", required=True)
    c = sub.add_parser("check")
    c.add_argument("paper_dir")
    c.add_argument("--runs-dir", default=DEFAULT_RUNS)
    c.add_argument("--sources", default=DEFAULT_SOURCES)
    c.set_defaults(func=cmd_check)
    args = p.parse_args(argv)
    return args.func(args)


def main_cli():
    return main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main_cli())
