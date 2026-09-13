# https://github.com/keiyoushi/extensions-source/pull/18989
"""瓜子漫画 — unified contract: search / get_chapters / resolve_read.

Web HTML for search/chapters; chapter images prefer the official app API
(api.guaziapp.com) because /chapter.php is heavily rate-limited (429) and
sometimes returns an empty reader for the newest chapter.
"""
from __future__ import annotations

import base64
import hashlib
import re
import uuid
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

API_URL = "https://api.guaziapp.com/index.php"
# From guazi.apk v1.6.1 — bump if the API starts rejecting old clients
APP_VERSION_CODE = "53"
SITE_TZ = timezone(timedelta(hours=8))  # Asia/Shanghai


class Provider:
    name = "guazi"
    #name = "瓜子漫画"

    def __init__(self, base_url: str = "https://www.guazimanhua.com"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0.0.0 Safari/537.36"
                ),
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;q=0.9,"
                    "image/webp,image/apng,*/*;q=0.8"
                ),
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": self.base_url + "/",
            }
        )
        # App API guest session (lazy)
        self._app_token: str | None = None
        self._app_identifier = hashlib.sha1(
            uuid.uuid4().hex.encode()
        ).hexdigest().upper()

    # ------------------------------------------------------------------ web
    def _get_html(self, path: str, params: dict | None = None) -> str:
        url = urljoin(self.base_url + "/", path.lstrip("/"))
        r = self.session.get(url, params=params, timeout=20)
        r.raise_for_status()
        r.encoding = r.apparent_encoding or "utf-8"
        return r.text

    @staticmethod
    def _id_from_href(href: str) -> str:
        if not href:
            return ""
        qs = parse_qs(urlparse(href).query)
        if qs.get("id"):
            return qs["id"][0]
        m = re.search(r"[?&]id=(\d+)", href)
        return m.group(1) if m else href.strip("/")

    def search(self, query: str, limit: int = 36, offset: int = 0) -> list[dict]:
        page = offset // 36 + 1 if offset else 1
        html = self._get_html(
            "/category.php",
            {"keyword": query, "sort": "hits", "page": page},
        )
        soup = BeautifulSoup(html, "html.parser")
        out: list[dict] = []
        for card in soup.select("article.card"):
            link = card.select_one("a.cover-wrap") or card.select_one("h3 a")
            title_el = card.select_one("h3 a")
            if not link or not title_el:
                continue
            href = link.get("href") or ""
            cover_el = card.select_one("img.cover")
            cover = (cover_el.get("src") if cover_el else "") or ""
            if cover.startswith("//"):
                cover = "https:" + cover
            meta = card.select_one("div.meta")
            remark = ""
            if meta:
                remark = (meta.get_text(" ", strip=True) or "").split("·")[0].strip()
            out.append(
                {
                    "id": self._id_from_href(href),
                    "name": title_el.get_text(strip=True),
                    "cover": cover,
                    "remark": remark,
                }
            )
            if len(out) >= limit:
                break
        return out

    def get_chapters(self, comic, **kwargs) -> list[dict]:
        cid = comic.get("id") if isinstance(comic, dict) else comic
        if not cid:
            return []
        html = self._get_html("/comic.php", {"id": cid})
        soup = BeautifulSoup(html, "html.parser")
        anchors = soup.select(
            "section.mobile-comic-all-chapters div.mobile-chapter-grid a"
        )
        if not anchors:
            anchors = soup.select("a[href*='chapter.php']")

        chapters: list[dict] = []
        seen: set[str] = set()
        for a in anchors:
            chap_id = self._id_from_href(a.get("href") or "")
            if not chap_id or chap_id in seen:
                continue
            seen.add(chap_id)
            chapters.append(
                {
                    "id": str(chap_id),
                    "name": a.get_text(strip=True) or f"第{len(chapters) + 1}话",
                    "comic_id": str(cid),
                }
            )
        # Site lists newest-first
        chapters.reverse()
        return chapters

    # ----------------------------------------------------------- app API
    def _app_headers(self) -> dict:
        return {
            "User-Agent": "okhttp/4.9.0",
            "deviceType": "android",
            "Accept": "application/json",
            "token": self._ensure_app_token(),
        }

    def _ensure_app_token(self) -> str:
        if self._app_token:
            return self._app_token
        r = self.session.post(
            f"{API_URL}/api/v2/login/visitor",
            headers={
                "User-Agent": "okhttp/4.9.0",
                "deviceType": "android",
                "Accept": "application/json",
            },
            data={
                "identifier": self._app_identifier,
                "versionCode": APP_VERSION_CODE,
            },
            timeout=20,
        )
        r.raise_for_status()
        token = (r.json().get("data") or {}).get("token")
        if not token:
            raise RuntimeError("Guazi app API did not return a guest token")
        self._app_token = token
        return token

    @staticmethod
    def _key_date(date_hdr: str | None) -> str:
        if date_hdr:
            dt = parsedate_to_datetime(date_hdr).astimezone(SITE_TZ)
        else:
            dt = datetime.now(SITE_TZ)
        return dt.strftime("%Y%m%d")

    @classmethod
    def _decrypt_img_field(cls, encoded: str, date_hdr: str | None) -> str:
        # key = MD5("guazi" + yyyyMMdd) as 32 UTF-8 bytes; IV = chars [8:24]
        material = hashlib.md5(
            ("guazi" + cls._key_date(date_hdr)).encode()
        ).hexdigest()
        key = material.encode("utf-8")
        iv = material[8:24].encode("utf-8")
        ct = base64.b64decode(encoded)
        plain = AES.new(key, AES.MODE_CBC, iv).decrypt(ct)
        try:
            plain = unpad(plain, 16)
        except ValueError:
            pass
        return plain.decode("utf-8")

    def _resolve_via_app(self, chap_id: str) -> list[str]:
        last_err = 0
        for _ in range(2):
            r = self.session.get(
                f"{API_URL}/api/v2/mcomic/pics",
                headers=self._app_headers(),
                params={
                    "chapter_id": str(chap_id),
                    "identifier": self._app_identifier,
                    "versionCode": APP_VERSION_CODE,
                },
                timeout=20,
            )
            r.raise_for_status()
            date_hdr = r.headers.get("Date")
            body = r.json()
            if body.get("error_code") == 0:
                images = (body.get("data") or {}).get("images") or []
                return [
                    self._decrypt_img_field(img["img"], date_hdr)
                    for img in images
                    if img.get("img")
                ]
            # stale token → re-login
            last_err = body.get("error_code")
            self._app_token = None
        raise RuntimeError(f"Guazi app API error_code={last_err}")

    def _resolve_via_web(self, chap_id: str, comic_id=None) -> list[str]:
        if comic_id:
            self.session.headers["Referer"] = (
                f"{self.base_url}/comic.php?id={comic_id}"
            )
        html = self._get_html("/chapter.php", {"id": chap_id})
        soup = BeautifulSoup(html, "html.parser")
        images = soup.select("section.reader-images img") or soup.select(
            "img.reading-image"
        )
        urls: list[str] = []
        seen: set[str] = set()
        for img in images:
            src = img.get("src") or img.get("data-src") or ""
            if not src:
                continue
            if src.startswith("//"):
                src = "https:" + src
            elif src.startswith("/"):
                src = urljoin(self.base_url, src)
            fn = src.rsplit("/", 1)[-1]
            if fn in seen:
                continue
            seen.add(fn)
            urls.append(src)
        return urls

    def resolve_read(self, chapter, comic=None) -> list[str]:
        if isinstance(chapter, dict):
            chap_id = (
                chapter.get("id")
                or chapter.get("uuid")
                or chapter.get("chapter_id")
                or ""
            )
            comic_id = chapter.get("comic_id") or (
                comic.get("id") if isinstance(comic, dict) else comic
            )
        else:
            chap_id = chapter
            comic_id = comic.get("id") if isinstance(comic, dict) else comic

        if not chap_id:
            raise ValueError("Missing chapter id")

        # App API first: avoids 429 on /chapter.php and works for withheld newest chapters
        try:
            urls = self._resolve_via_app(str(chap_id))
            if urls:
                return urls
        except Exception:
            pass

        # Web fallback (may 429 or return empty for newest chapter)
        try:
            urls = self._resolve_via_web(str(chap_id), comic_id)
            if urls:
                return urls
        except Exception:
            pass

        # Last resort: app API error surfaces to caller
        return self._resolve_via_app(str(chap_id))
