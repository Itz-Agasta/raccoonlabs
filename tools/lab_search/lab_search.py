#!/usr/bin/env python3
"""Look up literature for the lab, with the envelope blocklist applied.

  lab-search search "query" [--limit 5] [--source all|arxiv|crossref|s2]
  lab-search read 2401.00001
  lab-search fulltext 2401.00001    print the paper's text, needs pdftotext

Sealed items are withheld and every query is logged. The blocklist holds only
hashes, so reading it doesn't reveal what's sealed.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

BLOCKLIST = Path(__file__).resolve().parents[2] / "envelope/blocklist.sha256"
LOG = Path.home() / ".local/share/raccoonlabs/lab-search.jsonl"
SOURCES_LOG = Path.home() / ".local/share/raccoonlabs/sources.jsonl"
ATOM = {"a": "http://www.w3.org/2005/Atom"}
ARXIV_ID = re.compile(r"\b(\d{4}\.\d{4,5})(?:v\d+)?\b")
REFUSED = 3


def normalise(text):
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def digest(text):
    return hashlib.sha256(normalise(text).encode()).hexdigest()


def load_blocklist():
    return {line.strip() for line in BLOCKLIST.read_text().splitlines() if line.strip()}


def is_sealed(blocked, *texts):
    for text in texts:
        if not text:
            continue
        if digest(text) in blocked or digest(text.split(":")[0]) in blocked or any(digest(i) in blocked for i in ARXIV_ID.findall(text)):
            return True
    return False


def http_get(url):
    return http_bytes(url).decode()


def http_bytes(url):
    req = urllib.request.Request(url, headers={"User-Agent": "raccoonlabs-lab-search/0.1"})
    for attempt in (1, 2):
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                return r.read()
        except OSError:
            if attempt == 2:
                raise
            time.sleep(4)


def paper(title, authors, year, source, ident, abstract="", doi="", arxiv=""):
    return dict(title=" ".join(title.split()), authors=authors, year=year, source=source, id=ident,
                abstract=" ".join(abstract.split()), doi=doi, arxiv=arxiv)


def parse_arxiv(xml):
    out = []
    for e in ET.fromstring(xml).findall("a:entry", ATOM):
        link = e.findtext("a:id", "", ATOM)
        found = ARXIV_ID.search(link)
        if not found:
            continue
        out.append(paper(e.findtext("a:title", "", ATOM), [a.findtext("a:name", "", ATOM) for a in e.findall("a:author", ATOM)],
                         e.findtext("a:published", "", ATOM)[:4], "arxiv", found.group(1),
                         e.findtext("a:summary", "", ATOM), arxiv=found.group(1)))
    return out


def search_arxiv(query, limit):
    words = " AND ".join(f"all:{w}" for w in query.split())
    q = urllib.parse.urlencode({"search_query": words, "max_results": limit})
    return parse_arxiv(http_get(f"https://export.arxiv.org/api/query?{q}"))


def search_crossref(query, limit):
    q = urllib.parse.urlencode({"query.bibliographic": query, "rows": limit})
    out = []
    for w in json.loads(http_get(f"https://api.crossref.org/works?{q}"))["message"]["items"]:
        authors = [" ".join(filter(None, [a.get("given"), a.get("family")])) for a in w.get("author", [])]
        year = str(((w.get("issued", {}).get("date-parts") or [[""]])[0] or [""])[0] or "")
        title = (w.get("title") or [""])[0]
        if not title or not w.get("DOI"):
            continue  # Crossref has records with no title or date; skip those rather than lose the query
        out.append(paper(title, authors, year, "crossref", w["DOI"], re.sub(r"<[^>]+>", " ", w.get("abstract") or ""), doi=w["DOI"]))
    return out


def search_s2(query, limit):
    q = urllib.parse.urlencode({"query": query, "limit": limit, "fields": "title,authors,year,abstract,externalIds"})
    out = []
    for w in json.loads(http_get(f"https://api.semanticscholar.org/graph/v1/paper/search?{q}")).get("data") or []:
        ids = w.get("externalIds") or {}
        out.append(paper(w.get("title") or "", [a.get("name", "") for a in w.get("authors") or []], str(w.get("year") or ""), "s2",
                         w.get("paperId", ""), w.get("abstract") or "", doi=ids.get("DOI", ""), arxiv=ids.get("ArXiv", "")))
    return out


SOURCES = {"arxiv": search_arxiv, "crossref": search_crossref, "s2": search_s2}


def bibtex(p):
    first = (p["authors"] or ["unknown"])[0].split()[-1].lower()
    word = next((w for w in re.findall(r"[a-z]+", p["title"].lower()) if len(w) > 3), "paper")
    lines = [f"@misc{{{re.sub(r'[^a-z0-9]', '', first)}{p['year']}{word},", f"  title = {{{p['title']}}},",
             f"  author = {{{' and '.join(p['authors']) or 'Unknown'}}},", f"  year = {{{p['year']}}},"]
    if p["arxiv"]:
        lines += [f"  eprint = {{{p['arxiv']}}},", "  archivePrefix = {arXiv},"]
    if p["doi"]:
        lines.append(f"  doi = {{{p['doi']}}},")
    return "\n".join(lines) + "\n}"


def log(query, source, refused=False, results=0, withheld=0, errors=()):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(json.dumps(dict(at=datetime.now(timezone.utc).isoformat(timespec="seconds"), query=query, source=source,
                                refused=refused, results=results, withheld=withheld, errors=list(errors))) + "\n")


def remember(papers):
    """Keep what was returned, so lab-integrity can check citations and overlap offline."""
    if not papers:
        return
    SOURCES_LOG.parent.mkdir(parents=True, exist_ok=True)
    with SOURCES_LOG.open("a") as f:
        for p in papers:
            f.write(json.dumps({k: p[k] for k in ("title", "year", "id", "doi", "arxiv", "abstract")}) + "\n")


def show(p):
    print(f"## {p['title']}\n{', '.join(p['authors'][:6]) or 'Unknown authors'} ({p['year']}), {p['source']}: {p['id']}")
    if p["abstract"]:
        print(p["abstract"])
    print(bibtex(p) + "\n")


def cmd_search(args, blocked):
    if is_sealed(blocked, args.query):
        log(args.query, args.source, refused=True)
        print("lab-search: query refused by the envelope blocklist", file=sys.stderr)
        return REFUSED
    names = list(SOURCES) if args.source == "all" else [args.source]
    results, errors = [], []
    for name in names:
        try:
            results += SOURCES[name](args.query, args.limit)
        except (OSError, ValueError, KeyError, ET.ParseError) as e:
            errors.append(f"{name} failed: {e}")
    visible = [p for p in results if not is_sealed(blocked, p["title"], p["arxiv"], p["id"], p["doi"])]
    withheld = len(results) - len(visible)
    log(args.query, args.source, results=len(visible), withheld=withheld, errors=errors)
    remember(visible)
    for p in visible:
        show(p)
    print(f"results: {len(visible)}, withheld: {withheld}")
    for e in errors:
        print(e)
    return 1 if len(errors) == len(names) else 0


def cmd_read(args, blocked):
    if is_sealed(blocked, args.arxiv_id):
        log(f"read {args.arxiv_id}", "arxiv", refused=True)
        print("lab-search: refused by the envelope blocklist", file=sys.stderr)
        return REFUSED
    bare = ARXIV_ID.sub(r"\1", args.arxiv_id)
    try:
        found = parse_arxiv(http_get(f"https://export.arxiv.org/api/query?id_list={urllib.parse.quote(bare)}"))
    except (OSError, ET.ParseError) as e:
        log(f"read {args.arxiv_id}", "arxiv", errors=[str(e)])
        print(f"lab-search: arxiv failed: {e}", file=sys.stderr)
        return 1
    match = [p for p in found if p["arxiv"] == bare and not is_sealed(blocked, p["title"], p["arxiv"])]
    log(f"read {args.arxiv_id}", "arxiv", results=len(match))
    if not match:
        print(f"lab-search: nothing found for {bare}", file=sys.stderr)
        return 1
    remember(match)
    show(match[0])
    return 0


def cmd_fulltext(args, blocked):
    # Sealed items are refused by ID here, and by title after the lookup, before any download.
    if is_sealed(blocked, args.arxiv_id):
        log(f"fulltext {args.arxiv_id}", "arxiv", refused=True)
        print("lab-search: refused by the envelope blocklist", file=sys.stderr)
        return REFUSED
    bare = ARXIV_ID.sub(r"\1", args.arxiv_id)
    try:
        found = parse_arxiv(http_get(f"https://export.arxiv.org/api/query?id_list={urllib.parse.quote(bare)}"))
        match = [p for p in found if p["arxiv"] == bare and not is_sealed(blocked, p["title"], p["arxiv"])]
        if not match:
            log(f"fulltext {args.arxiv_id}", "arxiv")
            print(f"lab-search: nothing found for {bare}", file=sys.stderr)
            return 1
        pdf = http_bytes(f"https://arxiv.org/pdf/{urllib.parse.quote(bare)}")
    except (OSError, ET.ParseError) as e:
        log(f"fulltext {args.arxiv_id}", "arxiv", errors=[str(e)])
        print(f"lab-search: arxiv failed: {e}", file=sys.stderr)
        return 1
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(pdf)
        f.flush()
        r = subprocess.run(["pdftotext", "-layout", f.name, "-"], capture_output=True, text=True)
    log(f"fulltext {args.arxiv_id}", "arxiv", results=1 if r.returncode == 0 else 0)
    if r.returncode != 0:
        print(f"lab-search: can't read that PDF: {r.stderr.strip()}", file=sys.stderr)
        return 1
    remember(match)
    show(match[0])
    print(r.stdout)
    return 0


def main(argv):
    p = argparse.ArgumentParser(prog="lab-search", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="action", required=True)
    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=5)
    s.add_argument("--source", choices=["all", *SOURCES], default="all")
    s.set_defaults(func=cmd_search)
    r = sub.add_parser("read")
    r.add_argument("arxiv_id")
    r.set_defaults(func=cmd_read)
    t = sub.add_parser("fulltext")
    t.add_argument("arxiv_id")
    t.set_defaults(func=cmd_fulltext)
    args = p.parse_args(argv)
    try:
        blocked = load_blocklist()
    except OSError as e:
        print(f"lab-search: can't read the blocklist, refusing to search: {e}", file=sys.stderr)
        return 1
    return args.func(args, blocked)


def main_cli():
    return main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main_cli())
