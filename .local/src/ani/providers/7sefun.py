# https://github.com/Yswag/xptv-extensions/blob/main/js/7sefun.js
import base64
import json
import re
from urllib.parse import quote, unquote

import requests
from bs4 import BeautifulSoup
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad


class Provider:
    name = "7sf"
    #name = "七色番"
    BASE = "https://www.7sefun.top"
    UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0"
    )

    # player from → parse url (empty means internal player)
    PLAYER_CONFIG = {
        "2bdm": {"show": "七色R线", "parse": ""},
        "lmm": {
            "show": "七色A线",
            "parse": "https://dp.no3acg.com/player/ec.php?code=qw&if=1&from=lmm&url=",
        },
        "H265": {"show": "高清H265", "parse": ""},
        "CYDD1": {"show": "七色C线", "parse": ""},
        "ndx": {"show": "七色B线", "parse": ""},
        "funzy": {
            "show": "日漫高清",
            "parse": "https://nplayer.7sefun.top/player/index.php?code=qw&url=",
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
        self.session.headers.update(
            {
                "User-Agent": self.UA,
                "Referer": self.BASE,
                "Origin": self.BASE,
            }
        )

    def search(self, keyword):
        cards = []
        text = quote(keyword)
        url = f"{self.BASE}/vodsearch/{text}----------1---.html"
        resp = self.session.get(url, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        for el in soup.select("div.video"):
            a = el.select_one("a.video-wrapper")
            if not a:
                continue
            href = a.get("href", "")
            img = el.select_one("img.videoimg")
            title = (img.get("alt") if img else "") or ""
            cover = (img.get("src") if img else "") or ""
            sub = el.select_one(".video-time")
            remarks = sub.get_text(strip=True) if sub else ""
            cards.append(
                {
                    "vod_id": href,
                    "vod_name": title,
                    "vod_remarks": remarks,
                    "url": self.BASE + href,
                }
            )
        return cards

    def get_tracks(self, card):
        """
        Returns list of {name, url} for every playable episode across all
        source groups.
        """
        tracks = []
        resp = self.session.get(card["url"], timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")

        for container in soup.select(".vod-play-list-container"):
            for span in container.select("span"):
                a = span.select_one("a")
                if not a:
                    continue
                href = a.get("href", "")
                name = a.get_text(strip=True)
                tracks.append(
                    {
                        "name": name,
                        "url": self.BASE + href,
                    }
                )
        return tracks

    def resolve_play(self, track):
        resp = self.session.get(track["url"], timeout=15)
        html = resp.text

        # extract player_aaaa config
        m = re.search(
            r"var\s+player_aaaa\s*=\s*({.*?})\s*</script>",
            html,
            re.S,
        )
        if not m:
            # fallback: script containing player_aaaa
            soup = BeautifulSoup(html, "html.parser")
            for script in soup.find_all("script"):
                txt = script.string or ""
                if "player_aaaa" in txt:
                    m = re.search(r"player_aaaa\s*=\s*({.*?})\s*;?\s*$", txt, re.S)
                    if m:
                        break
            if not m:
                raise Exception("解析失敗: 找不到 player_aaaa")

        config = json.loads(m.group(1))
        encrypt = config.get("encrypt", 0)
        video_url = config.get("url", "")
        from_ = config.get("from", "")
        link = config.get("link", "")

        if encrypt == 2:
            # base64 + unescape
            video_url = unquote(
                base64.b64decode(video_url).decode("utf-8", errors="ignore")
            )
            # extract id from link path
            id_ = ""
            if link:
                parts = link.rstrip("/").split("/")
                last = parts[-1] if parts else ""
                id_ = last.split("-")[0] if last else ""

            jx_url = ""
            if from_ in self.PLAYER_CONFIG:
                jx_url = self.PLAYER_CONFIG[from_].get("parse") or ""

            if not jx_url:
                # internal player path
                index_url = (
                    f"{self.BASE}/addons/dp/player/index.php"
                    f"?key=0&id={id_}&uid=0&from={from_}&url={video_url}"
                )
                r = self.session.get(index_url, timeout=15)
                href_m = re.search(r'href="(.+?)";', r.text)
                if not href_m:
                    raise Exception("解析失敗: index.php 無 href")
                player_url = self.BASE + href_m.group(1)

                if "art.php" in player_url:
                    art = self.session.get(player_url, timeout=15).text
                    cfg_m = re.search(
                        r"config\s*=\s*({[\s\S]*?})\s*if\s*\(",
                        art,
                    )
                    if not cfg_m:
                        raise Exception("解析失敗: art.php 無 config")
                    # safe-ish eval of the JS object literal
                    cfg = self._js_obj_to_dict(cfg_m.group(1))
                    return cfg.get("url", "")
                else:
                    # dp.php or other
                    player_data = self.session.get(player_url, timeout=15).text
                    cfg_m = re.search(
                        r"config\s*=\s*(\{[\s\S]*?\})\s*(?:;|if\s*\()",
                        player_data,
                    )
                    if cfg_m:
                        cfg = self._js_obj_to_dict(cfg_m.group(1))
                        return cfg.get("url", "")
                    # fallback direct media url
                    video_m = re.search(
                        r'https?://[^\s"\']+\.(?:mp4|m3u8|flv)',
                        player_data,
                    )
                    if video_m:
                        return video_m.group(0)
                    raise Exception("解析失敗: 無法從 player 頁提取播放地址")

            elif "ec.php" in jx_url:
                jx_data = self.session.get(jx_url + video_url, timeout=15).text
                cfg_m = re.search(
                    r"ConFig\s*=\s*({[\s\S]*?})\s*,\s*box",
                    jx_data,
                )
                if not cfg_m:
                    raise Exception("解析失敗: ec.php 無 ConFig")
                ConFig = self._js_obj_to_dict(cfg_m.group(1))
                enc_url = ConFig.get("url", "")
                uid = (ConFig.get("config") or {}).get("uid", "")
                return self._aes_decrypt(enc_url, uid)

            else:
                # other external parse urls – just append and hope for m3u8/mp4
                # (most of these return a player page; caller may need extra work)
                return jx_url + video_url

        # plain m3u8
        if video_url.endswith(".m3u8"):
            return video_url

        # encrypt 0/1 fallbacks
        if encrypt == 1:
            return unquote(video_url)
        return video_url

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _aes_decrypt(ciphertext_b64: str, uid: str) -> str:
        """
        AES-CBC decrypt used by the lmm / ec.php player.
        Key:  Utf8("2890" + uid + "tB959C")
        IV:   Utf8("2F131BE91247866E")
        """
        key = ("2890" + str(uid) + "tB959C").encode("utf-8")
        iv = b"2F131BE91247866E"
        cipher = AES.new(key, AES.MODE_CBC, iv)
        raw = base64.b64decode(ciphertext_b64)
        decrypted = unpad(cipher.decrypt(raw), AES.block_size)
        return decrypted.decode("utf-8", errors="ignore")

    @staticmethod
    def _js_obj_to_dict(js_obj: str) -> dict:
        """
        Very lightweight conversion of a simple JS object literal to Python dict.
        Handles the common cases seen on this site (quoted/unquoted keys, nested
        objects, strings, numbers). Falls back to json.loads after light cleanup.
        """
        # try direct json first (already valid)
        try:
            return json.loads(js_obj)
        except Exception:
            pass

        # replace unquoted keys:  key: → "key":
        s = re.sub(
            r"([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:",
            r'\1"\2":',
            js_obj,
        )
        # single quotes → double
        s = s.replace("'", '"')
        # trailing commas
        s = re.sub(r",\s*([}\]])", r"\1", s)
        try:
            return json.loads(s)
        except Exception as e:
            raise Exception(f"無法解析 JS config: {e}") from e
