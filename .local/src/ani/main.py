#!/usr/bin/env python3

import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from selector import fzf_input, fzf_select, fzf_select_movie_stream


PROVIDERS = [
    "duboku",
    "ole",
    "7sefun",
    "yhdm",
    "iyf",
    #"myself",
    #"i275",
]


def load_provider(name):
    try:
        mod = importlib.import_module(f"providers.{name}")
        return mod.Provider()
    except Exception:
        print(f"❌ 載入 {name} 失敗")
        return None


def main():
    # 此 prompt 會立刻出現，因為不再先載入所有 provider
    keyword = fzf_input("搜尋關鍵字: ")
    if not keyword:
        sys.exit(0)

    selected_card = fzf_select_movie_stream(PROVIDERS, load_provider, keyword)

    if not selected_card:
        print("沒有找到結果。")
        sys.exit(0)

    src = selected_card["_provider"]
    title = selected_card.get("vod_name", "未知")

    try:
        tracks = src.get_tracks(selected_card)
    except Exception:
        print("取得播放清單失敗。")
        sys.exit(1)

    if not tracks:
        print("沒有可播放劇集。")
        sys.exit(0)

    ep_lines = [ep["name"] for ep in tracks]
    selected_ep = fzf_select(ep_lines, prompt="選擇劇集: ")

    if not selected_ep:
        print("未選擇劇集，退出。")
        sys.exit(0)

    try:
        selected_index = ep_lines.index(selected_ep)
    except ValueError:
        print("找不到選擇的劇集")
        sys.exit(1)

    try:
        play_url = src.resolve_play(tracks[selected_index])
    except Exception:
        print("解析播放地址失敗。")
        sys.exit(1)

    if not play_url:
        print("播放地址為空。")
        sys.exit(1)

    from player import play_single

    play_single(
        source_name=src.name,
        anime_title=title,
        tracks=tracks,
        start_index=selected_index,
        play_url=play_url,
        preferred_player=getattr(src, "preferred_player", None),
    )


if __name__ == "__main__":
    main()
