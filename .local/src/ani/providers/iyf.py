import hashlib
import json
import time
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup


class Provider:
    name = "iyf"
    #name = "爱壹帆"

    SITE = "https://m10.iyf.tv"

    UA = (
        "Mozilla/5.0 "
        "(X11; Linux x86_64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/123 Safari/537.36"
    )

    def __init__(self):
        self.public_key = None
        self.private_key = None

        # 建立 Session，設定預設 User‑Agent
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.UA
        })

    def _update_keys(self):
        """從首頁取得加密金鑰，只在第一次需要時執行"""
        if self.public_key:
            return

        resp = self.session.get(
            "https://www.iyf.tv",
            timeout=15
        )
        html = resp.text

        start = html.find("var injectJson =")
        if start < 0:
            raise Exception("Key not found")

        end = html.find(";", start)
        data = html[start:end]
        data = data.replace("var injectJson =", "").strip()

        obj = json.loads(data)
        pconfig = obj["config"][0]["pConfig"]
        self.public_key = pconfig["publicKey"]
        self.private_key = pconfig["privateKey"]

    def _sign(self, query):
        """動態簽名，使用私鑰的一部分"""
        self._update_keys()

        priv = self.private_key[
            int(time.time() * 1000) % len(self.private_key)
        ]
        raw = self.public_key + "&" + query.lower() + "&" + priv
        return hashlib.md5(raw.encode()).hexdigest()

    def search(self, keyword):
        self._update_keys()

        cards = []
        url = (
            "https://rankv21.iyf.tv"
            "/v3/list/briefsearch"
            f"?tags={quote(keyword)}"
            "&orderby=4"
            "&page=1"
            "&size=10"
        )

        resp = self.session.get(url, timeout=15)
        data = resp.json()
        #print(json.dumps(data, indent=2, ensure_ascii=False))
        result = data["data"]["info"][0]["result"]

        for item in result:
            cards.append({
                "vod_id": item["contxt"],
                "vod_name": item["title"],
                "vod_remarks": item.get("lastName", ""),
                "key": item["contxt"],
            })
        return cards

    def get_tracks(self, card):
        key = card["key"]
        query = (
            "cinema=1"
            f"&vid={key}"
            "&lsk=1"
            "&taxis=0"
            "&cid=0,1,4,133"
        )
        sign = self._sign(query)

        url = (
            f"{self.SITE}"
            "/v3/video/languagesplaylist?"
            f"{query}"
            f"&vv={sign}"
            f"&pub={self.public_key}"
        )

        resp = self.session.get(url, timeout=15)
        data = resp.json()
        playlist = data["data"]["info"][0]["playList"]

        tracks = []
        for item in playlist:
            tracks.append({
                "name": item["name"],
                "key": item["key"],
            })
        return tracks

    def resolve_play(self, track):
        key = track["key"]
        query = (
            "cinema=1"
            f"&id={key}"
            "&a=0"
            "&lang=none"
            "&usersign=1"
            "&region=GL."
            "&device=1"
            "&isMasterSupport=1"
        )
        sign = self._sign(query)

        url = (
            f"{self.SITE}"
            "/v3/video/play?"
            f"{query}"
            f"&vv={sign}"
            f"&pub={self.public_key}"
        )

        resp = self.session.get(url, timeout=15)
        data = resp.json()
        flvs = data["data"]["info"][0]["flvPathList"]

        for item in flvs:
            if item.get("isHls"):
                return item["result"] + f"?pub={self.public_key}"

        raise Exception("No stream")
