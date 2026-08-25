# https://github.com/YYDS678/uzVideo-extensions/blob/main/vod/js/Zhi_wooyun.js
# The speed throttling is severe (you might have to wait several seconds for it to buffer just to play one second of video)
import re
from urllib.parse import quote, urljoin, urlparse

import requests


class Provider:
    name = "woo"
    #name = "乌云影视"
    #preferred_player = "streamlink"

    BASE = "https://wooyun.tv"
    API_PROXY = BASE + "/api/proxy"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/145.0.0.0 Safari/537.36"
            ),
            "Referer": self.BASE,
        })

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------
    def _post_media_search(self, payload):
        """POST /movie/media/search (透过代理)"""
        url = f"{self.API_PROXY}?url=%2Fmovie%2Fmedia%2Fsearch"
        resp = self.session.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def _get_media_video_list(self, media_id):
        """GET /movie/media/video/list (透过代理)"""
        path = f"/movie/media/video/list?mediaId={media_id}&lineName=&resolutionCode="
        url = f"{self.API_PROXY}?url={quote(path)}"
        resp = self.session.get(url, timeout=15)
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # 核心接口
    # ------------------------------------------------------------------
    def search(self, keyword, page=1):
        """
        搜索影片。
        返回格式：[{ "vod_id": "topCode|mediaId", "vod_name": ..., "cover": ..., "vod_remarks": ... }]
        """
        if not keyword:
            return []  # 无关键词时不查询

        payload = {
            "menuCodeList": [],
            "pageIndex": str(page),
            "pageSize": 10,
            "searchKey": keyword,
            "topCode": "",
        }
        resp = self._post_media_search(payload)
        records = resp.get("data", {}).get("records", [])

        cards = []
        for item in records:
            media_type = item.get("mediaType", {}).get("code", "movie")
            vod_id = f"{media_type}|{item['id']}"
            cards.append({
                "vod_id": vod_id,
                "vod_name": item.get("title", ""),
                "cover": item.get("posterUrlS3") or item.get("posterUrl", ""),
                "vod_remarks": item.get("episodeStatus", ""),
            })
        return cards

    def get_tracks(self, card):
        """
        从卡片 vod_id 中解析出剧集列表。
        vod_id 格式： "topCode|mediaId"
        返回：[{ "name": "剧集名", "url": "wooyun://play?...token..." }]
        """
        vod_id = card["vod_id"]
        parts = vod_id.split("|", 1)
        if len(parts) != 2:
            return []
        media_id = parts[1]

        resp = self._get_media_video_list(media_id)
        seasons = resp.get("data", [])

        tracks = []
        for season in seasons:
            for ep in season.get("videoList", []):
                ep_name = ep.get("remark") or f"第{ep.get('epNo', 1)}集"
                video_id = str(ep["id"])
                token = (
                    f"wooyun://play?"
                    f"mediaId={quote(media_id)}&videoId={quote(video_id)}"
                )
                tracks.append({"name": ep_name, "url": token})
        return tracks

    def resolve_play(self, track):
        """
        将 token 或直接地址转换为最终播放 URL。
        """
        raw_url = track["url"]

        # 如果已经是普通 http(s) 地址，直接返回
        if raw_url.startswith("http://") or raw_url.startswith("https://"):
            return raw_url

        # 解析 token
        if not raw_url.startswith("wooyun://play?"):
            return raw_url  # 无法识别，原样返回

        query_str = raw_url.split("?", 1)[1]
        params = {}
        for pair in query_str.split("&"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                params[k] = requests.utils.unquote(v)
        media_id = params.get("mediaId", "")
        video_id = params.get("videoId", "")

        # 从 API 获取播放直链
        resp = self._get_media_video_list(media_id)
        seasons = resp.get("data", [])
        play_url = None
        for season in seasons:
            for ep in season.get("videoList", []):
                if str(ep["id"]) == video_id:
                    play_url = ep.get("playUrl", "")
                    break
            if play_url:
                break

        if not play_url:
            raise Exception("未找到播放地址")

        # 跟随 302 拿到最终地址
        resp = self.session.get(play_url, allow_redirects=False, timeout=10)
        if resp.status_code == 302 and "Location" in resp.headers:
            final = resp.headers["Location"]
            # 处理相对路径
            if final.startswith("/"):
                parsed = urlparse(play_url)
                final = f"{parsed.scheme}://{parsed.netloc}{final}"
            return final
        # 若无 302，尝试用返回的 url 本身
        return resp.url if resp.url != play_url else play_url
