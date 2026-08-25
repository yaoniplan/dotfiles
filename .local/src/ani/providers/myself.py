# https://github.com/JacobLinCool/Myself-BBS-API
# https://github.com/CatsSky/MyselfAnimeDownloader-cli/blob/9cbfb2183887742869d807143b547df4dafa7c72/myself.py
# https://github.com/jackykwandesign/MyselfAnimeDownloader/blob/852ef30aa903c1332824262348de6eea411d66ea/myself_tools.py

import json
import re
import ssl
from urllib.parse import quote

import requests
import websocket
from contextlib import closing
from bs4 import BeautifulSoup  # 保留以备 fallback


# ---------- 全局配置（与原脚本保持一致） ----------
HEADERS = {
    "origin": "https://v.myself-bbs.com",
    "referer": "https://v.myself-bbs.com/",
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux i686; rv:125.0) "
        "Gecko/20100101 Firefox/125.0"
    ),
}

WS_OPT = {
    "header": HEADERS,
    "url": "wss://v.myself-bbs.com/ws",
    "host": "v.myself-bbs.com",
    "origin": "https://v.myself-bbs.com",
}


class Provider:
    name = "bbs"
    #name = "Myself 動漫 | 日本在線動畫"

    # Worker API 基础地址（社区维护的代理）
    WORKER_API = "https://myself-bbs.jacob.workers.dev"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    # ---------- 私有方法：WebSocket 获取 m3u8 ----------
    def _ws_get_host_and_m3u8_url(self, tid: str, vid: str, video_id: str):
        """
        通过 WebSocket 获取视频 host 和 m3u8 地址
        原脚本 ws_get_host_and_m3u8_url 的移植
        """
        try:
            with closing(websocket.create_connection(**WS_OPT)) as ws:
                ws.send(json.dumps({"tid": tid, "vid": vid, "id": video_id}))
                recv = ws.recv()
                res = json.loads(recv)
                m3u8_url = f"https:{res['video']}"
                # 返回 (host, m3u8_url)，这里只返回 m3u8_url
                return m3u8_url
        except ssl.SSLCertVerificationError:
            # 某些环境 SSL 证书问题，忽略验证重试
            WS_OPT["sslopt"] = {"cert_reqs": ssl.CERT_NONE}
            return self._ws_get_host_and_m3u8_url(tid, vid, video_id)
        except Exception as e:
            raise ValueError(f"WebSocket 获取播放地址失败: {e}")

    def _parse_episode_url(self, url: str) -> str:
        """
        从播放页 URL 提取参数，调用 WebSocket 获取 m3u8
        原脚本 parse_episode_url 的逻辑
        """
        s = url.split("/")
        # URL 格式示例: https://v.myself-bbs.com/player/play/44252/001
        # 或 https://v.myself-bbs.com/vpx/...
        if s[-1].isdigit():
            tid, vid, video_id = s[-2], s[-1], ""
        else:
            tid, vid, video_id = "", "", s[-1]
        return self._ws_get_host_and_m3u8_url(tid, vid, video_id)

    # ---------- Provider 接口 ----------

    def search(self, keyword: str):
        """
        搜索动画，返回卡片列表
        使用 Worker API: /search/{keyword}
        """
        url = f"{self.WORKER_API}/search/{quote(keyword)}"
        resp = self.session.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        cards = []
        for item in data.get("data", []):
            vid = str(item["id"])
            cards.append({
                "vod_id": vid,
                "vod_name": item["title"],
                "cover": item.get("image", ""),
                "vod_remarks": f"{item.get('ep', '')}集" if item.get("ep") else "",
                "url": item.get("link", ""),  # 备用链接
            })
        return cards

    def get_tracks(self, card: dict):
        """
        获取剧集列表（按集数升序）
        使用 Worker API: /anime/{id}
        """
        vid = card["vod_id"]
        url = f"{self.WORKER_API}/anime/{vid}"
        resp = self.session.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json().get("data", {})

        episodes = data.get("episodes", {})
        tracks = []

        for label, path in episodes.items():
            # path 格式: "play/44252/001"
            # 构造完整播放 URL: https://v.myself-bbs.com/player/{path}
            play_url = f"https://v.myself-bbs.com/player/{path}"
            # 提取集数数字用于排序
            match = re.search(r"(\d+)", label)
            ep_num = int(match.group(1)) if match else 9999

            tracks.append({
                "name": label,          # 如 "第 01 話"
                "url": play_url,
                "_sort": ep_num,
            })

        # 按集数升序排列
        tracks.sort(key=lambda x: x["_sort"])
        for t in tracks:
            del t["_sort"]
        return tracks

    def resolve_play(self, track: dict) -> str:
        """
        解析单集播放地址，返回 m3u8 URL
        通过 WebSocket 获取真实视频地址
        """
        play_url = track["url"]
        return self._parse_episode_url(play_url)
