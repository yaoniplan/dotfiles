"""
多來源 fzf 看片器（可擴充來源清單版）
流程：
  搜尋關鍵字 → 同時搜尋所有來源 → fzf 選影片 → fzf 選劇集 → 自動呼叫播放器

新增來源時，只要：
  1. 寫好 search / tracks / resolve_play（resolve_play 可選）
  2. 把 Source 加進 SOURCES
"""
import base64
import json
import re
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup


class Provider:
    name = "dbk"
    #name = "独播库"

    BASE = "https://www.dbku.tv"

    UA = (
        "Mozilla/5.0 "
        "(X11; Linux x86_64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/130 Safari/537.36"
    )

    def __init__(self):
        # 建立 Session，設定預設 Headers
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.UA,
            "Referer": self.BASE,
            "Origin": self.BASE,
        })

    def search(self, keyword):
        cards = []

        url = (
            f"{self.BASE}"
            "/vodsearch/"
            "-------------.html"
            f"?wd={quote(keyword)}"
        )

        resp = self.session.get(url, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")

        for a in soup.select("a.myui-vodlist__thumb"):
            href = a.get("href", "")
            if not href.startswith("/voddetail/"):
                continue

            #parent = a.parent
            #print("=== DEBUG: 卡片 HTML ===")
            #print(parent.prettify())
            #print("=== END DEBUG ===")
            cards.append({
                "vod_id": href,
                "vod_name": a.get("title", ""),
                "vod_remarks": (lambda el: el.text.strip() if el else "")(a.select_one(".pic-text.text-right")),
                "url": self.BASE + href,
            })

        return cards

    def get_tracks(self, card):
        tracks = []

        resp = self.session.get(card["url"], timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")

        for a in soup.select("#playlist1 a"):
            href = a.get("href", "")
            if not href.startswith("/vodplay/"):
                continue

            tracks.append({
                "name": a.text.strip(),
                "url": self.BASE + href,
            })

        return tracks

    def resolve_play(self, track):
        resp = self.session.get(track["url"], timeout=15)
        html = resp.text

        match = re.search(
            r"var\s+player_.*?=\s*({.*?})\s*</script>",
            html,
            re.S,
        )

        if not match:
            raise Exception("解析失敗")

        obj = json.loads(match.group(1))
        player = obj["url"]
        encrypt = obj.get("encrypt", 0)

        if encrypt == 1:
            player = requests.utils.unquote(player)
        elif encrypt == 2:
            player = base64.b64decode(player).decode("utf-8", errors="ignore")
            player = requests.utils.unquote(player)

        return player
