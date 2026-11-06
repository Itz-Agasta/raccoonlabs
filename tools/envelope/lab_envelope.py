#!/usr/bin/env python3
"""Seal a file or folder with a passphrase, open it at the end, and check the scorecard.

  lab-envelope seal SRC [--out FILE]        encrypt SRC (asks for the passphrase)
  lab-envelope fingerprint [FILE]           print the sha256 to post before a run
  lab-envelope unseal OUTDIR [--in FILE] [--passphrase-stdin]
  lab-envelope scorecard-check SCORECARD --claims CLAIMS [--runs-dir DIR]

Claims file: one claim per line, as `C1: what the paper claims`.
Scorecard: a markdown table, one row per claim, with the claim ID in the first
cell, the batch ID in the second last and the verdict in the last.
Verdicts: match, partial, miss, not tested. Only `not tested` may lack a batch.
"""
import argparse
import getpass
import hashlib
import io
import os
import re
import subprocess
import sys
import tarfile
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

DEFAULT = Path(__file__).resolve().parents[2] / "envelope/sealed.enc"
MAGIC = b"RACCOON1"
VERDICTS = {"match", "partial", "miss", "not tested"}


def key_from(passphrase, salt):
    return Scrypt(salt=salt, length=32, n=2**15, r=8, p=1).derive(passphrase.encode())


def seal_bytes(data, passphrase):
    salt, nonce = os.urandom(16), os.urandom(12)
    return MAGIC + salt + nonce + AESGCM(key_from(passphrase, salt)).encrypt(nonce, data, MAGIC)


def unseal_bytes(blob, passphrase):
    if not blob.startswith(MAGIC):
        raise ValueError("not a sealed envelope")
    salt, nonce, body = blob[8:24], blob[24:36], blob[36:]
    return AESGCM(key_from(passphrase, salt)).decrypt(nonce, body, MAGIC)


def fail(message):
    print(f"lab-envelope: {message}", file=sys.stderr)
    return 1


def fingerprint(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def cmd_seal(args):
    src = Path(args.src)
    if not src.exists():
        return fail(f"{src} doesn't exist")
    passphrase = sys.stdin.readline().rstrip("\n") if args.passphrase_stdin else getpass.getpass("Passphrase: ")
    if not args.passphrase_stdin and passphrase != getpass.getpass("Again: "):
        return fail("the passphrases differ; nothing was sealed")
    if not passphrase:
        return fail("an empty passphrase isn't allowed")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add(src, arcname=".")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(seal_bytes(buf.getvalue(), passphrase))
    print(f"sealed {out}\nsha256 {fingerprint(out)}")
    return 0


def cmd_fingerprint(args):
    print(fingerprint(args.file))
    return 0


def cmd_unseal(args):
    passphrase = sys.stdin.readline().rstrip("\n") if args.passphrase_stdin else getpass.getpass("Passphrase: ")
    try:
        data = unseal_bytes(Path(args.file).read_bytes(), passphrase)
    except OSError as e:
        return fail(f"can't read the envelope: {e}")
    except ValueError as e:
        return fail(str(e))
    except InvalidTag:
        return fail("wrong passphrase, or the envelope was changed; nothing was opened")
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        tar.extractall(out, filter="data")
    print(f"sha256 {fingerprint(args.file)}\nopened into {out}")
    for path in sorted(p for p in out.rglob("*") if p.is_file()):
        print(path)
    return 0


def rows(text):
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.lstrip().startswith("|") and re.fullmatch(r"C\d+", cells[0]):
            yield cells


def cmd_scorecard_check(args):
    claims = re.findall(r"^(C\d+):", Path(args.claims).read_text(), re.M)
    if not claims:
        return fail(f"no claims found in {args.claims}")
    found = {r[0]: r for r in rows(Path(args.scorecard).read_text())}
    problems = [f"{c}: no row" for c in claims if c not in found]
    problems += [f"{c}: not in the claims file" for c in found if c not in claims]
    for claim, cells in found.items():
        batch, verdict = cells[-2], cells[-1].lower()
        if verdict not in VERDICTS:
            problems.append(f"{claim}: unknown verdict {cells[-1]!r}")
        elif verdict != "not tested":
            cmd = ["labrun", "check", "--batch", batch]
            if args.runs_dir:
                cmd += ["--runs-dir", args.runs_dir]
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode != 0:
                problems.append(f"{claim}: batch {batch!r} fails labrun check: {(r.stdout + r.stderr).strip()}")
    for p in problems:
        print(f"FAIL {p}")
    print(f"scorecard: {len(found)} rows, {len(claims)} claims, {len(problems)} problems")
    return 1 if problems else 0


def main(argv):
    p = argparse.ArgumentParser(prog="lab-envelope", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="action", required=True)
    s = sub.add_parser("seal")
    s.add_argument("src")
    s.add_argument("--out", default=DEFAULT)
    s.add_argument("--passphrase-stdin", action="store_true")
    s.set_defaults(func=cmd_seal)
    f = sub.add_parser("fingerprint")
    f.add_argument("file", nargs="?", default=DEFAULT)
    f.set_defaults(func=cmd_fingerprint)
    u = sub.add_parser("unseal")
    u.add_argument("outdir")
    u.add_argument("--in", dest="file", default=DEFAULT)
    u.add_argument("--passphrase-stdin", action="store_true")
    u.set_defaults(func=cmd_unseal)
    c = sub.add_parser("scorecard-check")
    c.add_argument("scorecard")
    c.add_argument("--claims", required=True)
    c.add_argument("--runs-dir")
    c.set_defaults(func=cmd_scorecard_check)
    args = p.parse_args(argv)
    return args.func(args)


def main_cli():
    return main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main_cli())
