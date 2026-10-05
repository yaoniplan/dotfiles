#!/usr/bin/env python3
"""Provider smoke tests — interactive or CLI (CI-friendly).

Interactive:
  uv run test.py

Non-interactive:
  uv run test.py libgen "The Diary of a Young Girl"
  uv run test.py libgen "python" --download
  uv run test.py zlib "anne frank" --download --limit 3
  uv run test.py all "python"          # search only on every provider
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import platform
import shutil
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from envutil import load_dotenv

load_dotenv()

def discover_providers() -> list[str]:
    """Provider modules under providers/*.py (skip private/underscore names)."""
    root = Path(os.path.dirname(os.path.abspath(__file__))) / "providers"
    names = []
    for p in sorted(root.glob("*.py")):
        if p.name.startswith("_"):
            continue
        names.append(p.stem)
    return names


PROVIDERS = discover_providers()


def fzf_available() -> bool:
    return shutil.which("fzf") is not None


def fzf_select(options: list[str], prompt: str = "请选择"):
    if not options:
        return None
    if not fzf_available() or not sys.stdin.isatty():
        return options[0]
    try:
        proc = subprocess.run(
            ["fzf", "--prompt", f"{prompt}: ", "--height", "40%", "--border"],
            input="\n".join(options),
            text=True,
            stdout=subprocess.PIPE,
        )
        if proc.returncode != 0:
            return None
        return proc.stdout.strip() or None
    except Exception:
        return options[0]


def ask_yes(msg: str, default: bool = True) -> bool:
    if not sys.stdin.isatty():
        return default
    hint = "Y/n" if default else "y/N"
    try:
        ans = input(f"{msg} ({hint}): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return default
    if not ans:
        return default
    return ans in ("y", "yes", "1", "是")


def load_provider(name: str):
    mod = importlib.import_module(f"providers.{name}")
    if name == "zlib" and hasattr(mod, "get_shared_provider"):
        return mod.get_shared_provider()
    return mod.Provider()


class Report:
    def __init__(self, provider: str, keyword: str):
        self.meta = {
            "provider": provider,
            "keyword": keyword,
            "time": datetime.now().isoformat(timespec="seconds"),
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        }
        self.steps: list[dict] = []
        self.trace: str | None = None

    def ok(self, step: str, **info):
        self.steps.append({"step": step, "ok": True, **info})
        print(f"  ✓ {step}", end="")
        if info:
            print(f"  { {k: v for k, v in info.items() if k != 'preview'} }")
        else:
            print()

    def fail(self, step: str, err: BaseException):
        self.steps.append({"step": step, "ok": False, "error": str(err)})
        self.trace = traceback.format_exc()
        print(f"  ✗ {step}: {err}")

    def dump(self):
        print("\n===== DIAG REPORT =====")
        print(json.dumps({"meta": self.meta, "steps": self.steps}, ensure_ascii=False, indent=2))
        if self.trace:
            print("--- traceback ---")
            print(self.trace.rstrip())
        print("===== END REPORT =====")

    @property
    def success(self) -> bool:
        return all(s.get("ok") for s in self.steps) and any(
            s.get("step") == "search" and s.get("count", 0) > 0 for s in self.steps
        )


def pick_card(cards: list[dict], prefer_ext: str | None) -> dict:
    if prefer_ext:
        for c in cards:
            if (c.get("extension") or "").lower() == prefer_ext.lower():
                return c
    for c in cards:
        if (c.get("extension") or "").lower() in ("epub", "pdf"):
            return c
    return cards[0]


def run_one(
    name: str,
    keyword: str,
    *,
    do_download: bool,
    limit: int,
    pick_index: int | None,
    prefer_ext: str | None,
    auto_yes: bool,
) -> Report:
    report = Report(name, keyword)
    print(f"\n=== {name} ===")

    try:
        provider = load_provider(name)
        report.ok("load")
    except Exception as e:
        report.fail("load", e)
        return report

    if hasattr(provider, "login"):
        try:
            ok = provider.login()
            if not ok:
                raise RuntimeError("login returned False")
            report.ok("login")
        except Exception as e:
            report.fail("login", e)
            return report

    try:
        cards = provider.search(keyword, limit=limit)
        report.ok("search", count=len(cards))
    except Exception as e:
        report.fail("search", e)
        return report

    if not cards:
        print("  (no results)")
        return report

    for i, c in enumerate(cards[:limit]):
        print(
            f"    {i}: [{c.get('extension')}] {(c.get('name') or '')[:60]}  "
            f"{c.get('size', '')}  {(c.get('remark') or '')[:40]}"
        )

    if pick_index is not None and 0 <= pick_index < len(cards):
        card = cards[pick_index]
    elif auto_yes or not sys.stdin.isatty():
        card = pick_card(cards, prefer_ext)
    else:
        labels = [
            f"{i}: [{c.get('extension')}] {c.get('name', '')[:70]}  {c.get('size', '')}"
            for i, c in enumerate(cards)
        ]
        sel = fzf_select(labels, prompt="card")
        if not sel:
            return report
        card = cards[int(sel.split(":")[0])]

    report.ok(
        "select",
        id=str(card.get("id", ""))[:40],
        name=(card.get("name") or "")[:80],
        extension=card.get("extension"),
    )

    if not do_download:
        if auto_yes or not sys.stdin.isatty():
            return report
        if not ask_yes("run get_sections / ensure_file?", default=True):
            return report

    try:
        sections = provider.get_sections(card)
        report.ok("get_sections", count=len(sections))
        for s in sections[:8]:
            print(f"     - {s.get('name')}")
        if len(sections) > 8:
            print(f"     … +{len(sections) - 8} more")
    except Exception as e:
        report.fail("get_sections", e)
        try:
            path = provider.ensure_file(card)
            report.ok("ensure_file", path=str(path), size=path.stat().st_size)
        except Exception as e2:
            report.fail("ensure_file", e2)
        return report

    if sections and (auto_yes or not sys.stdin.isatty() or ask_yes("resolve_read first section?", default=True)):
        try:
            data = provider.resolve_read(sections[0])
            preview = ""
            if isinstance(data.get("html"), str):
                preview = data["html"][:200]
            elif isinstance(data.get("paragraphs"), list):
                preview = " ".join(str(x) for x in data["paragraphs"][:3])[:200]
            report.ok("resolve_read", keys=list(data.keys())[:12], preview=preview)
            if preview:
                print(f"     preview: {preview[:120]}…")
        except Exception as e:
            report.fail("resolve_read", e)

    return report


def main() -> None:
    ap = argparse.ArgumentParser(description="pub provider tests")
    ap.add_argument(
        "provider",
        nargs="?",
        default=None,
        help="zlib | anna | libgen | all  (default: interactive pick)",
    )
    ap.add_argument("keyword", nargs="?", default=None, help="search keyword")
    ap.add_argument("--download", "-d", action="store_true", help="run get_sections/ensure_file")
    ap.add_argument("--yes", "-y", action="store_true", help="no prompts; auto-pick first suitable card")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--index", type=int, default=None, help="pick search result index")
    ap.add_argument("--ext", default=None, help="prefer extension (epub/pdf)")
    args = ap.parse_args()

    if args.provider is None and sys.stdin.isatty():
        name = fzf_select(PROVIDERS, prompt="provider")
        if not name:
            sys.exit(0)
        try:
            keyword = input("keyword: ").strip() or "python"
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)
        names = [name]
        auto_yes = False
        do_download = args.download
    else:
        names = PROVIDERS if (args.provider or "all") == "all" else [args.provider]
        for n in names:
            if n not in PROVIDERS:
                print(f"unknown provider: {n}", file=sys.stderr)
                sys.exit(2)
        keyword = args.keyword or "python"
        auto_yes = args.yes or not sys.stdin.isatty()
        do_download = args.download

    failed = 0
    reports = []
    for name in names:
        rep = run_one(
            name,
            keyword,
            do_download=do_download,
            limit=args.limit,
            pick_index=args.index,
            prefer_ext=args.ext,
            auto_yes=auto_yes,
        )
        reports.append(rep)
        rep.dump()
        if not rep.success:
            failed += 1

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
