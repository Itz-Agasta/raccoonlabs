#!/usr/bin/env python3
"""Run a command across seeds and keep evidence a reviewer can check.

  labrun exec --batch B1 --seeds 0,1,2 --approved-by "alex: go ahead" -- python exp.py --seed {seed}
  labrun check --batch B1 [--min-seeds 3]
  labrun show --batch B1

Each batch writes <runs>/<batch>/manifest.json and one seed-<n>.log per seed.
labrun refuses to overwrite a batch and marks finished files read-only. That
guards against accidents, not against someone deleting files: anchor a batch by
posting the sha256 it prints.
"""
import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_RUNS = Path.home() / ".local/share/raccoonlabs/runs"
running = set()


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_manifest(path, manifest):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(manifest, indent=2) + "\n")
    os.replace(tmp, path)


def kill_group(pid):
    try:
        os.killpg(pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def run_seed(seed, command, log, timeout):
    argv = [part.replace("{seed}", str(seed)) for part in command]
    started_at = now()
    start = time.monotonic()
    exit_code, timed_out = None, False
    with log.open("w") as out:
        try:
            # Its own process group, so wrappers like `uv run` can't leave a seed behind.
            proc = subprocess.Popen(argv, stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
            running.add(proc.pid)
            try:
                exit_code = proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                kill_group(proc.pid)
                proc.wait()
            finally:
                kill_group(proc.pid)
                running.discard(proc.pid)
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
        "seeds_requested": seeds,
        "seeds": [],
    }
    path = batch_dir / "manifest.json"
    write_manifest(path, manifest)
    lock = threading.Lock()

    def interrupted(signum, frame):
        for pid in list(running):
            kill_group(pid)
        with lock:
            manifest["interrupted"] = True
            write_manifest(path, manifest)
        os._exit(128 + signum)

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)

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
    for item in batch_dir.iterdir():
        item.chmod(0o444)
    good = sum(e["exit_code"] == 0 for e in entries)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    print(f"batch {args.batch}: {good} of {len(entries)} seeds succeeded; manifest at {path}; sha256 {digest}")
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
    if "seeds_requested" not in manifest:
        print(f"batch {args.batch}: FAIL: predates requested-seed tracking, so missing seeds can't be ruled out")
        return 1
    requested = len(manifest["seeds_requested"])
    failed = len(manifest["seeds"]) - good
    missing = requested - len(manifest["seeds"])
    problems = []
    if manifest.get("interrupted"):
        problems.append("batch was interrupted")
    elif "finished_at" not in manifest:
        problems.append("batch has not finished")
    if failed or missing:
        problems.append("not every requested seed succeeded")
    if good < args.min_seeds:
        problems.append("below the minimum")
    print(
        f"batch {args.batch}: {good} of {requested} requested seeds exited cleanly; {failed} failed; "
        f"{missing} missing; minimum {args.min_seeds}: {'FAIL: ' + '; '.join(problems) if problems else 'PASS'} "
        "(clean exits only; compare the logs against any claimed result)"
    )
    return 1 if problems else 0


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
