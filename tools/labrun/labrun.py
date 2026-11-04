#!/usr/bin/env python3
"""Run a command across seeds and keep evidence a reviewer can check.

  labrun exec --batch B1 --seeds 0,1,2 --approved-by "alex: go ahead" -- python exp.py --seed {seed}
  labrun check --batch B1 [--min-seeds 3]
  labrun show --batch B1

Each batch writes <runs>/<batch>/manifest.json and one seed-<n>.log per seed.
Batches are never overwritten, so evidence can't be silently replaced.
"""
import argparse
import json
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_RUNS = Path.home() / ".local/share/raccoonlabs/runs"


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_manifest(path, manifest):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(manifest, indent=2) + "\n")
    os.replace(tmp, path)


def run_seed(seed, command, log, timeout):
    argv = [part.replace("{seed}", str(seed)) for part in command]
    started_at = now()
    start = time.monotonic()
    exit_code, timed_out = None, False
    with log.open("w") as out:
        try:
            exit_code = subprocess.run(argv, stdout=out, stderr=subprocess.STDOUT, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            timed_out = True
        except OSError as e:
            out.write(f"labrun: could not start command: {e}\n")
            exit_code = 127
    return {
        "seed": seed,
        "exit_code": exit_code,
        "seconds": round(time.monotonic() - start, 2),
        "started_at": started_at,
        "finished_at": now(),
        "log": str(log),
        "timed_out": timed_out,
    }


def cmd_exec(args):
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not args.approved_by.strip():
        return fail("--approved-by must name the person and their approval message")
    if not any("{seed}" in part for part in command):
        return fail("the command must contain {seed}")
    try:
        seeds = [int(s) for s in args.seeds.split(",")]
    except ValueError:
        return fail(f"--seeds must be comma-separated integers, got {args.seeds!r}")
    if len(set(seeds)) != len(seeds):
        return fail(f"--seeds has duplicates: {args.seeds}")

    batch_dir = args.runs_dir / args.batch
    try:
        batch_dir.mkdir(parents=True)
    except FileExistsError:
        return fail(f"batch {args.batch} already exists at {batch_dir}; use a new batch ID")

    manifest = {
        "batch": args.batch,
        "command": command,
        "approved_by": args.approved_by,
        "started_at": now(),
        "seeds": [],
    }
    path = batch_dir / "manifest.json"
    write_manifest(path, manifest)
    lock = threading.Lock()

    def work(seed):
        entry = run_seed(seed, command, batch_dir / f"seed-{seed}.log", args.timeout)
        with lock:
            manifest["seeds"].append(entry)
            manifest["seeds"].sort(key=lambda s: s["seed"])
            write_manifest(path, manifest)
        return entry

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        entries = list(pool.map(work, seeds))
    manifest["finished_at"] = now()
    write_manifest(path, manifest)
    good = sum(e["exit_code"] == 0 for e in entries)
    print(f"batch {args.batch}: {good} of {len(entries)} seeds succeeded; manifest at {path}")
    return 0 if good == len(entries) else 1


def load(args):
    path = args.runs_dir / args.batch / "manifest.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def cmd_check(args):
    manifest = load(args)
    if manifest is None:
        return fail(f"no batch named {args.batch} in {args.runs_dir}")
    good = sum(s["exit_code"] == 0 for s in manifest["seeds"])
    enough = good >= args.min_seeds
    print(
        f"batch {args.batch}: {good} of {args.min_seeds} required seeds succeeded: {'PASS' if enough else 'FAIL'} "
        "(clean exits only; compare the logs against any claimed result)"
    )
    return 0 if enough else 1


def cmd_show(args):
    manifest = load(args)
    if manifest is None:
        return fail(f"no batch named {args.batch} in {args.runs_dir}")
    print(json.dumps(manifest, indent=2))
    return 0


def fail(message):
    print(f"labrun: {message}", file=sys.stderr)
    return 2


def parser():
    p = argparse.ArgumentParser(prog="labrun", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="action", required=True)

    def add(name, func):
        s = sub.add_parser(name)
        s.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS)
        s.add_argument("--batch", required=True)
        s.set_defaults(func=func)
        return s

    e = add("exec", cmd_exec)
    e.add_argument("--seeds", required=True)
    e.add_argument("--approved-by", required=True)
    e.add_argument("--jobs", type=int, default=2)
    e.add_argument("--timeout", type=float, default=1800)
    e.add_argument("command", nargs=argparse.REMAINDER)

    c = add("check", cmd_check)
    c.add_argument("--min-seeds", type=int, default=3)

    add("show", cmd_show)
    return p


def main():
    args = parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
