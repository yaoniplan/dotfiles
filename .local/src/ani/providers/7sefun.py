# https://github.com/Yswag/xptv-extensions/blob/main/js/7sefun.js
import base64
import json
import re
from urllib.parse import quote, unquote, urljoin

import requests
from bs4 import BeautifulSoup

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad


class Provider:
    name = "7sf"
    #name = "七色番"

    BASE = "https://www.7sefun.top"

    UA = (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0"
    )

    # 只保留有 parse 的线路；空 parse 会走站内 dp 解析流程
    PLAYER_CONFIG = {
        "lmm": {
            "show": "七色A线",
            "parse": "https://dp.no3acg.com/player/ec.php?code=qw&if=1&from=lmm&url=",
        },
        "funzy": {
            "show": "日漫高清",
            "parse": "https://nplayer.7sefun.top/player/index.php?code=qw&url=",
        },
        "sssfun": {
            "show": "日漫流畅版",
            "parse": "https://www.7sefun.com/jx.php?url=",
        },
        "7sefun": {
            "show": "七色番",
            "parse": "https://play.7sefun.com/?url=",
        },
        "bilibili": {
            "show": "bilibili",
            "parse": "https://jx.jsonplayer.com/player/?url=",
        },
        "lzm3u8": {
            "show": "备用有广告版",
            "parse": "https://mf.qiau.cn/json.php?url=",
        },
        "qiyi": {
            "show": "奇艺视频",
            "parse": "https://jx.jsonplayer.com/player/?url=",
        },
        "qq": {
            "show": "腾讯视频",
            "parse": "https://jx.jsonplayer.com/player/?url=",
        },
        "youku": {
            "show": "优酷视频",
            "parse": "https://jx.jsonplayer.com/player/?url=",
        },
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.UA,
            "Referer": self.BASE,
            "Origin": self.BASE,
        })

    # ---------- 搜索 ----------
    def search(self, keyword, page=1):
        cards = []

        url = (
            f"{self.BASE}/vodsearch/{quote(keyword)}"
            f"----------{page}---.html"
        )

        resp = self.session.get(url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for item in soup.select("div.video"):
            a = item.select_one("a.video-wrapper") or item.select_one("a[href]")
            if not a:
                continue

            href = a.get("href", "")
            if not href:
                continue

            img = item.select_one("img.videoimg")
            title = ""
            cover = ""

            if img:
                title = (
                    img.get("alt")
                    or img.get("title")
                    or a.get("title")
                    or a.text.strip()
                )
                cover = img.get("src") or img.get("data-original") or ""

            if not title:
                title = a.get("title") or a.text.strip()

            time_tag = item.select_one(".video-time")
            remarks = time_tag.text.strip() if time_tag else ""

            if title and len(title) > 1:
                cards.append({
                    "vod_id": href,
                    "vod_name": title,
                    "vod_pic": cover,
                    "vod_remarks": remarks,
                    "url": urljoin(self.BASE, href),
                })

        return cards

    # ---------- 选集：只返回第一条线路 ----------
    def get_tracks(self, card):
        tracks = []

        resp = self.session.get(card["url"], timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        containers = soup.select(".vod-play-list-container")

        if containers:
            # 只使用第一条线路，避免把所有线路都平铺出来
            first = containers[0]
            for a in first.select("span a[href]"):
                href = a.get("href", "")
                if not href:
                    continue

                tracks.append({
                    "name": a.text.strip() or "播放",
                    "url": urljoin(self.BASE, href),
                })
        else:
            # 站点改版时的兜底选择器
            episode_selectors = [
                "a[href*='/vod/play/']",
                "a[href*='play/id']",
                ".playlist a",
                ".sort-list a",
                ".episode-list a",
                ".video-list a",
            ]

            for sel in episode_selectors:
                links = soup.select(sel)
                if links:
                    for a in links:
                        href = a.get("href", "")
                        if href:
                            tracks.append({
                                "name": a.text.strip() or "播放",
                                "url": urljoin(self.BASE, href),
                            })
                    break

        return tracks

    # ---------- JS 对象提取 ----------
    @staticmethod
    def _extract_js_object(text, pattern):
        """
        从 JS 文本中提取第一个 `{...}` 对象，并尝试按 JSON 解析。
        会忽略字符串内的花括号，避免截断错误。
        """
        m = re.search(pattern, text, re.S)
        if not m:
            return None

        start = m.end()
        while start < len(text) and text[start] in " \t\r\n":
            start += 1

        if start >= len(text) or text[start] != "{":
            return None

        brace_count = 0
        in_string = None
        escaped = False

        for i in range(start, len(text)):
            ch = text[i]

            if in_string:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == in_string:
                    in_string = None
                continue

            if ch in ('"', "'"):
                in_string = ch
            elif ch == "{":
                brace_count += 1
            elif ch == "}":
                brace_count -= 1
                if brace_count == 0:
                    json_str = text[start:i + 1]
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        return None

        return None

    def _parse_player_config(self, html):
        """解析 var player_aaaa = {...} 配置。"""
        soup = BeautifulSoup(html, "html.parser")

        for script in soup.find_all("script"):
            text = script.string or script.get_text()
            if "player_aaaa" not in text:
                continue

            cfg = self._extract_js_object(text, r"var\s+player_aaaa\s*=\s*")
            if cfg is not None:
                return cfg

        cfg = self._extract_js_object(html, r"var\s+player_aaaa\s*=\s*")
        if cfg is not None:
            return cfg

        raise Exception("找不到播放器配置 player_aaaa")

    # ---------- 加密/编码工具 ----------
    @staticmethod
    def _base64_decode_utf8(s):
        s = s.strip()
        try:
            return base64.b64decode(s).decode("utf-8")
        except Exception:
            pass

        s_padded = s + "=" * (-len(s) % 4)
        try:
            return base64.b64decode(s_padded).decode("utf-8")
        except Exception:
            return base64.urlsafe_b64decode(s_padded).decode("utf-8")

    @staticmethod
    def _js_unescape(s):
        """模拟 JS 的 unescape：处理 %xx 和 %uXXXX。"""
        s = re.sub(
            r"%u([0-9A-Fa-f]{4})",
            lambda m: chr(int(m.group(1), 16)),
            s,
        )
        return unquote(s)

    @staticmethod
    def _aes_decrypt(ciphertext: str, uid: str) -> str:
        key = f"2890{uid}tB959C".encode("utf-8")
        iv = b"2F131BE91247866E"

        try:
            data = base64.b64decode(ciphertext)
        except Exception:
            data = base64.b64decode(ciphertext + "=" * (-len(ciphertext) % 4))

        cipher = AES.new(key, AES.MODE_CBC, iv)
        return unpad(
            cipher.decrypt(data),
            AES.block_size,
        ).decode("utf-8")

    # ---------- 播放解析 ----------
    def resolve_play(self, track):
        resp = self.session.get(track["url"], timeout=15)
        resp.raise_for_status()
        html = resp.text

        config = self._parse_player_config(html)

        if "url" not in config:
            raise Exception("播放配置缺少 url")

        try:
            encrypt = int(config.get("encrypt", 0))
        except (TypeError, ValueError):
            encrypt = None

        if encrypt == 2:
            # 新版加密：base64 + unescape 后才得到真实地址
            video_url = self._js_unescape(
                self._base64_decode_utf8(config["url"])
            )

            from_ = config.get("from", "")
            link = config.get("link", "")
            ep_id = link.rstrip("/").split("/")[-1].split("-")[0] if link else ""

            jx_cfg = self.PLAYER_CONFIG.get(from_, {})
            jx_url = jx_cfg.get("parse", "") if jx_cfg else ""

            if not jx_url:
                # 没有外部解析接口，走站内 dp 播放器
                index_url = (
                    f"{self.BASE}/addons/dp/player/index.php"
                    f"?key=0&id={ep_id}&uid=0&from={from_}&url={video_url}"
                )

                resp = self.session.get(
                    index_url,
                    headers={"User-Agent": self.UA},
                    timeout=15,
                )
                resp.raise_for_status()
                index_data = resp.text

                m = re.search(r'href="([^"]+)";', index_data)
                if not m:
                    raise Exception("找不到播放器跳转链接")

                player_url = urljoin(self.BASE, m.group(1))

                if "art.php" in player_url:
                    resp = self.session.get(
                        player_url,
                        headers={"User-Agent": self.UA},
                        timeout=15,
                    )
                    resp.raise_for_status()
                    art_data = resp.text

                    art_cfg = self._extract_js_object(
                        art_data,
                        r"config\s*=\s*",
                    )
                    if not art_cfg or "url" not in art_cfg:
                        raise Exception("找不到 art.php 中的 config")

                    return art_cfg["url"]

                # 其它播放器页面，例如 dp.php
                resp = self.session.get(
                    player_url,
                    headers={"User-Agent": self.UA},
                    timeout=15,
                )
                resp.raise_for_status()
                player_data = resp.text

                cfg = self._extract_js_object(
                    player_data,
                    r"config\s*=\s*",
                )
                if cfg and "url" in cfg:
                    return cfg["url"]

                # 兜底：直接匹配 mp4/m3u8/flv 地址
                m = re.search(
                    r"https?://[^\s\"']+\.(?:mp4|m3u8|flv)",
                    player_data,
                )
                if m:
                    return m.group(0)

                raise Exception("找不到视频地址")

            elif "ec.php" in jx_url:
                parser_url = jx_url + video_url

                resp = self.session.get(
                    parser_url,
                    headers={
                        "User-Agent": self.UA,
                        "Referer": track["url"],
                    },
                    timeout=15,
                )
                resp.raise_for_status()
                jx_data = resp.text

                m = re.search(
                    r"ConFig\s*=\s*(\{[\s\S]*?\})\s*,\s*box",
                    jx_data,
                )
                if not m:
                    raise Exception("找不到 ConFig")

                conf = json.loads(m.group(1))

                if "config" not in conf or "uid" not in conf["config"]:
                    raise Exception("ConFig 缺少 config.uid")

                return self._aes_decrypt(
                    conf["url"],
                    conf["config"]["uid"],
                )

            else:
                raise Exception(f"不支援的播放线路: {from_}")

        elif config["url"].endswith(".m3u8"):
            return config["url"]

        raise Exception("無法解析播放地址")
