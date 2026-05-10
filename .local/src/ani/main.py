#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多來源 fzf 看片器（可擴充來源清單版）
流程：
  搜尋關鍵字 → 同時搜尋所有來源 → fzf 選影片 → fzf 選劇集 → 自動呼叫播放器

新增來源時，只要：
  1. 寫好 search / tracks / resolve_play（resolve_play 可選）
  2. 把 Source 加進 SOURCES

依賴：
  - fzf
  - requests
  - beautifulsoup4
"""

from __future__ import annotations

import base64
import concurrent.futures
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Callable, Optional
from urllib.parse import quote, unquote

import requests
from bs4 import BeautifulSoup


UA_OLE = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0"
)
UA_WEB = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)
UA_IYF = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.3"
)

OLE_SITE = "https://api.olelive.com"
DBKU_SITE = "https://www.dbku.tv"
IYF_SITE = "https://m10.iyf.tv"

session = requests.Session()
IYF_KEYS: Optional[dict] = None


# -------------------- 基礎工具 --------------------
def http_get(url: str, headers: Optional[dict] = None, timeout: int = 12) -> requests.Response:
    r = session.get(url, headers=headers or {}, timeout=timeout)
    r.raise_for_status()
    return r


def safe_str(x) -> str:
    return "" if x is None else str(x)


# -------------------- 資料結構 --------------------
@dataclass(frozen=True)
class Source:
    id: str
    name: str
    search: Callable[[str], list[dict]]
    tracks: Callable[[str], list[dict]]
    resolve_play: Callable[[str], Optional[str]]


# -------------------- olelive --------------------
def ole_signature(timestamp_str: str) -> str:
    def digit_bin(ch):
        parts = []
        for i, c in enumerate(ch):
            if i != 0:
                parts.append(" ")
            parts.append(bin(ord(c))[2:])
        return "".join(parts)

    r = [[], [], [], []]
    for ch in timestamp_str:
        b = digit_bin(ch)
        r[0].append(b[2:3] if len(b) > 2 else "")
        r[1].append(b[3:4] if len(b) > 3 else "")
        r[2].append(b[4:5] if len(b) > 4 else "")
        r[3].append(b[5:] if len(b) > 5 else "")

    a = []
    for bits in r:
        s = "".join(bits)
        a.append("000" if s == "" else hex(int(s, 2))[2:].zfill(3))

    md5 = hashlib.md5(timestamp_str.encode()).hexdigest()
    return (
        md5[0:3] + a[0] + md5[6:11] + a[1] + md5[14:19] + a[2] + md5[22:27] + a[3] + md5[30:]
    )


def ole_get_sign() -> str:
    return ole_signature(str(int(time.time())))


def ole_search(keyword: str) -> list[dict]:
    try:
        url = f"{OLE_SITE}/v1/pub/index/search/{quote(keyword)}/vod/0/1/48?_vv={ole_get_sign()}"
        data = http_get(url, headers={"User-Agent": UA_OLE}).json().get("data", {}).get("data", [])
        vod_data = next((x for x in data if x.get("type") == "vod"), None)

        cards: list[dict] = []
        if vod_data:
            for item in vod_data.get("list", []):
                if item.get("vip"):
                    continue
                cards.append(
                    {
                        "source": "ole",
                        "source_name": "欧乐",
                        "title": item.get("name", ""),
                        "remark": item.get("remark", ""),
                        "play_ref": safe_str(item.get("id", "")),
                    }
                )
        return cards
    except Exception:
        return []


def ole_tracks(play_ref: str) -> list[dict]:
    try:
        url = f"{OLE_SITE}/v1/pub/vod/detail/{play_ref}/true?_vv={ole_get_sign()}"
        data = http_get(url, headers={"User-Agent": UA_OLE}).json().get("data", {})
        tracks: list[dict] = []
        for item in data.get("urls", []):
            tracks.append(
                {
                    "name": item.get("title", ""),
                    "play_ref": item.get("url", ""),
                }
            )
        return tracks
    except Exception:
        return []


def ole_resolve_play(track_ref: str) -> Optional[str]:
    return track_ref or None


# -------------------- duboku --------------------
def dbku_search(keyword: str) -> list[dict]:
    try:
        url = f"{DBKU_SITE}/vodsearch/-------------.html?wd={quote(keyword)}&submit="
        html = http_get(
            url,
            headers={
                "Referer": DBKU_SITE,
                "Origin": DBKU_SITE,
                "User-Agent": UA_WEB,
            },
        ).text

        soup = BeautifulSoup(html, "html.parser")
        cards: list[dict] = []
        seen = set()

        for a in soup.select("a.myui-vodlist__thumb"):
            href = a.get("href", "")
            if not href.startswith("/voddetail/"):
                continue
            if href in seen:
                continue
            seen.add(href)

            title = (a.get("title") or "").strip()
            remark_node = a.select_one(".text-right")
            remark = remark_node.get_text(" ", strip=True) if remark_node else ""

            cards.append(
                {
                    "source": "dbku",
                    "source_name": "独播库",
                    "title": title,
                    "remark": remark,
                    "play_ref": DBKU_SITE + href,
                }
            )
        return cards
    except Exception:
        return []


def dbku_tracks(detail_url: str) -> list[dict]:
    try:
        html = http_get(
            detail_url,
            headers={
                "Referer": DBKU_SITE,
                "Origin": DBKU_SITE,
                "User-Agent": UA_WEB,
            },
        ).text

        soup = BeautifulSoup(html, "html.parser")
        tracks: list[dict] = []
        for a in soup.select("#playlist1 a"):
            href = a.get("href", "")
            if href.startswith("/vodplay/"):
                tracks.append(
                    {
                        "name": a.get_text(" ", strip=True),
                        "play_ref": DBKU_SITE + href,
                    }
                )
        return tracks
    except Exception:
        return []


def dbku_resolve_play(play_page_url: str) -> Optional[str]:
    try:
        html = http_get(
            play_page_url,
            headers={
                "Referer": DBKU_SITE,
                "Origin": DBKU_SITE,
                "User-Agent": UA_WEB,
            },
        ).text

        m = re.search(r"var\s+player_data\s*=\s*({.*?})\s*</script>", html, re.S)
        if not m:
            m = re.search(r"var\s+player_.*?\s*=\s*({.*?})\s*</script>", html, re.S)
        if not m:
            return None

        obj = json.loads(m.group(1))
        player = obj.get("url", "")

        if obj.get("encrypt") == 1:
            player = unquote(player)
        elif obj.get("encrypt") == 2:
            player = unquote(base64.b64decode(player).decode("utf-8", "ignore"))
        elif obj.get("encrypt") == 3:
            player = player[8:]
            player = base64.b64decode(player).decode("utf-8", "ignore")
            player = player[8:-8]

        return player or None
    except Exception:
        return None


# -------------------- iyf --------------------
def iyf_update_keys() -> dict:
    global IYF_KEYS
    if IYF_KEYS is not None:
        return IYF_KEYS

    html = http_get("https://www.iyf.tv", headers={"User-Agent": UA_IYF}).text
    m = re.search(r"var\s+injectJson\s*=\s*(\{.*?\});", html, re.S)
    if not m:
        raise RuntimeError("无法获取爱壹帆密钥")

    data = json.loads(m.group(1))
    public_key = data["config"][0]["pConfig"]["publicKey"]
    private_key = data["config"][0]["pConfig"]["privateKey"]
    IYF_KEYS = {"publicKey": public_key, "privateKey": private_key}
    return IYF_KEYS


def iyf_get_private_key() -> str:
    private_key = iyf_update_keys()["privateKey"]
    return private_key[int(time.time() * 1000) % len(private_key)]


def iyf_get_signature(query: str) -> str:
    public_key = iyf_update_keys()["publicKey"]
    private_key = iyf_get_private_key()
    input_str = public_key + "&" + query.lower() + "&" + private_key
    return hashlib.md5(input_str.encode("utf-8")).hexdigest()


def iyf_search(keyword: str) -> list[dict]:
    try:
        text = quote(keyword)
        url = (
            f"https://rankv21.iyf.tv/v3/list/briefsearch"
            f"?tags={text}&orderby=4&page=1&size=10&desc=0&isserial=-1&istitle=true"
        )
        data = http_get(url, headers={"User-Agent": UA_IYF}).json()
        lst = data.get("data", {}).get("info", [{}])[0].get("result", [])

        cards: list[dict] = []
        for e in lst:
            cards.append(
                {
                    "source": "iyf",
                    "source_name": "爱壹帆",
                    "title": e.get("title", ""),
                    "remark": e.get("cid", ""),
                    "play_ref": e.get("contxt", ""),
                }
            )
        return cards
    except Exception:
        return []


def iyf_tracks(play_ref: str) -> list[dict]:
    try:
        keys = iyf_update_keys()
        public_key = keys["publicKey"]

        url = f"{IYF_SITE}/v3/video/languagesplaylist?cinema=1&vid={play_ref}&lsk=1&taxis=0&cid=0,1,4,133"
        params = url.split("?", 1)[1]
        url += f"&vv={iyf_get_signature(params)}&pub={public_key}"

        data = http_get(url, headers={"User-Agent": UA_IYF}).json()
        playlist = data.get("data", {}).get("info", [{}])[0].get("playList", [])

        tracks: list[dict] = []
        for e in playlist:
            tracks.append(
                {
                    "name": e.get("name", ""),
                    "play_ref": e.get("key", ""),
                }
            )
        return tracks
    except Exception:
        return []


def iyf_resolve_play(track_ref: str) -> Optional[str]:
    try:
        keys = iyf_update_keys()
        public_key = keys["publicKey"]

        url = f"{IYF_SITE}/v3/video/play?cinema=1&id={track_ref}&a=0&lang=none&usersign=1&region=GL.&device=1&isMasterSupport=1"
        params = url.split("?", 1)[1]
        url += f"&vv={iyf_get_signature(params)}&pub={public_key}"

        data = http_get(url, headers={"User-Agent": UA_IYF}).json()
        paths = data.get("data", {}).get("info", [{}])[0].get("flvPathList", [])

        for e in paths:
            if e.get("isHls"):
                play_url = e.get("result", "")
                if play_url:
                    return play_url + f"?vv={iyf_get_signature('')}&pub={public_key}"

        if paths:
            play_url = paths[0].get("result", "")
            if play_url:
                return play_url + f"?vv={iyf_get_signature('')}&pub={public_key}"

        return None
    except Exception:
        return None


# -------------------- 來源註冊表 --------------------
SOURCES: list[Source] = [
    Source(
        id="ole",
        name="欧乐",
        search=ole_search,
        tracks=ole_tracks,
        resolve_play=ole_resolve_play,
    ),
    Source(
        id="dbku",
        name="独播库",
        search=dbku_search,
        tracks=dbku_tracks,
        resolve_play=dbku_resolve_play,
    ),
    Source(
        id="iyf",
        name="爱壹帆",
        search=iyf_search,
        tracks=iyf_tracks,
        resolve_play=iyf_resolve_play,
    ),
]

SOURCE_BY_ID = {s.id: s for s in SOURCES}


# -------------------- fzf --------------------
def fzf_select(lines: list[str], prompt: str = "選擇: ", expect_keys: str = "alt-a") -> Optional[str]:
    """expect_keys: comma‑separated list of fzf `--expect` keys (e.g., 'alt-a,alt-s')"""
    if not lines:
        return None

    try:
        cmd = [
            "fzf",
            "--prompt",
            prompt,
            "--height=40%",
            "--border",
            "--delimiter",
            "\t",
            "--with-nth",
            "1,2,3,4",
        ]
        # 添加多个期望的按键
        if expect_keys:
            cmd.append(f"--expect={expect_keys}")
        cmd.append("--header=Enter=播放單集 | Alt+A=播放全部 | Alt+S=從此集到結尾")

        proc = subprocess.run(
            cmd,
            input="\n".join(lines),
            text=True,
            capture_output=True,
        )

        if proc.returncode != 0:
            return None

        output = proc.stdout.strip()
        if not output:
            return None

        return output

    except FileNotFoundError:
        print("❌ 找不到 fzf，請先安裝: sudo pacman -S fzf")
        sys.exit(1)


def format_search_line(item: dict) -> str:
    return "\t".join(
        [
            item.get("source_name", ""),
            item.get("title", ""),
            item.get("remark", ""),
            item.get("play_ref", ""),
        ]
    )


def parse_line(line: str) -> dict:
    parts = line.split("\t")
    while len(parts) < 4:
        parts.append("")
    return {
        "source_name": parts[0],
        "title": parts[1],
        "remark": parts[2],
        "play_ref": parts[3],
    }


# -------------------- 主流程 --------------------
def search_all(keyword: str) -> list[dict]:
    results: list[dict] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(SOURCES)) as ex:
        future_map = {ex.submit(src.search, keyword): src for src in SOURCES}
        for fut in concurrent.futures.as_completed(future_map):
            src = future_map[fut]
            try:
                items = fut.result() or []
                for item in items:
                    item.setdefault("source", src.id)
                    item.setdefault("source_name", src.name)
                results.extend(items)
            except Exception:
                continue

    return results


def get_source_by_name(source_name: str) -> Optional[Source]:
    for src in SOURCES:
        if src.name == source_name or src.id == source_name:
            return src
    return None


def build_player_base_cmd() -> list[str]:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_mpv_conf = os.path.join(script_dir, "mpv.conf")

    player_cmd = os.environ.get("OLE_PLAYER", "mpv").split()

    if os.path.isfile(local_mpv_conf):
        player_cmd.append(f"--include={local_mpv_conf}")

    return player_cmd


def play_with_player(url: str, media_title: str = ""):
    player_cmd = build_player_base_cmd()

    if media_title:
        player_cmd.append(f"--force-media-title={media_title}")

    player_cmd.append(url)

    subprocess.Popen(
        player_cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def play_with_player_playlist(entries: list[dict], start_index: int = 0):
    """
    entries: 每个元素包含 url 和 title。
    start_index: 0‑based，从列表中的第几个条目开始播放（0 = 第一个）
    """
    if not entries:
        print("播放列表為空。")
        return

    player_cmd = build_player_base_cmd()

    # 如果起始索引大于0，添加 --playlist-start
    if start_index > 0:
        player_cmd.append(f"--playlist-start={start_index}")

    for item in entries:
        url = item["url"]
        title = item.get("title", "").strip()

        if title:
            player_cmd.extend(
                [
                    "--{",
                    f"--force-media-title={title}",
                    url,
                    "--}",
                ]
            )
        else:
            player_cmd.append(url)

    subprocess.Popen(
        player_cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def main():
    keyword = input("搜尋關鍵字: ").strip()
    if not keyword:
        print("未輸入關鍵字，退出。")
        return

    print("搜尋中...")
    results = search_all(keyword)

    if not results:
        print("所有來源都沒有找到結果。")
        return

    search_lines = [format_search_line(item) for item in results]

    selected = fzf_select(
        search_lines,
        prompt="選擇影片: ",
        expect_keys="alt-a,alt-s",  # 在搜索结果阶段也可以加，但这里只用来跳过，实际不影响
    )

    if not selected:
        print("取消選擇。")
        return

    # 解析选中的影片信息（fzf 输出可能是 "key\n选中的行"）
    lines = selected.splitlines()
    if len(lines) >= 2:
        # 如果有按键，第一行是键，第二行是选中行
        # 但我们在这个阶段不需要解析按键，直接取最后一行
        selected_line = lines[-1]
    else:
        selected_line = lines[0]

    picked = parse_line(selected_line)

    source_name = picked["source_name"]
    play_ref = picked["play_ref"]
    title = picked["title"]

    src = get_source_by_name(source_name)
    if not src:
        print("未知來源。")
        return

    print("取得播放清單...")
    tracks = src.tracks(play_ref)

    if not tracks:
        print("這個來源沒有可播放的劇集。")
        return

    track_lines = []
    for t in tracks:
        name = t.get("name", "")
        ref = t.get("play_ref", "")
        if name and ref:
            track_lines.append(f"{name}\t{ref}")

    # 第二次 fzf：选择剧集，监听 alt-a / alt-s
    selected_output = fzf_select(
        track_lines,
        prompt="選擇劇集: ",
        expect_keys="alt-a,alt-s",
    )

    if not selected_output:
        print("取消選擇。")
        return

    output_lines = selected_output.splitlines()
    pressed_key = ""
    selected_ep_line = ""

    if len(output_lines) >= 2:
        pressed_key = output_lines[0].strip()
        selected_ep_line = output_lines[1].strip()
    elif len(output_lines) == 1:
        selected_ep_line = output_lines[0].strip()

    if not selected_ep_line:
        print("取消選擇。")
        return

    ep_name, ep_ref = (selected_ep_line.split("\t", 1) + [""])[:2]
    if not ep_ref:
        print("劇集資料無效。")
        return

    # 找到当前剧集在 tracks 列表中的索引（用于 Alt+S）
    try:
        current_idx = next(i for i, t in enumerate(tracks) if t.get("play_ref") == ep_ref)
    except StopIteration:
        current_idx = 0

    # --- 处理三种播放模式 ---
    if pressed_key == "alt-a":
        # 播放全部（所有集）
        entries_to_play = tracks
        start_idx = 0
    elif pressed_key == "alt-s":
        # 从当前集到结尾
        entries_to_play = tracks[current_idx:]
        start_idx = 0  # 因为列表已经是从该集开始，所以从0开始播放
    else:
        # 单集 (Enter)
        print("解析播放地址...")
        play_url = src.resolve_play(ep_ref)
        if not play_url:
            print("無法取得播放地址。")
            return

        media_title = f"[{src.name}] {title} / {ep_name}"
        print(f"▶ 正在播放: {media_title}")
        play_with_player(play_url, media_title=media_title)
        print("播放器已啟動。")
        return

    # 批量解析播放地址（用于 alt-a 或 alt-s 模式）
    print("解析播放地址...")
    playlist = []
    for t in entries_to_play:
        ep_name = t.get("name", "")
        ep_ref = t.get("play_ref", "")
        if not ep_ref:
            continue
        play_url = src.resolve_play(ep_ref)
        if play_url:
            media_title = f"[{src.name}] {title} / {ep_name}"
            playlist.append({"url": play_url, "title": media_title})

    if not playlist:
        print("沒有可播放劇集。")
        return

    if pressed_key == "alt-s":
        print(f"▶ 從第{current_idx+1}集播到結尾（共{len(playlist)}集）")
    else:
        print(f"▶ 播放全部（{len(playlist)}集）")

    play_with_player_playlist(playlist, start_index=start_idx)
    print("播放器已啟動。")


if __name__ == "__main__":
    main()
