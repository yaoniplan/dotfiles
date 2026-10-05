"""Minimal PDF helpers (stdlib only)."""

from __future__ import annotations

import re
from pathlib import Path


def page_count(path: str | Path) -> int:
    """Best-effort page count from PDF bytes (largest /Count)."""
    data = Path(path).read_bytes()
    if not data.startswith(b"%PDF"):
        raise ValueError("not a PDF")
    counts = [int(x) for x in re.findall(rb"/Count\s+(\d+)", data)]
    if counts:
        return max(1, max(counts))
    # fallback: count page objects
    n = len(re.findall(rb"/Type\s*/Page\b", data))
    return max(1, n)
