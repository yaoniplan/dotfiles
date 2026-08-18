# https://github.com/fangkuia/XPTV/blob/main/js/age.js
# The community is no longer maintaining it (for example, the latest encryption/decryption methods have not been updated.)
import re
from urllib.parse import quote

import requests


class Provider:
    name = "age"
    #name = "AGE动漫"

    SITE = "https://www.agedm.io"
    API = "https://api.agedm.io"

    UA = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0.0.0 Safari/537.36"
    )

    HEADERS = {
        "Referer": "https://www.agedm.io/",
        "Origin": "https://www.agedm.io/",
        "User-Agent": UA,
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def _get_json(self, url, timeout=15):
        resp = self.session.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.json()

    def _pick_best_playlist(self, playlists):
        """
        選集數最多的播放源。
        """
        return max(playlists, key=len, default=[])

    def search(self, keyword):
        cards = []

        url = (
            f"{self.API}/v2/search"
            f"?query={quote(keyword)}"
            f"&page=1"
        )

        try:
            data = self._get_json(url)
        except Exception:
            return cards

        videos = (
            data.get("data", {})
            .get("videos", [])
        )

        for item in videos:
            vid = item.get("id")
            if not vid:
                continue

            cards.append(
                {
                    "vod_id": str(vid),
                    "vod_name": item.get("name", ""),
                    "vod_pic": item.get("cover", ""),
                    "vod_remarks": item.get("uptodate", ""),
                    "ext": {
                        "url": f"{self.API}/v2/detail/{vid}",
                    },
                }
            )

        return cards

    def get_tracks(self, card):
        detail_url = card.get("ext", {}).get("url")
        if not detail_url:
            return []

        try:
            data = self._get_json(detail_url)
        except Exception:
            return []

        video = data.get("video", {})
        playlists = video.get("playlists", {})

        player_jx = data.get("player_jx", {})

        vip_prefix = player_jx.get("vip", "")
        zj_prefix = player_jx.get("zj", "")

        player_vip = data.get("player_vip", "")

        if isinstance(player_vip, str):
            player_vip = {
                x.strip()
                for x in player_vip.split(",")
                if x.strip()
            }
        elif isinstance(player_vip, list):
            player_vip = set(player_vip)
        else:
            player_vip = set()

        all_playlists = []

        for source_name, episodes in playlists.items():
            if not isinstance(episodes, list):
                continue

            current_playlist = []

            for ep in episodes:
                if not isinstance(ep, list):
                    continue

                if len(ep) != 2:
                    continue

                ep_name, ep_path = ep

                if source_name in player_vip:
                    play_url = f"{vip_prefix}{ep_path}"
                else:
                    play_url = f"{zj_prefix}{ep_path}"

                current_playlist.append(
                    {
                        "name": ep_name,
                        "url": play_url,
                    }
                )

            if current_playlist:
                all_playlists.append(current_playlist)

        return self._pick_best_playlist(all_playlists)

    def resolve_play(self, track):
        url = track.get("url")
        if not url:
            return ""

        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
        except Exception:
            return ""

        text = resp.text

        match = re.search(
            r"Vurl\s*=\s*['\"](.+?)['\"]",
            text,
        )

        if match:
            return match.group(1)

        match = re.search(
            r'url\s*:\s*["\'](.+?)["\']',
            text,
        )

        if match:
            return match.group(1)

        return ""
