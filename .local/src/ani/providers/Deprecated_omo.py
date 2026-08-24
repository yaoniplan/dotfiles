# https://github.com/frxz751113/IPTVzb1/blob/main/lib/OmoFun%5B%E6%BC%AB%5D.js
# Because there are advertisements.
import base64
import json
import re
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup


class Provider:
    name = "omofun"
    #name = "OmoFun动漫"

    BASE = "https://www.omofun.icu"

    UA = (
        "Mozilla/5.0 "
        "(X11; Linux x86_64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/130 Safari/537.36"
    )

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.UA,
            "Referer": self.BASE,
            "Origin": self.BASE,
        })

    def search(self, keyword):
        cards = []

        url = f"{self.BASE}/vod/search/wd/{quote(keyword)}.html"

        resp = self.session.get(url, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")

        # 新增多種可能的卡片選擇器（適配當前網站）
        selectors = [
            ".module-card-item",           # 舊版
            ".myui-vodlist__box",          # 常見模板
            ".searchlist-item",            # 搜尋結果常見
            "li.col-md-6",                 # 另一種常見排版
            ".module-list .col",           # 另一種可能
        ]

        for sel in selectors:
            items = soup.select(sel)
            if items:
                print(f"🔍 使用選擇器: {sel} 找到 {len(items)} 個項目")
                break

        for item in items:
            a = item.select_one("a")
            if not a:
                continue

            title_tag = a.select_one(".module-card-item-title") or a.select_one("h4") or a
            title = title_tag.text.strip() if title_tag else a.get("title", "").strip()

            img = item.select_one("img")
            img_url = (img.get("data-original") or img.get("src") or "") if img else ""

            remarks = item.select_one(".module-item-note, .pic-text, .text-right, .remarks")
            remarks_text = remarks.text.strip() if remarks else ""

            href = a.get("href", "")
            if href and title:
                full_url = self.BASE + href if not href.startswith("http") else href
                cards.append({
                    "vod_id": href,
                    "vod_name": title,
                    "vod_remarks": remarks_text,
                    "url": full_url,
                })

        print(f"✅ search 返回 {len(cards)} 個結果")
        return cards

    def get_tracks(self, card):
        tracks = []

        resp = self.session.get(card["url"], timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")

        # 多種播放列表選擇器
        for a in soup.select(".sort-list a, a[href*='/vod/play/'], .playlist a"):
            href = a.get("href", "")
            if href and "/vod/play/" in href:
                tracks.append({
                    "name": a.text.strip(),
                    "url": self.BASE + href if not href.startswith("http") else href,
                })

        print(f"✅ get_tracks 返回 {len(tracks)} 集")
        return tracks

    def resolve_play(self, track):
        resp = self.session.get(track["url"], timeout=15)
        html = resp.text

        # 加強版匹配
        patterns = [
            r"r player_.*?=\s*(\{.*?\})\s*</script>",
            r"player_.*?=\s*(\{.*?\})\s*</script>",
            r"var\s+player_.*?=\s*(\{.*?\})",
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.S)
            if match:
                break

        if not match:
            raise Exception("無法找到播放器配置")

        try:
            obj = json.loads(match.group(1))
            url = obj.get("url", "")

            encrypt = obj.get("encrypt", 0)

            if encrypt == 1:
                url = requests.utils.unquote(url)
            elif encrypt == 2:
                decoded = base64.b64decode(url + "==").decode("utf-8", errors="ignore")  # 補齊 base64
                url = requests.utils.unquote(decoded)

            if url:
                print(f"✅ 解析到真實連結: {url[:100]}...")
                return url
            else:
                raise Exception("解析出的連結為空")

        except Exception as e:
            raise Exception(f"解析播放連結失敗: {e}")
