#!/usr/bin/env python3
"""Search → select publication → section fzf (stream) → read."""

from __future__ import annotations

import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from envutil import load_dotenv

load_dotenv()

from reader import launch_online, launch_pdf_reader, launch_reader
from selector import fzf_select, fzf_select_book_stream, fzf_select_sections_stream

PROVIDERS = [
    "zlib",
    "libgen",
    "opds",
]


def load_provider(name: str):
    try:
        mod = importlib.import_module(f"providers.{name}")
        # zlib: reuse session (skip re-login every search)
        if name == "zlib" and hasattr(mod, "get_shared_provider"):
            return mod.get_shared_provider()
        return mod.Provider()
    except Exception as e:
        print(f"❌ 载入 {name} 失败: {e}")
        return None


def main():
    keyword = fzf_select([], prompt="搜尋關鍵字: ")
    if not keyword:
        sys.exit(0)
    keyword = keyword.strip()

    card = fzf_select_book_stream(PROVIDERS, load_provider, keyword)
    if not card:
        print("未选中任何出版物。")
        sys.exit(0)

    provider = card["_provider"]
    title = card.get("name") or "未知"
    ext = (card.get("extension") or "epub").lower()
    online = (card.get("readOnlineUrl") or "").strip()

    def try_online(reason: str = "") -> bool:
        if not online:
            return False
        if reason:
            print(reason)
        launch_online(online, title)
        return True

    if ext not in ("epub", "epub3", "pdf"):
        if try_online():
            return
        print(f"暂不支持 .{ext}（支持 epub / pdf）")
        sys.exit(1)

    try:
        sections, start_index = fzf_select_sections_stream(provider, card)
    except Exception as e:
        if try_online(f"获取章节失败，改用在线阅读: {e}"):
            return
        print(f"获取章节失败: {e}")
        sys.exit(1)

    if not sections:
        if try_online("无本地章节，改用在线阅读"):
            return
        print("未选中章节或目录为空。")
        sys.exit(0)

    try:
        if ext == "pdf":
            path = sections[0].get("path") or provider.ensure_file(card)
            src = card.get("_provider_module") or getattr(provider, "name", "") or ""
            launch_pdf_reader(
                path, title=title, start_page=start_index + 1, source=src
            )
        else:
            launch_reader(
                provider=provider,
                card=card,
                sections=sections,
                start_index=start_index,
            )
    except Exception as e:
        if try_online(f"打开失败，改用在线阅读: {e}"):
            return
        print(f"打开阅读器失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
