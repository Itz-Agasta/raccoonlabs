"""Tracked files must not leak the sealed papers. The term list itself stays untracked."""
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TERMS = ROOT / "notes/sealed-terms.txt"


def test_tracked_files_have_no_sealed_terms():
    if not TERMS.exists():
        pytest.skip("notes/sealed-terms.txt is local only")
    terms = [t.strip().lower() for t in TERMS.read_text().splitlines() if t.strip()]
    files = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    leaks = []
    for name in files:
        path = ROOT / name
        if not path.is_file():
            continue
        text = path.read_text(errors="ignore").lower()
        leaks += [f"{name}: {t}" for t in terms if t in text]
    assert not leaks, leaks
