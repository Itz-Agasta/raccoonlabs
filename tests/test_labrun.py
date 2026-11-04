"""Behaviour of the labrun CLI, driven as agents drive it: through the command line."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LABRUN = [sys.executable, str(ROOT / "tools/labrun/labrun.py")]


def run(tmp, *args):
    return subprocess.run([*LABRUN, *args[:1], "--runs-dir", str(tmp), *args[1:]], capture_output=True, text=True)


def execute(tmp, batch, *code_argv, seeds="0,1,2", extra=()):
    return run(tmp, "exec", "--batch", batch, "--seeds", seeds, "--approved-by", "alex: go", *extra, "--", sys.executable, *code_argv)


def manifest(tmp, batch):
    return json.loads((tmp / batch / "manifest.json").read_text())


def test_three_seeds_write_a_manifest(tmp_path):
    r = execute(tmp_path, "b1", "-c", "print('{seed}')")
    assert r.returncode == 0, r.stderr
    m = manifest(tmp_path, "b1")
    assert [s["seed"] for s in sorted(m["seeds"], key=lambda s: s["seed"])] == [0, 1, 2]
    assert all(s["exit_code"] == 0 and not s["timed_out"] for s in m["seeds"])
    assert m["approved_by"] == "alex: go"
    assert (tmp_path / "b1" / "seed-1.log").read_text().strip() == "1"


def test_check_passes_at_three_and_fails_at_two(tmp_path):
    execute(tmp_path, "three", "-c", "pass  # {seed}")
    execute(tmp_path, "two", "-c", "pass  # {seed}", seeds="0,1")
    assert run(tmp_path, "check", "--batch", "three").returncode == 0
    r = run(tmp_path, "check", "--batch", "two")
    assert r.returncode != 0
    assert "2 of 3" in r.stdout


def test_crashing_seed_is_recorded_and_check_fails(tmp_path):
    r = execute(tmp_path, "b", "-c", "import sys; sys.exit(3 if {seed} == 1 else 0)")
    assert r.returncode != 0
    by_seed = {s["seed"]: s for s in manifest(tmp_path, "b")["seeds"]}
    assert by_seed[1]["exit_code"] == 3
    assert by_seed[0]["exit_code"] == 0
    assert run(tmp_path, "check", "--batch", "b").returncode != 0


def test_timeout_is_recorded(tmp_path):
    r = execute(tmp_path, "b", "-c", "import time; time.sleep(30)  # {seed}", seeds="0", extra=("--timeout", "1"))
    assert r.returncode != 0
    assert manifest(tmp_path, "b")["seeds"][0]["timed_out"] is True


def test_existing_batch_is_refused(tmp_path):
    execute(tmp_path, "b", "-c", "print('first {seed}')")
    before = (tmp_path / "b" / "manifest.json").read_text()
    r = execute(tmp_path, "b", "-c", "print('second {seed}')")
    assert r.returncode != 0
    assert "already exists" in r.stderr
    assert (tmp_path / "b" / "manifest.json").read_text() == before


def test_command_without_seed_placeholder_is_refused(tmp_path):
    r = execute(tmp_path, "b", "-c", "pass")
    assert r.returncode != 0
    assert "{seed}" in r.stderr
    assert not (tmp_path / "b").exists()


def test_blank_approval_is_refused(tmp_path):
    r = run(tmp_path, "exec", "--batch", "b", "--seeds", "0", "--approved-by", "  ", "--", sys.executable, "-c", "pass # {seed}")
    assert r.returncode != 0
    assert "approved-by" in r.stderr
    assert not (tmp_path / "b").exists()


def test_seed_is_substituted_as_one_argument(tmp_path):
    execute(tmp_path, "b", "-c", "import sys; print(sys.argv[1:])", "a b {seed}; echo hacked", seeds="4")
    assert (tmp_path / "b" / "seed-4.log").read_text().strip() == "['a b 4; echo hacked']"


def test_check_on_missing_batch_fails(tmp_path):
    r = run(tmp_path, "check", "--batch", "nope")
    assert r.returncode != 0
    assert "no batch" in r.stderr


def test_show_prints_the_manifest(tmp_path):
    execute(tmp_path, "b", "-c", "pass  # {seed}", seeds="0")
    r = run(tmp_path, "show", "--batch", "b")
    assert json.loads(r.stdout)["batch"] == "b"


def test_each_seed_records_when_it_ran(tmp_path):
    execute(tmp_path, "b", "-c", "pass  # {seed}", seeds="0,1")
    m = manifest(tmp_path, "b")
    assert m["finished_at"] >= m["started_at"]
    for s in m["seeds"]:
        assert m["started_at"] <= s["started_at"] <= s["finished_at"] <= m["finished_at"]


def test_seed_entries_are_in_seed_order_after_parallel_runs(tmp_path):
    execute(tmp_path, "b", "-c", "import time; time.sleep(0.3 if {seed} == 0 else 0)", seeds="0,1,2", extra=("--jobs", "3"))
    assert [s["seed"] for s in manifest(tmp_path, "b")["seeds"]] == [0, 1, 2]


def test_check_says_it_only_covers_clean_exits(tmp_path):
    execute(tmp_path, "b", "-c", "pass  # {seed}")
    assert "clean exits only" in run(tmp_path, "check", "--batch", "b").stdout
