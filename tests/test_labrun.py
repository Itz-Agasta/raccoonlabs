"""Behaviour of the labrun CLI, driven as agents drive it: through the command line."""
import json
import os
import stat
import subprocess
import sys
import time
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
    assert "minimum 3" in r.stdout


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


def wait_for(condition, seconds=10):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if condition():
            return True
        time.sleep(0.05)
    return False


def test_check_fails_when_seeds_crash_even_above_the_minimum(tmp_path):
    execute(tmp_path, "b", "-c", "import sys; sys.exit(7 if {seed} in (3, 4) else 0)", seeds="0,1,2,3,4")
    r = run(tmp_path, "check", "--batch", "b")
    assert r.returncode != 0
    assert "3 of 5" in r.stdout and "2 failed" in r.stdout


def start_batch(tmp_path, batch, code, seeds):
    return subprocess.Popen(
        [*LABRUN, "exec", "--runs-dir", str(tmp_path), "--batch", batch, "--seeds", seeds, "--approved-by", "alex: go", "--jobs", "1", "--", sys.executable, "-c", code],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def test_check_fails_while_a_batch_is_running(tmp_path):
    p = start_batch(tmp_path, "b", "import time; time.sleep(0.2 if {seed} < 3 else 8)", "0,1,2,3")
    try:
        assert wait_for(lambda: (tmp_path / "b/manifest.json").exists() and len(manifest(tmp_path, "b")["seeds"]) == 3)
        r = run(tmp_path, "check", "--batch", "b")
        assert r.returncode != 0
        assert "not finished" in r.stdout
    finally:
        p.terminate()
        p.wait()


def test_killed_batch_fails_check_and_leaves_no_children(tmp_path):
    marker = tmp_path / "late"
    code = f"import time; time.sleep(0 if {{seed}} == 0 else 2); open({str(marker)!r}, 'w').write('x')"
    p = start_batch(tmp_path, "b", code, "0,1")
    assert wait_for(lambda: (tmp_path / "b/manifest.json").exists() and len(manifest(tmp_path, "b")["seeds"]) == 1)
    marker.unlink()
    time.sleep(0.2)
    p.terminate()
    p.wait()
    assert manifest(tmp_path, "b")["interrupted"] is True
    r = run(tmp_path, "check", "--batch", "b")
    assert r.returncode != 0 and "interrupted" in r.stdout
    time.sleep(2.5)
    assert not marker.exists()


def test_timeout_also_stops_grandchildren(tmp_path):
    marker = tmp_path / "late"
    child = f"import time; time.sleep(2); open({str(marker)!r}, 'w').write('x')"
    code = f"import subprocess, sys; subprocess.run([sys.executable, '-c', {child!r}])  # {{seed}}"
    r = execute(tmp_path, "b", "-c", code, seeds="0", extra=("--timeout", "1"))
    assert r.returncode != 0
    assert manifest(tmp_path, "b")["seeds"][0]["timed_out"] is True
    time.sleep(2.5)
    assert not marker.exists()


def test_old_manifest_without_requested_seeds_fails_check(tmp_path):
    (tmp_path / "old").mkdir()
    (tmp_path / "old/manifest.json").write_text(json.dumps({"batch": "old", "seeds": [{"seed": i, "exit_code": 0} for i in range(3)]}))
    r = run(tmp_path, "check", "--batch", "old")
    assert r.returncode != 0
    assert "predates" in r.stdout


def test_finished_batch_is_read_only_and_prints_a_checksum(tmp_path):
    r = execute(tmp_path, "b", "-c", "pass  # {seed}", seeds="0")
    assert "sha256" in r.stdout
    for name in ("manifest.json", "seed-0.log"):
        assert not os.stat(tmp_path / "b" / name).st_mode & stat.S_IWUSR
