#!/usr/bin/env python3
"""Search → select comic → select chapter → read."""

import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reader import launch_reader
from selector import fzf_select, fzf_select_comic_stream

PROVIDERS = [
    "copy",
    "manwa",
    "guazi",
    "hip",
    "manhuagui",
]


def load_provider(name: str):
    try:
        return importlib.import_module(f"providers.{name}").Provider()
    except Exception as e:
        print(f"❌ 载入 {name} 失败: {e}")
        return None


def main():
    keyword = fzf_select([], prompt="搜尋關鍵字: ")
    if not keyword:
        sys.exit(0)
    keyword = keyword.strip()

    card = fzf_select_comic_stream(PROVIDERS, load_provider, keyword)
    if not card:
        print("未选中任何漫画。")
        sys.exit(0)

    provider = card["_provider"]
    chapters = provider.get_chapters(card)
    if not chapters:
        print("未发现有效章节。")
        sys.exit(0)

    chap_lines = [c["name"] for c in chapters]
    selected = fzf_select(chap_lines, prompt="选择章节: ")
    if not selected:
        sys.exit(0)
    idx = chap_lines.index(selected)

    launch_reader(provider=provider, card=card, chapters=chapters, start_index=idx)


if __name__ == "__main__":
    main()
