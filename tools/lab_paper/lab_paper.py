#!/usr/bin/env python3
"""Start and compile the lab's paper.

  lab-paper new DIR     copy the template into DIR
  lab-paper build DIR   compile DIR/main.tex to DIR/main.pdf with tectonic

A build fails on LaTeX errors, undefined citations and undefined references, so
a PDF that exists has resolved every one of them.
"""
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent / "template"
PROBLEMS = re.compile(r"(?:Citation|Reference) [`'](\S+?)' (?:on page \d+ )?undefined")


def cmd_new(args):
    target = Path(args.dir)
    if target.exists() and any(target.iterdir()):
        print(f"lab-paper: {target} already has files; nothing was changed", file=sys.stderr)
        return 2
    shutil.copytree(TEMPLATE, target, dirs_exist_ok=True)
    print(f"template copied to {target}")
    return 0


def cmd_build(args):
    target = Path(args.dir)
    if not (target / "main.tex").exists():
        print(f"lab-paper: no main.tex in {target}", file=sys.stderr)
        return 2
    pdf = target / "main.pdf"
    pdf.unlink(missing_ok=True)
    r = subprocess.run(["tectonic", "--keep-logs", "--keep-intermediates", "main.tex"], cwd=target, capture_output=True, text=True)
    log = target / "main.log"
    text = (log.read_text(errors="ignore") if log.exists() else "") + r.stderr
    missing = sorted(set(PROBLEMS.findall(text)))
    if r.returncode != 0 or missing or not pdf.exists():
        pdf.unlink(missing_ok=True)
        if missing:
            print(f"lab-paper: undefined citations or references: {', '.join(missing)}", file=sys.stderr)
        if r.returncode != 0:
            print("\n".join(r.stderr.splitlines()[-15:]), file=sys.stderr)
        return 1
    print(f"built {pdf}")
    return 0


def main(argv):
    p = argparse.ArgumentParser(prog="lab-paper", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="action", required=True)
    for name, func in (("new", cmd_new), ("build", cmd_build)):
        s = sub.add_parser(name)
        s.add_argument("dir")
        s.set_defaults(func=func)
    args = p.parse_args(argv)
    return args.func(args)


def main_cli():
    return main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main_cli())
