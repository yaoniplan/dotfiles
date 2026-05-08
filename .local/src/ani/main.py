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
def fzf_select(lines: list[str], prompt: str = "選擇: ") -> Optional[str]:
    if not lines:
        return None
    try:
        proc = subprocess.run(
            [
                "fzf",
                "--prompt",
                prompt,
                "--height=40%",
                "--border",
                "--delimiter",
                "\t",
                "--with-nth",
                "1,2,3,4",
            ],
            input="\n".join(lines),
            text=True,
            capture_output=True,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
        return None
    except FileNotFoundError:
        print("❌ 找不到 fzf，請先安裝: sudo pacman -S fzf")
        sys.exit(1)


def format_search_line(item: dict) -> str:
    # source_name \t title \t remark \t play_ref
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
                # 統一補上來源 id/name，方便後面擴充
                for item in items:
                    item.setdefault("source", src.id)
                    item.setdefault("source_name", src.name)
                results.extend(items)
            except Exception:
                # 單一來源炸掉，直接略過
                continue

    return results


def get_source_by_name(source_name: str) -> Optional[Source]:
    for src in SOURCES:
        if src.name == source_name or src.id == source_name:
            return src
    return None


def play_with_player(url: str, media_title: str = ""):
    # main.py 所在目錄
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # ani/mpv.conf
    local_mpv_conf = os.path.join(script_dir, "mpv.conf")

    player_cmd = os.environ.get("OLE_PLAYER", "mpv").split()

    # 有專案設定才載入，沒有就 fallback 到 mpv global config
    if os.path.isfile(local_mpv_conf):
        player_cmd.append(f"--include={local_mpv_conf}")

    if media_title:
        player_cmd.append(f"--force-media-title={media_title}")

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
    selected = fzf_select(search_lines, prompt="選擇影片: ")
    if not selected:
        print("取消選擇。")
        return

    picked = parse_line(selected)
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

    track_lines = [f"{t.get('name', '')}\t{t.get('play_ref', '')}" for t in tracks if t.get("name")]
    selected_ep = fzf_select(track_lines, prompt="選擇劇集: ")
    if not selected_ep:
        print("取消選擇。")
        return

    ep_name, ep_ref = (selected_ep.split("\t", 1) + [""])[:2]
    if not ep_ref:
        print("劇集資料無效。")
        return

    print("解析播放地址...")
    play_url = src.resolve_play(ep_ref)
    if not play_url:
        print("無法取得播放地址。")
        return

    media_title = f"[{src.name}] {title} / {ep_name}"
    print(f"▶ 正在播放: {media_title}")
    play_with_player(play_url, media_title=media_title)
    print("播放器已啟動。")
