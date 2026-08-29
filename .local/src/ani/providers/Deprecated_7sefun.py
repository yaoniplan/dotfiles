# https://github.com/Yswag/xptv-extensions/blob/main/js/7sefun.js
# Because the site owner updates the encryption method too frequently.

import base64
import json
import re
import warnings
from urllib.parse import quote, unquote

import requests
from bs4 import BeautifulSoup
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from urllib3.exceptions import InsecureRequestWarning

# 外部解析站常見過期證書，關閉對應告警
warnings.filterwarnings("ignore", category=InsecureRequestWarning)


class Provider:
    name = "7sf"
    #name = "七色番"
    BASE = "https://www.7sefun.top"
    UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0"
    )

    # from → parse url (empty = internal player)
    PLAYER_CONFIG = {
        "2bdm": {"show": "七色R线", "parse": ""},
        "lmm": {
            "show": "七色A线",
            "parse": (
                "https://dp.no3acg.com/player/ec.php"
                "?code=qw&if=1&from=lmm&url="
            ),
        },
        "H265": {"show": "高清H265", "parse": ""},
        "CYDD1": {"show": "七色C线", "parse": ""},
        "ndx": {"show": "七色B线", "parse": ""},
        "funzy": {
            "show": "日漫高清",
            "parse": (
                "https://nplayer.7sefun.top/player/"
                "index.php?code=qw&url="
            ),
        },
        "funzycn": {"show": "国语高清", "parse": ""},
        "funzy4K": {"show": "4K超清", "parse": ""},
        "tsfun": {"show": "特摄", "parse": ""},
        "sssfun": {
            "show": "日漫流畅版",
            "parse": "https://www.7sefun.com/jx.php?url=",
        },
        "sssfuncn": {"show": "国语流畅", "parse": ""},
        "gmfun": {"show": "国漫", "parse": ""},
        "gmfun4k": {"show": "国漫4K", "parse": ""},
        "funzyjp": {"show": "日配版", "parse": ""},
        "mmfun": {"show": "美漫", "parse": ""},
        "7sefun": {
            "show": "七色番",
            "parse": "https://play.7sefun.com/?url=",
        },
        "videojs": {"show": "videojs-H5播放器", "parse": ""},
        "iva": {"show": "iva-H5播放器", "parse": ""},
        "iframe": {"show": "iframe外链数据", "parse": ""},
        "link": {"show": "外链数据", "parse": ""},
        "swf": {"show": "Flash文件", "parse": ""},
        "flv": {"show": "Flv文件", "parse": ""},
        "dplayer": {"show": "七色", "parse": ""},
        "MIPFS": {"show": "M线", "parse": ""},
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
        # 部分解析域名證書過期，統一關閉校驗
        self.session.verify = False
        self.session.headers.update(
            {
                "User-Agent": self.UA,
                "Referer": self.BASE,
                "Origin": self.BASE,
            }
        )

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def search(self, keyword):
        cards = []
        url = (
            f"{self.BASE}/vodsearch/"
            f"{quote(keyword)}----------1---.html"
        )
        resp = self.session.get(url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for video in soup.select("div.video"):
            a = video.select_one("a.video-wrapper")
            if not a:
                continue
            href = a.get("href", "")
            if not href:
                continue
            img = video.select_one("img.videoimg")
            title = (img.get("alt") if img else "") or ""
            cover = (img.get("src") if img else "") or ""
            remark_el = video.select_one(".video-time")
            remark = remark_el.get_text(strip=True) if remark_el else ""
            cards.append(
                {
                    "vod_id": href,
                    "vod_name": title,
                    "vod_pic": cover,
                    "vod_remarks": remark,
                    "url": self.BASE + href,
                }
            )
        return cards

    def get_tracks(self, card):
        """
        Flatten all playlists into a single list of episodes.
        Same episode from later sources is kept as alternate URLs so
        resolve_play can fall back when the first route fails.
        Display name stays plain: 第01集
        """
        # ep_name → list of play page urls (one per source)
        by_name = {}
        order = []

        resp = self.session.get(card["url"], timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for playlist in soup.select(".vod-play-list-container"):
            for span in playlist.select("span"):
                a = span.select_one("a")
                if not a:
                    continue
                href = a.get("href", "")
                if not href:
                    continue
                name = a.get_text(strip=True)
                play_url = self.BASE + href
                if name not in by_name:
                    by_name[name] = []
                    order.append(name)
                by_name[name].append(play_url)

        tracks = []
        for name in order:
            urls = by_name[name]
            tracks.append(
                {
                    "name": name,
                    "url": urls[0],
                    # extra routes for fallback inside resolve_play
                    "alt_urls": urls[1:],
                }
            )
        return tracks

    def resolve_play(self, track):
        urls = [track["url"]] + list(track.get("alt_urls") or [])
        last_err = None

        for play_page in urls:
            try:
                return self._resolve_one(play_page)
            except Exception as e:
                last_err = e
                continue

        raise Exception(
            f"解析失敗: 所有線路均不可用 ({last_err})"
        )

    def _resolve_one(self, play_page_url):
        resp = self.session.get(play_page_url, timeout=15)
        resp.raise_for_status()
        config = self._get_player_config(resp.text)
        if not config:
            raise Exception("未找到播放器配置")

        encrypt = config.get("encrypt", 0)
        video_url = config.get("url", "")

        # encrypt 0 / 1 or already-plain m3u8
        if encrypt != 2:
            if encrypt == 1:
                video_url = unquote(video_url)
            if video_url.endswith(".m3u8") or video_url:
                return video_url
            raise Exception("未找到播放地址")

        # encrypt == 2 → base64 + unescape
        video_url = self._decode_url(video_url)
        from_name = config.get("from", "")
        jx_url = self.PLAYER_CONFIG.get(from_name, {}).get("parse", "")

        if not jx_url:
            return self._resolve_internal(video_url, from_name, config)

        if "ec.php" in jx_url:
            try:
                return self._resolve_ec(jx_url + video_url)
            except Exception:
                # external AES path failed → try site internal player
                return self._resolve_internal(video_url, from_name, config)

        # other external parsers
        try:
            return jx_url + video_url
        except Exception:
            return self._resolve_internal(video_url, from_name, config)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_player_config(html):
        """Extract player_* JSON object (player_aaaa, player_xxxx, …)."""
        match = re.search(
            r"var\s+player_[A-Za-z0-9_]*\s*=\s*(\{.*?\})\s*</script>",
            html,
            re.S,
        )
        if not match:
            match = re.search(
                r"var\s+player_[A-Za-z0-9_]*\s*=\s*(\{[\s\S]*?\})",
                html,
            )
        if not match:
            return None
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _decode_url(value):
        """Equivalent to JS: unescape(base64Decode(config.url))."""
        decoded = base64.b64decode(value).decode("utf-8", errors="ignore")
        return unquote(decoded)

    def _resolve_internal(self, video_url, from_name, config):
        """Handle empty-parse sources via site's own dp player."""
        link = config.get("link", "")
        video_id = link.rsplit("/", 1)[-1].split("-", 1)[0] if link else ""

        index_url = (
            f"{self.BASE}/addons/dp/player/index.php"
            f"?key=0&id={video_id}"
            f"&uid=0"
            f"&from={from_name}"
            f"&url={quote(video_url, safe='')}"
        )
        resp = self.session.get(index_url, timeout=15)
        resp.raise_for_status()

        match = re.search(r'href="([^"]+)";', resp.text)
        if not match:
            raise Exception("index.php 無 href")
        player_url = self.BASE + match.group(1)

        resp = self.session.get(player_url, timeout=15)
        resp.raise_for_status()
        player_html = resp.text

        cfg = self._extract_config(player_html)
        if cfg and cfg.get("url"):
            return cfg["url"]

        match = re.search(
            r'https?://[^\s"\']+\.(?:mp4|m3u8|flv)',
            player_html,
            re.I,
        )
        if match:
            return match.group(0)

        raise Exception("無法從 player 頁提取播放地址")

    def _resolve_ec(self, url):
        """lmm / ec.php AES path."""
        resp = self.session.get(url, timeout=15)
        resp.raise_for_status()

        match = re.search(
            r"ConFig\s*=\s*(\{[\s\S]*?\})\s*,\s*box",
            resp.text,
        )
        if not match:
            raise Exception("ec.php 無 ConFig")

        cfg = self._js_obj_to_dict(match.group(1))
        enc_url = cfg.get("url", "")
        uid = (cfg.get("config") or {}).get("uid", "")
        if not enc_url:
            raise Exception("ConFig 無 url")
        return self._decrypt_ec(enc_url, uid)

    @staticmethod
    def _decrypt_ec(data, uid):
        """
        AES-CBC-PKCS7
        key = UTF8('2890' + uid + 'tB959C')
        iv  = UTF8('2F131BE91247866E')
        """
        key = f"2890{uid}tB959C".encode("utf-8")
        iv = b"2F131BE91247866E"
        encrypted = base64.b64decode(data)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = unpad(cipher.decrypt(encrypted), AES.block_size)
        return decrypted.decode("utf-8", errors="ignore")

    @staticmethod
    def _extract_config(html):
        """Pull a JS `config = {...}` object from player pages."""
        match = re.search(
            r"config\s*=\s*(\{[\s\S]*?\})\s*(?:;|if\s*\()",
            html,
        )
        if not match:
            match = re.search(r"config\s*=\s*(\{[\s\S]*?\})", html)
        if not match:
            return None
        return Provider._js_obj_to_dict(match.group(1))

    @staticmethod
    def _js_obj_to_dict(raw):
        """
        Convert a simple JS object literal to a Python dict.
        Tries strict JSON first, then light cleanup for unquoted keys /
        single quotes / trailing commas.
        """
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        s = re.sub(
            r"([{,]\s*)([A-Za-z_$][\w$]*)\s*:",
            r'\1"\2":',
            raw,
        )
        s = s.replace("'", '"')
        s = re.sub(r",\s*([}\]])", r"\1", s)
        try:
            return json.loads(s)
        except json.JSONDecodeError as e:
            raise Exception(f"無法解析 JS config: {e}") from e
