#!/usr/bin/env python3
"""Hash notes/sealed-blocklist.txt (local only) into envelope/blocklist.sha256 (tracked)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/lab_search"))
from lab_search import digest  # noqa: E402

terms = [t.strip() for t in (ROOT / "notes/sealed-blocklist.txt").read_text().splitlines() if t.strip()]
(ROOT / "envelope/blocklist.sha256").write_text("".join(sorted(digest(t) + "\n" for t in terms)))
print(f"{len(terms)} terms hashed")
