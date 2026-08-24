# https://github.com/woshishiq1/hipy-drpy2/blob/main/dr/js/%E5%8A%A8%E6%BC%AB/%E7%95%AA%E8%96%AF%E5%8A%A8%E6%BC%AB%5B%E6%BC%AB%5D.js
# The community is no longer maintaining it (for example, the latest encryption/decryption methods have not been updated.)
# Captcha-like human verification - Cloudflare JavaScript challenge - Slider verrification
import base64
import hashlib
import random
import re
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


class Provider:
    name = "fsdm"
    #name = "番薯动漫"

    BASE = "https://www.fsdm02.com"

    def __init__(self):
        # 动态 User-Agent，模拟原脚本
        webkit_ver = f"{(537 + random.random() * 2):.2f}"
        chrome_ver = random.randint(90, 129)
        ua = (
            f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            f"AppleWebKit/{webkit_ver} (KHTML, like Gecko) "
            f"Chrome/{chrome_ver}.0.0.0 Safari/537.36"
        )

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": ua,
            "X-Forwarded-For": f"116.25.{random.randint(0,255)}.{random.randint(0,255)}",
            "Referer": self.BASE,
            "Origin": self.BASE,
        })

    # ------------------------------------------------------------------
    # 解密 player_data
    # ------------------------------------------------------------------
    def _decrypt_player(self, encrypted_data: str) -> str:
        if not HAS_CRYPTO:
            raise RuntimeError("需要安装 pycryptodome 库: pip install pycryptodome")

        # key = MD5('fsdm@2024') 的十六进制字符串
        key_hex = hashlib.md5("fsdm@2024".encode()).hexdigest()
        key = key_hex.encode("utf-8")          # 作为 UTF‑8 文本
        iv = key_hex[16:32].encode("utf-8")    # 取后 16 字节（128 位）

        # CryptoJS 默认 AES‑CBC，密文是 Base64 编码
        ciphertext = base64.b64decode(encrypted_data)
        cipher = AES.new(key, AES.MODE_CBC, iv=iv)
        decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)
        return decrypted.decode("utf-8")

    # ------------------------------------------------------------------
    # 搜索
    # ------------------------------------------------------------------
    def search(self, keyword: str) -> list[dict]:
        """返回 vod_id, vod_name, vod_remarks, url 的卡片列表"""
        url = f"{self.BASE}/vodsearch/-------------.html?wd={quote(keyword)}"
        resp = self.session.get(url, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")

        cards = []
        for item in soup.select(".search-item"):
            a_tag = item.select_one("a")
            if not a_tag:
                continue
            href = a_tag.get("href", "")
            if not href.startswith("/voddetail/"):
                continue

            title_el = item.select_one(".title")
            img_el = item.select_one("img")
            desc_el = item.select_one(".info")

            cards.append({
                "vod_id": href,
                "vod_name": (
                    title_el.text.strip() if title_el
                    else (img_el.get("alt", "") if img_el else "")
                ),
                "vod_remarks": desc_el.text.strip() if desc_el else "",
                "url": self.BASE + href,
            })

        return cards

    # ------------------------------------------------------------------
    # 获取剧集列表 (tabs / episodes)
    # ------------------------------------------------------------------
    def get_tracks(self, card: dict) -> list[dict]:
        """返回 {name, url} 的剧集列表"""
        resp = self.session.get(card["url"], timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")

        tabs = soup.select(".play-source-tab a")
        if not tabs:
            return []

        episode_lists = soup.select(".episode-list")
        tracks = []

        for i, tab in enumerate(tabs):
            source_name = tab.text.strip()
            if i >= len(episode_lists):
                break
            ep_list = episode_lists[i]
            for a_tag in ep_list.select("a"):
                href = a_tag.get("href", "")
                if not href.startswith("/vodplay/"):
                    continue
                ep_name = a_tag.text.strip()
                tracks.append({
                    "name": f"【{source_name}】{ep_name}",
                    "url": self.BASE + href,
                })

        return tracks

    # ------------------------------------------------------------------
    # 解析真实播放地址
    # ------------------------------------------------------------------
    def resolve_play(self, track: dict) -> str:
        """返回可直接播放的 m3u8 / mp4 地址"""
        resp = self.session.get(track["url"], timeout=15)
        html = resp.text

        match = re.search(r"var\s+player_data\s*=\s*'(.*?)'", html)
        if not match:
            raise Exception("未找到加密的 player_data")

        encrypted = match.group(1)
        play_url = self._decrypt_player(encrypted)
        return play_url
