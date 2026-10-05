"""Minimal .env loader (stdlib only). Does not override existing env vars."""

from __future__ import annotations

import os
from pathlib import Path


def load_dotenv(*paths: str | Path | None) -> None:
    candidates: list[Path] = []
    for p in paths:
        if p:
            candidates.append(Path(p))
    # project root (next to this file) and cwd
    here = Path(__file__).resolve().parent
    candidates.extend([here / ".env", Path.cwd() / ".env"])

    seen: set[Path] = set()
    for path in candidates:
        try:
            path = path.resolve()
        except OSError:
            continue
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            if "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()
            if not key:
                continue
            if (val.startswith('"') and val.endswith('"')) or (
                val.startswith("'") and val.endswith("'")
            ):
                val = val[1:-1]
            if key not in os.environ:
                os.environ[key] = val
