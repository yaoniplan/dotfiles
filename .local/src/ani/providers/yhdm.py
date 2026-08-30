# https://github.com/yaoniplan/dotfiles/blob/master/.config/yt-dlp/plugins/yhdm/yt_dlp_plugins/extractor/yhdm.py
# Not recommended for streaming (Because it has ads)
# Only use it to check the release year (Because the search is super fast)
import re
import json
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup


class Provider:
    name = "yhdm"
    #name = "樱花动漫"

    BASE_URL = "https://yhdm.one"
    API_URL = "https://yhdm.one/_get_plays/{video_id}/{ep}"

    UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )
    HEADERS = {
        "Referer": BASE_URL + "/",
        "User-Agent": UA,
    }

    # 源优先级（按顺序），域名映射
    SOURCES = {
        "WJ": ["ppqrrs.com"],
        "UK": ["ukzy.ukubf3.com"],
        "YH": ["vod12.wgslsw.com"],
        "JY": ["hd.ijycnd.com"],
        "SN": ["yuglf.com"],
        "GS": ["v.gsuus.com"],
        "XL": ["play.xluuss.com"],
        "HN": ["hn.bfvvs.com"],
        "MD": ["play.modujx11.com"],
        "IK": ["bfikuncdn.com"],
        "FF": ["vip.ffzy-plays.com"],
        "LZ": ["v.lzcdn27.com"],
        "JS": ["vv.jisuzyv.com"],
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def _label_from_url(self, url):
        """根据 m3u8 URL 的域名返回源标签"""
        try:
            host = urlparse(url).hostname
            if host:
                for label, domains in self.SOURCES.items():
                    if any(domain in host for domain in domains):
                        return label
        except Exception:
            pass
        return None

    # -------------------- Provider 接口 --------------------

    def search(self, keyword: str):
        """搜索动画，返回卡片列表"""
        url = f"{self.BASE_URL}/search?q={keyword}"
        resp = self.session.get(url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        cards = []
        # 搜索列表：每个 li 包含一个卡片
        for li in soup.select("#search_list ul.list-unstyled li"):
            a = li.find("a", href=True)
            if not a:
                continue
            href = a["href"]
            if not href.startswith("/vod/"):
                continue

            # 提取 vod_id
            match = re.search(r"/vod/(\d+)\.html", href)
            if not match:
                continue
            vid = match.group(1)

            # 标题
            title_tag = li.find("h6").find("a") if li.find("h6") else None
            title = title_tag.get_text(strip=True) if title_tag else ""

            # 封面
            img = li.find("img")
            cover = img.get("src") or img.get("data-original") if img else ""
            if cover and not cover.startswith("http"):
                cover = self.BASE_URL + cover

            # 备注（如年份、集数等）
            remark = ""
            year_tag = li.find("div", class_="small", string=re.compile(r"年份"))
            if year_tag:
                year_text = year_tag.get_text(strip=True)
                year_match = re.search(r"(\d{4})", year_text)
                if year_match:
                    remark = year_match.group(1)

            cards.append({
                "vod_id": vid,
                "vod_name": title,
                "cover": cover,
                "vod_remarks": remark,
                "url": self.BASE_URL + href,
            })
        return cards

    def get_tracks(self, card: dict):
        """从详情页获取剧集列表（反转顺序，使第1集在前）"""
        vid = card["vod_id"]
        detail_url = f"{self.BASE_URL}/vod/{vid}.html"
        resp = self.session.get(detail_url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        tracks = []
        for a in soup.select(".ep-col a"):
            href = a.get("href")
            if not href or not href.startswith("/vod-play/"):
                continue
            title = a.get_text(strip=True) or a.get("title", "")
            if not title:
                continue
            play_url = self.BASE_URL + href
            tracks.append({
                "name": title,
                "url": play_url,
            })

        # 反转顺序，使第1集在前（原页面通常是倒序）
        tracks.reverse()
        return tracks

    def resolve_play(self, track: dict):
        """解析单集播放地址，返回 m3u8 URL（按源优先级选择）"""
        play_url = track["url"]

        # 从播放页 URL 提取 video_id 和 ep
        match = re.search(r"/vod-play/(\d+)/(ep\d+)\.html", play_url)
        if not match:
            raise Exception("无效的播放页 URL")
        video_id, ep = match.groups()

        # 调用 API 获取源列表
        api_url = self.API_URL.format(video_id=video_id, ep=ep)
        try:
            resp = self.session.get(api_url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            raise Exception(f"获取播放源失败: {e}")

        sources = {}
        if data and "video_plays" in data:
            for play in data["video_plays"]:
                m3u8_url = play.get("play_data")
                if not m3u8_url or ".m3u8" not in m3u8_url:
                    continue
                # 简单验证 URL
                if not (m3u8_url.startswith("http://") or m3u8_url.startswith("https://")):
                    continue
                label = self._label_from_url(m3u8_url) or f"source_{len(sources)}"
                if label not in sources:
                    sources[label] = m3u8_url

        # 按优先级选择
        chosen_url = None
        for label in self.SOURCES:
            if label in sources:
                chosen_url = sources[label]
                break
        if not chosen_url and sources:
            chosen_url = next(iter(sources.values()))

        if not chosen_url:
            raise Exception("未找到可用的播放源")

        return chosen_url
