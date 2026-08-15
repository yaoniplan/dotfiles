import hashlib
import time
from urllib.parse import quote

import requests


class Provider:
    name = "ole"
    #name = "欧乐"

    SITE = "https://api.olelive.com"

    UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0"
    )

    def __init__(self):
        # 重用 Session
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.UA})

    # ---------- 完整簽名演算法（與舊版 main.py 一致）----------
    def _digit_bin(self, ch):
        """把字元轉成二進位表示（各 bit 用空格分隔）"""
        parts = []
        for i, c in enumerate(ch):
            if i != 0:
                parts.append(" ")
            parts.append(bin(ord(c))[2:])
        return "".join(parts)

    def _signature(self, timestamp_str: str) -> str:
        r = [[], [], [], []]
        for ch in timestamp_str:
            b = self._digit_bin(ch)
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

    def _sign(self) -> str:
        return self._signature(str(int(time.time())))
    # --------------------------------------------------------

    def search(self, keyword):
        cards = []

        # 使用舊版 URL 格式（路徑參數）
        url = (
            f"{self.SITE}"
            f"/v1/pub/index/search/{quote(keyword)}"
            f"/vod/0/1/48"
            f"?_vv={self._sign()}"
        )

        resp = self.session.get(url, timeout=15)
        data = resp.json()

        blocks = data.get("data", {}).get("data", [])
        if not isinstance(blocks, list):
            return cards

        vod = None
        for item in blocks:
            if isinstance(item, dict) and item.get("type") == "vod":
                vod = item
                break

        if not vod:
            return cards

        vod_list = vod.get("list")
        if not isinstance(vod_list, list):
            return cards

        for item in vod_list:
            if item.get("vip"):
                continue
            cards.append({
                "vod_id": str(item["id"]),
                "vod_name": item["name"],
                "vod_remarks": item.get("remarks", ""),
            })

        return cards

    def get_tracks(self, card):
        vod_id = card["vod_id"]

        url = (
            f"{self.SITE}"
            "/v1/pub/vod/detail/"
            f"{vod_id}"
            "/true"
            f"?_vv={self._sign()}"
        )

        resp = self.session.get(url, timeout=15)
        data = resp.json()

        urls = data.get("data", {}).get("urls", [])

        tracks = []
        for item in urls:
            tracks.append({
                "name": item["title"],
                "url": item["url"],
            })

        return tracks

    def resolve_play(self, track):
        return track["url"]
