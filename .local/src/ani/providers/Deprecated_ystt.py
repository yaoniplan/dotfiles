# https://github.com/fangkuia/XPTV/blob/main/js/ystt.js
# Because there are advertisements.

import urllib.parse
import requests
from bs4 import BeautifulSoup


class Provider:
    name = "ystt"
    #name = "影视天堂"
    BASE_URL = "https://ysttv.com"

    # Mobile User-Agent from the working JS version
    UA = (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 18_2_1 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2.1 Mobile/15E148 Safari/604.1"
    )

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.UA,
        })

    def search(self, keyword: str, page: int = 1) -> list:
        """搜索"""
        kw = urllib.parse.quote(keyword)
        # 默认搜索类型为 1（电影），如需其他类型可扩展
        url = f"{self.BASE_URL}/search/index/type/1/keyword/{kw}/page/{page}"
        resp = self.session.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        cards = []
        for item in soup.select("main ul.grid > li"):
            a = item.find("a")
            img = item.find("img")
            if not a or not img:
                continue
            href = a.get("href", "")
            title = a.get("title", "")
            pic = img.get("data-src") or img.get("src", "")
            cards.append({
                "vod_id": href,
                "vod_name": title,
                "cover": pic,
                "vod_remarks": "",   # 搜索页无评分/集数，详情页会补充
                "url": self.BASE_URL + href,   # 方便 get_tracks 直接使用
            })
        return cards

    def get_tracks(self, card: dict) -> list:
        """获取剧集列表（扁平化，因为通常只有一个分组）"""
        detail_url = card.get("url")
        if not detail_url:
            # 兼容旧版 card 格式
            detail_url = self.BASE_URL + card.get("vod_id", "")
        resp = self.session.get(detail_url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        tracks = []
        for li in soup.select(".overflow-auto > ul > li"):
            a = li.find("a")
            if not a:
                continue
            name = a.get_text(strip=True)
            href = a.get("href", "")
            tracks.append({
                "name": name,
                "url": self.BASE_URL + href,   # 播放页完整地址
            })
        return tracks

    def resolve_play(self, track: dict) -> str:
        """解析播放页，返回 m3u8 地址"""
        play_url = track.get("url", "")
        if not play_url:
            return ""
        resp = self.session.get(play_url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        mse = soup.select_one("#mse")
        if mse and mse.get("data-url"):
            return mse["data-url"]
        return ""
