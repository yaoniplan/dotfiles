# https://github.com/keiyoushi/extensions-source/blob/main/src/zh/manhuagui/src/eu/kanade/tachiyomi/extension/zh/manhuagui/Manhuagui.kt
from __future__ import annotations

import json
import re
from urllib.parse import urljoin

import lzstring
import requests
from bs4 import BeautifulSoup


def _convert_base(value: int, base: int) -> str:
    digits = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if value == 0:
        return "0"
    result = ""
    while value > 0:
        result = digits[value % base] + result
        value //= base
    return result


def _unpack_packed_js(function_frame: str, a: int, c: int, data: list[str]) -> dict:
    def e(inner_c: int) -> str:
        return ("" if inner_c < a else e(inner_c // a)) + (
            chr(inner_c % a + 29) if inner_c % a > 35 else _convert_base(inner_c % a, 36)
        )

    c -= 1
    mapping: dict[str, str] = {}
    while c + 1:
        mapping[e(c)] = e(c) if data[c] == "" else data[c]
        c -= 1

    pieces = re.split(r"(\b\w+\b)", function_frame)
    js = "".join(mapping[x] if x in mapping else x for x in pieces).replace("\\'", "'")
    match = re.search(r"^.*\((\{.*\})\).*$", js)
    if not match:
        raise ValueError("Failed to extract JSON from unpacked chapter script")
    return json.loads(match.group(1))


class Provider:
    name = "manhuagui"
    #name = "漫画柜"

    IMAGE_SERVERS = [
        "https://i.hamreus.com",
        "https://cf.hamreus.com",
        "https://eu.hamreus.com",
        "https://us.hamreus.com",
    ]

    def __init__(
        self,
        base_url: str = "https://www.manhuagui.com",
        image_server: str | None = None,
        show_r18: bool = False,
    ):
        self.base_url = base_url.rstrip("/")
        self.image_server = (image_server or self.IMAGE_SERVERS[0]).rstrip("/")
        self.show_r18 = show_r18
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/138.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
                "Referer": self.base_url + "/",
            }
        )
        if self.show_r18:
            self.session.headers["Cookie"] = "isAdult=1"

    def _get(self, url: str, **kwargs) -> requests.Response:
        r = self.session.get(url, timeout=kwargs.pop("timeout", 15), **kwargs)
        r.raise_for_status()
        r.encoding = r.apparent_encoding or "utf-8"
        return r

    def _abs(self, path: str) -> str:
        if not path:
            return ""
        if path.startswith("http"):
            return path
        return urljoin(self.base_url + "/", path.lstrip("/"))

    @staticmethod
    def _extract_id(path_or_url: str) -> str:
        m = re.search(r"/comic/(\d+)", path_or_url or "")
        return m.group(1) if m else (path_or_url or "").strip("/")

    def _comic_id(self, comic) -> str:
        if isinstance(comic, dict):
            cid = comic.get("id") or comic.get("comic_id") or ""
        else:
            cid = str(comic or "")
        if cid.startswith("http"):
            return self._extract_id(cid)
        return str(cid).strip("/")

    # ------------------------------------------------------------------
    # search
    # ------------------------------------------------------------------

    def search(self, query: str, limit: int = 30, offset: int = 0) -> list[dict]:
        page = max(1, (offset // max(limit, 1)) + 1)

        if query.startswith("id:"):
            comic_id = query[3:].strip()
            info = self._comic_meta(comic_id)
            return [
                {
                    "id": info["id"],
                    "name": info["name"],
                    "cover": info.get("cover") or "",
                    "remark": ", ".join(info.get("authors") or []) or "未知作者",
                }
            ]

        if query.startswith("http") and (
            "manhuagui.com" in query or "mhgui.com" in query
        ):
            m = re.search(r"/comic/(\d+)", query)
            if m:
                return self.search(f"id:{m.group(1)}", limit=limit, offset=offset)

        if not query:
            return self._parse_list_page(
                f"{self.base_url}/list/view_p{page}.html", limit
            )

        url = f"{self.base_url}/s/{query}_p{page}.html"
        soup = BeautifulSoup(self._get(url).text, "html.parser")
        out: list[dict] = []
        for li in soup.select("div.book-result > ul > li"):
            detail = li.select_one("div.book-detail")
            if not detail:
                continue
            a = detail.select_one("dl > dt > a")
            if not a:
                continue
            href = a.get("href") or ""
            comic_id = self._extract_id(href)
            title = a.get("title") or a.get_text(strip=True)
            cover_el = li.select_one("div.book-cover > a.bcover > img")
            cover = ""
            if cover_el:
                cover = self._abs(
                    cover_el.get("src") or cover_el.get("data-src") or ""
                )
            authors = [
                x.get_text(strip=True)
                for x in detail.select("dd.tags a[href*='/author/']")
            ]
            out.append(
                {
                    "id": comic_id,
                    "name": title,
                    "cover": cover,
                    "remark": ", ".join(authors) if authors else "未知作者",
                }
            )
            if len(out) >= limit:
                break
        return out

    def _parse_list_page(self, url: str, limit: int = 30) -> list[dict]:
        soup = BeautifulSoup(self._get(url).text, "html.parser")
        out: list[dict] = []
        for li in soup.select("ul#contList > li"):
            a = li.select_one("a.bcover")
            if not a:
                continue
            href = a.get("href") or ""
            comic_id = self._extract_id(href)
            title = a.get("title") or a.get_text(strip=True)
            img = a.select_one("img")
            cover = ""
            if img:
                cover = self._abs(img.get("src") or img.get("data-src") or "")
            out.append(
                {
                    "id": comic_id,
                    "name": title,
                    "cover": cover,
                    "remark": "",
                }
            )
            if len(out) >= limit:
                break
        return out

    def _comic_meta(self, comic_id: str) -> dict:
        comic_id = self._extract_id(str(comic_id))
        soup = BeautifulSoup(
            self._get(f"{self.base_url}/comic/{comic_id}/").text, "html.parser"
        )
        title = ""
        h1 = soup.select_one("div.book-title > h1")
        if h1:
            title = h1.get_text(strip=True)
        cover = ""
        cover_el = soup.select_one("p.hcover > img") or soup.select_one(".hcover img")
        if cover_el:
            cover = self._abs(cover_el.get("src") or cover_el.get("data-src") or "")
        authors = []
        for a in soup.select("a[href^='/author/']"):
            t = a.get_text(strip=True)
            if t and t not in authors:
                authors.append(t)
        return {
            "id": comic_id,
            "name": title,
            "cover": cover,
            "authors": authors,
        }

    # ------------------------------------------------------------------
    # get_chapters
    # ------------------------------------------------------------------

    def get_chapters(self, comic, **kwargs) -> list[dict]:
        comic_id = self._comic_id(comic)
        if not comic_id:
            return []

        soup = BeautifulSoup(
            self._get(f"{self.base_url}/comic/{comic_id}/").text, "html.parser"
        )

        # R18 chapters may be LZString-compressed in __VIEWSTATE
        hidden = soup.select_one("#__VIEWSTATE")
        if hidden is not None:
            if not self.show_r18:
                raise ValueError(
                    "此作品包含 R18 章节。初始化时设置 show_r18=True。"
                )
            raw = hidden.get("value") or ""
            if raw:
                decoded = lzstring.LZString().decompressFromBase64(raw)
                if decoded:
                    hidden_soup = BeautifulSoup(decoded, "html.parser")
                    err = soup.select_one("#erroraudit_show")
                    if err:
                        err.replace_with(hidden_soup)
                    else:
                        soup.append(hidden_soup)
                    hidden.decompose()

        chapters: list[dict] = []
        # Each section lists newest-first → reverse within ul for oldest→newest
        for section in soup.select("[id^=chapter-list-]"):
            for ul in section.select("ul"):
                links = list(ul.select("li > a.status0, li > a"))
                for a in reversed(links):
                    href = a.get("href") or ""
                    if not href or "/comic/" not in href:
                        continue
                    name = a.get("title") or ""
                    if not name:
                        span = a.select_one("span")
                        name = (
                            span.get_text(strip=True)
                            if span
                            else a.get_text(strip=True)
                        )
                    name = re.sub(r"\d+p$", "", name).strip() or name
                    chapter_id = href.rstrip(".html").split("/")[-1]
                    chapters.append(
                        {
                            "id": chapter_id,
                            "name": name,
                            "comic_id": comic_id,
                        }
                    )
        return chapters

    # ------------------------------------------------------------------
    # resolve_read
    # ------------------------------------------------------------------

    def resolve_read(self, chapter, comic=None) -> list[str]:
        if isinstance(chapter, dict):
            chapter_id = chapter.get("id") or chapter.get("uuid") or ""
            comic_id = chapter.get("comic_id") or self._comic_id(comic)
            chapter_path = chapter.get("url")
        else:
            chapter_id = str(chapter or "")
            comic_id = self._comic_id(comic)
            chapter_path = None

        if not chapter_path:
            if not comic_id or not chapter_id:
                raise ValueError("Missing comic_id or chapter id")
            chapter_path = f"/comic/{comic_id}/{chapter_id}.html"

        url = (
            chapter_path
            if chapter_path.startswith("http")
            else self._abs(chapter_path)
        )
        html = self._get(url).text
        if "erroraudit_show" in html and not self.show_r18:
            raise ValueError("R18 作品显示开关未开启")
        return self._parse_page_list(html)

    def _parse_page_list(self, html: str) -> list[str]:
        packed_re = re.compile(
            r"""\}\(\s*'((?:\\'|[^'])*)'\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*'([0-9A-Za-z+/=]+)'""",
            re.DOTALL,
        )
        m = packed_re.search(html)
        if not m:
            raise ValueError(
                "Failed to find packed image code; site may have changed"
            )

        function_frame = m.group(1)
        a = int(m.group(2))
        c = int(m.group(3))
        data = lzstring.LZString().decompressFromBase64(m.group(4)).split("|")
        image_json = _unpack_packed_js(function_frame, a, c, data)

        path = image_json.get("path") or ""
        files = image_json.get("files") or []
        sl = image_json.get("sl") or {}
        e = sl.get("e", "")
        m_token = sl.get("m", "")

        return [
            f"{self.image_server}{path}{fname}?e={e}&m={m_token}" for fname in files
        ]

    def fetch_image(self, url: str) -> bytes:
        r = self.session.get(
            url,
            headers={
                "Referer": self.base_url + "/",
                "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                "Sec-Fetch-Dest": "image",
                "Sec-Fetch-Mode": "no-cors",
                "Sec-Fetch-Site": "cross-site",
            },
            timeout=20,
        )
        r.raise_for_status()
        return r.content
