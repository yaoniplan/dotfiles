# https://github.com/fangkuia/XPTV/blob/main/js/libvio.js
# The anime library isn't very comprehensive. (e.g. Berserk)
# You will need to additionally register for a Chinese cloud storage service and pay a fee to lift the speed restrictions.
import re
import json
import time
import base64
import urllib.parse
import requests
from bs4 import BeautifulSoup


class Provider:
    name = "LIBVIO"
    BASE_URL = "https://www.libvios.com"
    UA = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    )

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Referer": self.BASE_URL + "/",
            "Origin": self.BASE_URL,
            "User-Agent": self.UA,
        })

    # ---------- 对外接口 ----------
    def search(self, keyword: str, page: int = 1):
        """搜索影片"""
        if page > 1:
            return []   # libvio 搜索结果只有一页
        text = urllib.parse.quote(keyword)
        url = f"{self.BASE_URL}/search/-------------.html?wd={text}&submit="
        resp = self.session.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        cards = []
        seen = set()
        for a in soup.select("a.stui-vodlist__thumb"):
            path = a.get("href")
            if path and path.startswith("/detail/") and path not in seen:
                seen.add(path)
                cards.append({
                    "vod_id": path,
                    "vod_name": a.get("title", ""),
                    "cover": a.get("data-original", ""),
                    "vod_remarks": (
                        a.select_one(".text-right").get_text(strip=True)
                        if a.select_one(".text-right") else ""
                    ),
                    # 详情页 URL，供 get_tracks 使用
                    "url": self.BASE_URL + path,
                })
        return cards

    def get_tracks(self, card: dict):
        """根据卡片获取所有播放线路（扁平化为单个列表）"""
        detail_url = card.get("url") or card.get("ext", {}).get("url")
        if not detail_url:
            return []
        resp = self.session.get(detail_url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        groups = []

        # 方式1：从 playlist-panel 抓取播放列表
        for panel in soup.select("div.playlist-panel"):
            title_el = panel.select_one(".panel-head h3")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title or "猜你喜欢" in title or "下载" in title:
                continue
            tracks = []
            for li in panel.select(".stui-content__playlist li"):
                a = li.find("a")
                if a:
                    tracks.append({
                        "name": a.get_text(strip=True),
                        "url": self.BASE_URL + a.get("href"),
                    })
            if tracks:
                groups.append({"name": title, "tracks": tracks})

        # 方式2：没有 playlist-panel 时，使用“立即播放”按钮
        if not groups:
            play_btn = soup.select_one('a[href^="/play/"]')
            if play_btn:
                groups.append({
                    "name": "立即播放",
                    "tracks": [{
                        "name": "第1集",
                        "url": self.BASE_URL + play_btn["href"],
                    }],
                })

        # 网盘下载
        for panel in soup.select("div.netdisk-panel, div.playlist-panel.netdisk-panel"):
            title_el = panel.select_one(".panel-head h3")
            if not title_el or "下载" not in title_el.get_text(strip=True):
                continue
            title = title_el.get_text(strip=True)
            for a in panel.select(".netdisk-list a"):
                name_el = a.select_one(".netdisk-name")
                name = name_el.get_text(strip=True) if name_el else "合集"
                href = a.get("href")
                if href:
                    groups.append({
                        "name": title,
                        "tracks": [{"name": name, "pan": href}],
                    })

        # 将所有分组扁平化为一个 track 列表
        tracks_flat = []
        multiple_groups = len(groups) > 1
        for group in groups:
            group_title = group["name"]
            for t in group["tracks"]:
                if "pan" in t:
                    tracks_flat.append({
                        "name": f"{group_title} - {t['name']}" if multiple_groups else t["name"],
                        "pan": t["pan"],
                    })
                else:
                    tracks_flat.append({
                        "name": f"{group_title} - {t['name']}" if multiple_groups else t["name"],
                        "url": t["url"],
                    })
        return tracks_flat

    def resolve_play(self, track: dict) -> str:
        """解析播放页，返回最终的媒体 URL"""
        # 网盘直链直接返回
        if "pan" in track:
            return track["pan"]

        play_url = track.get("url")
        if not play_url:
            return ""

        try:
            resp = self.session.get(play_url, timeout=10)
            resp.raise_for_status()
            page_text = resp.text
        except Exception as e:
            print(f"Error fetching {play_url}: {e}")
            return ""

        # 提取 player_* 变量
        match = re.search(r'var player_.*?=(.*?)<', page_text)
        if not match:
            return ""
        try:
            obj = json.loads(match.group(1))
        except json.JSONDecodeError:
            return ""

        player_url = obj.get("url", "")
        encrypt = obj.get("encrypt", "0")

        # 解密
        if encrypt == "1":
            player_url = urllib.parse.unquote(player_url)
        elif encrypt == "2":
            player_url = urllib.parse.unquote(
                base64.b64decode(player_url).decode("utf-8")
            )
        elif encrypt == "3":
            player_url = base64.b64decode(player_url).decode("utf-8")

        if player_url.startswith("http"):
            return player_url

        # 二次解析（非直链）
        next_link = obj.get("link_next", "")
        vid = obj.get("id", "")
        ty_url = (
            f"{self.BASE_URL}/vid/ty4.php"
            f"?url={player_url}&next={next_link}&id={vid}&nid=1"
        )

        try:
            ty_resp = self.session.get(ty_url, timeout=10)
            ty_resp.raise_for_status()
            ty_text = ty_resp.text
        except Exception as e:
            print(f"Error fetching {ty_url}: {e}")
            return ""

        # 解析 PARSE_URL
        parse_url_match = re.search(
            r"var\s+PARSE_URL\s*=\s*['\"]([^'\"]+)['\"]", ty_text
        )
        if not parse_url_match:
            return ""
        parse_url = self.BASE_URL + parse_url_match.group(1)

        # 解析 PARSE_BODY
        body_url_match = re.search(
            r"var\s+PARSE_BODY\s*=\s*JSON\.stringify\(\s*\{url:\s*['\"]([^'\"]+)['\"]\s*\}\s*\)",
            ty_text,
        )
        if not body_url_match:
            return ""
        post_body = json.dumps({"url": body_url_match.group(1)})

        # 最多重试 6 次
        headers = {
            "Referer": ty_url,
            "Origin": self.BASE_URL,
            "User-Agent": self.UA,
            "Content-Type": "application/json",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "sec-fetch-dest": "empty",
        }
        for attempt in range(6):
            try:
                parse_resp = self.session.post(
                    parse_url, data=post_body, headers=headers, timeout=10
                )
                parse_resp.raise_for_status()
                parsed = parse_resp.json()
                if parsed.get("url"):
                    return parsed["url"]
                if parsed.get("fatal") is True:
                    break
            except Exception as e:
                print(f"parse attempt {attempt+1} error: {e}")
            time.sleep(2)

        return ""
