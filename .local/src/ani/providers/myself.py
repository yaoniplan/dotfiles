# https://github.com/JacobLinCool/Myself-BBS-API
# https://github.com/CatsSky/MyselfAnimeDownloader-cli/blob/9cbfb2183887742869d807143b547df4dafa7c72/myself.py
# https://github.com/jackykwandesign/MyselfAnimeDownloader/blob/852ef30aa903c1332824262348de6eea411d66ea/myself_tools.py
# Myself-BBS provider（无 WebSocket）
# - search / get_tracks：Worker API
# - resolve_play：直接拼 CDN URL（兼容旧 vpx 与新 hls opaque id）

import re
from urllib.parse import quote

import requests


class Provider:
    name = "bbs"
    #name = "Myself 動漫 | 日本在線動畫"

    HEADERS = {
        "origin": "https://v.myself-bbs.com",
        "referer": "https://v.myself-bbs.com/",
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux i686; rv:125.0) "
            "Gecko/20100101 Firefox/125.0"
        ),
    }

    WORKER_API = "https://myself-bbs.jacob.workers.dev"

    # CDN 主机候选（会轮换，按优先级探测）
    VPX_HOSTS = (
        "vpx05",
        "vpx07",
        "vpx08",
        "vpx09",
        "vpx10",
        "vpx06",
        "vpx04",
        "vpx03",
    )

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self._last_good_host: str | None = None

    # ---------- 内部工具 ----------

    def _get_json(self, path: str, timeout: float = 12):
        url = f"{self.WORKER_API}{path}"
        resp = self.session.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _hls_path_from_video_id(video_id: str) -> str:
        """
        新版 opaque id → CDN 相对路径
        例: AgADEBAAAhogeVQ → hls/EB/AA/Ah/AgADEBAAAhogeVQ/index.m3u8
        """
        if len(video_id) < 10:
            raise ValueError(f"video_id 太短: {video_id}")
        return (
            f"hls/{video_id[4:6]}/{video_id[6:8]}/{video_id[8:10]}/"
            f"{video_id}/index.m3u8"
        )

    def _probe_url(self, path: str) -> str:
        """
        path 为相对路径，例如:
          vpx/44252/001/720p.m3u8
          hls/EB/AA/Ah/AgADEBAAAhogeVQ/index.m3u8
        """
        candidates = []
        if self._last_good_host:
            candidates.append(self._last_good_host)
        candidates.extend(h for h in self.VPX_HOSTS if h != self._last_good_host)

        for host in candidates:
            url = f"https://{host}.myself-bbs.com/{path}"
            try:
                r = self.session.head(url, timeout=4, allow_redirects=True)
                if r.status_code == 200:
                    self._last_good_host = host
                    return url

                r = self.session.get(url, timeout=4, stream=True)
                if r.status_code == 200 and r.raw.read(16).startswith(b"#EXTM3U"):
                    self._last_good_host = host
                    r.close()
                    return url
                r.close()
            except requests.RequestException:
                continue

        raise ValueError(f"无法解析播放地址: {path}")

    # ---------- Provider 接口 ----------

    def search(self, keyword: str):
        """
        搜索动画 → 卡片列表
        Worker: /search/{keyword}
        """
        data = self._get_json(f"/search/{quote(keyword)}")
        cards = []
        for item in data.get("data", []):
            vid = str(item["id"])
            cards.append({
                "vod_id": vid,
                "vod_name": item["title"],
                "cover": item.get("image", ""),
                "vod_remarks": f"{item.get('ep', '')}集" if item.get("ep") else "",
                "url": item.get("link", ""),
            })
        return cards

    def get_tracks(self, card: dict):
        """
        获取剧集列表（按集数升序）
        Worker: /anime/{id}

        episodes 可能是两种格式:
          旧: {"第 01 話": "play/44252/001"}
          新: {"第 01 話": "AgADEBAAAhogeVQ"}
        """
        vid = card["vod_id"]
        data = self._get_json(f"/anime/{vid}").get("data", {})
        episodes = data.get("episodes", {})

        tracks = []
        for label, path in episodes.items():
            path = (path or "").strip()
            match = re.search(r"(\d+)", label)
            ep_num = int(match.group(1)) if match else 9999

            if path.startswith("play/"):
                parts = path.strip("/").split("/")
                if len(parts) >= 3:
                    tid, ep = parts[1], parts[2].zfill(3)
                else:
                    tid, ep = str(vid), f"{ep_num:03d}"
                tracks.append({
                    "name": label,
                    "url": f"https://v.myself-bbs.com/player/{path}",
                    "kind": "vpx",
                    "tid": tid,
                    "ep": ep,
                    "_sort": ep_num,
                })
            else:
                tracks.append({
                    "name": label,
                    "url": f"https://v.myself-bbs.com/player/{path}",
                    "kind": "hls",
                    "video_id": path,
                    "_sort": ep_num,
                })

        tracks.sort(key=lambda x: x["_sort"])
        for t in tracks:
            del t["_sort"]
        return tracks

    def resolve_play(self, track: dict) -> str:
        """
        解析单集播放地址 → 可直接播放的 m3u8 URL
        无 WebSocket，按 kind 拼 CDN 路径并探测可用 host。
        """
        kind = track.get("kind")

        if not kind:
            s = track.get("url", "").rstrip("/").split("/")
            last = s[-1] if s else ""
            if last.isdigit():
                kind = "vpx"
                track = {
                    **track,
                    "tid": s[-2] if len(s) >= 2 else track.get("tid"),
                    "ep": last.zfill(3),
                }
            else:
                kind = "hls"
                track = {**track, "video_id": last}

        if kind == "vpx":
            tid = track["tid"]
            ep = str(track["ep"]).zfill(3)
            return self._probe_url(f"vpx/{tid}/{ep}/720p.m3u8")

        if kind == "hls":
            video_id = track["video_id"]
            return self._probe_url(self._hls_path_from_video_id(video_id))

        raise ValueError(f"未知 track 类型: {track}")
