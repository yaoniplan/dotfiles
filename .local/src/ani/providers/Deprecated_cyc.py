# https://github.com/AniBakaBaka/AniBaka/blob/b2b0fcc9877646220b220554ff8df6971b67db71/assets/rules/cycani.json#L5
# The community is no longer maintaining it (for example, need to log in to get the video URL.)
import re
from urllib.parse import urljoin, quote

import requests


class Provider:
    name = "cyc"
    #name = "次元城动画"

    BASE = "https://www.cycani.org/"
    SEARCH_API = "https://www.cycani.org/api/videos/search"
    VIDEO_API = "https://www.cycani.org/api/videos/{video_id}"
    SECTIONS_API = "https://www.cycani.org/api/videos/{video_id}/sections"
    PLAY_URL_API = "https://www.cycani.org/api/sections/{section_id}/play-url"

    UA = (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0.0.0 Safari/537.36"
    )

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.UA,
            "Referer": self.BASE,
            "Origin": self.BASE,
            "Accept": "application/json",
            "x-app-name": "cyc_web",
            "x-app-version": "cycweb",
        })
        self.timeout = 15

    def search(self, keyword: str):
        """
        搜索关键词，返回卡片列表
        """
        params = {
            "q": keyword,
            "page": 1,
            "page_size": 24,
        }
        resp = self.session.get(self.SEARCH_API, params=params, timeout=self.timeout)
        resp.raise_for_status()

        data = resp.json()
        cards = []

        if data.get("code") != 0:
            return cards

        video_list = data.get("data", {}).get("list", [])
        for item in video_list:
            video_id = item.get("video_id")
            title = item.get("title", "")
            cover_url = item.get("cover_url", "")
            remarks = item.get("remarks", "")

            if not video_id or not title:
                continue

            detail_url = urljoin(self.BASE, f"/voddetail/{video_id}")
            cover = cover_url if cover_url else ""

            card = {
                "vod_id": str(video_id),
                "vod_name": title,
                "vod_remarks": remarks,
                "url": detail_url,
                "cover": cover,
            }
            cards.append(card)

        return cards

    def get_tracks(self, card: dict):
        """
        获取剧集列表，只取第一个播放线路，显示仅集数名称
        """
        video_id = card.get("vod_id")
        if not video_id:
            return []

        # 1. 获取视频详情，得到 play_from 列表
        try:
            detail_resp = self.session.get(
                self.VIDEO_API.format(video_id=video_id),
                timeout=self.timeout
            )
            detail_resp.raise_for_status()
            detail_data = detail_resp.json()
            if detail_data.get("code") != 0:
                return []
            play_from = detail_data.get("data", {}).get("play_from", [])
            if not play_from:
                return []
        except Exception:
            return []

        # 只使用第一个线路
        source = play_from[0]
        code = source.get("code")
        if not code:
            return []

        # 2. 获取该线路的剧集
        try:
            sections_resp = self.session.get(
                self.SECTIONS_API.format(video_id=video_id),
                params={
                    "player_code": code,
                    "page": 1,
                    "page_size": 48,
                },
                timeout=self.timeout
            )
            sections_resp.raise_for_status()
            sections_data = sections_resp.json()
            if sections_data.get("code") != 0:
                return []
            sections = sections_data.get("data", {}).get("list", [])
        except Exception:
            return []

        tracks = []
        for section in sections:
            section_id = section.get("id")
            section_title = section.get("title", f"第{section_id}集")
            if not section_id:
                continue

            play_url = urljoin(self.BASE, f"/vodplay/{section_id}")
            tracks.append({
                "name": section_title,          # 仅显示集数
                "url": play_url,
            })

        return tracks

    def resolve_play(self, track: dict):
        """
        通过API获取实际的视频流地址
        """
        play_url = track["url"]
        match = re.search(r'/vodplay/(\d+)', play_url)
        if not match:
            raise Exception("无法从播放页URL中提取section_id")
        section_id = match.group(1)

        api_url = self.PLAY_URL_API.format(section_id=section_id)
        resp = self.session.get(api_url, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise Exception(f"API返回错误: {data.get('msg')}")

        video_url = data.get("data", {}).get("url")
        if not video_url:
            raise Exception("未找到视频地址")

        return video_url
