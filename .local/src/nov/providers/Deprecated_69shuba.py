# https://github.com/juliusnguyen/noveltrans/blob/8305448da8cc76355528c7200fb9811628e54cf4/src/noveltrans/scrapers/shuba69.py
# https://github.com/lncrawl/lightnovel-crawler/blob/59b0382d51927953aa8120c5de62dab23ce3f731/sources/zh/69shuba.py
# https://github.com/HarlestNguyen/NovelCrawler/blob/4d90be331d2f79d23abee3130e8e4a570f5dcd39/parsers/parser_69shuba.py
# Because we need to handle Cloudflare challenges.
"""69书吧 (69shuba.com) Provider

对齐 noveltrans scrapers/shuba69.py + lncrawl sources/zh/69shuba.py
+ NovelCrawler parsers/parser_69shuba.py：

  - 书页：/book/<id>.htm          — OpenGraph 元数据
  - 目录：/book/<id>/             — 全量目录，一页 #catalog ul li a
  - 章节：/txt/<id>/<cid>         — 正文 div.txtnav（<br> 分隔）
  - 搜索：POST /modules/article/search.php  searchkey=（GBK）
  - 编码：页面多为 gbk
  - Cloudflare：部分网络下纯 requests 会 403

契约: search / get_chapters / resolve_read
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup

ORIGIN = "https://www.69shuba.com"

DESKTOP_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

_BOOK_RE = re.compile(r"/(?:book|txt)/(\d+)")
_CHAP_RE = re.compile(r"/txt/(\d+)/(\d+)")
_WS_RE = re.compile(r"\s+")
_INDEX_PREFIX_RE = re.compile(r"^\s*\d+\s*[.．、]\s*")

SEL_TOC = "#catalog ul li a[href], #catalog a[href]"
SEL_CONTENT = "div.txtnav, #content, .content"
SEL_CHROME = (
    "h1, h1.hide720, div.txtinfo, div.txtinfo.hide720, "
    "div#txtright, div.contentadv, div.bottom-ad, "
    "script, style, ins"
)

_NOISE_PREFIXES = (
    "作者：",
    "作者:",
    "更新时间：",
    "更新时间:",
    "发布时间：",
    "发布时间:",
    "上一章",
    "下一章",
    "目录",
    "返回书页",
)


class Provider:
    name = "69shuba"
    #name = "69书吧"
    base = ORIGIN

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": DESKTOP_UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,zh-TW;q=0.8,en;q=0.7",
                "Connection": "keep-alive",
                "Referer": f"{ORIGIN}/",
            }
        )
        self.headers = dict(self.session.headers)

    def _decode(self, r: requests.Response) -> str:
        raw = r.content
        for enc in ("gbk", "gb18030", "utf-8"):
            try:
                text = raw.decode(enc)
                if "�" not in text[:800]:
                    return text
            except Exception:
                continue
        r.encoding = r.apparent_encoding or "utf-8"
        return r.text

    def _get_html(self, url: str) -> str:
        r = self.session.get(url, timeout=25)
        if r.status_code == 403:
            raise RuntimeError(
                "69shuba 返回 403（Cloudflare）。"
                "请在本机浏览器打开一次站点完成验证，或换网络后再试。"
            )
        r.raise_for_status()
        return self._decode(r)

    def _book_id(self, text: str) -> str | None:
        m = _BOOK_RE.search(text or "")
        return m.group(1) if m else None

    @staticmethod
    def _norm(text: str) -> str:
        return _WS_RE.sub(" ", (text or "")).strip()

    @staticmethod
    def _clean_title(text: str) -> str:
        return _INDEX_PREFIX_RE.sub("", (text or "").strip())

    def _info_url(self, bid: str) -> str:
        return f"{ORIGIN}/book/{bid}.htm"

    def _toc_url(self, bid: str) -> str:
        return f"{ORIGIN}/book/{bid}/"

    def _chap_url(self, bid: str, cid: str) -> str:
        return f"{ORIGIN}/txt/{bid}/{cid}"

    def _parse_meta(self, html: str, bid: str) -> dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")

        def og(prop: str) -> str:
            el = soup.select_one(f"meta[property='{prop}']")
            return (el.get("content") or "").strip() if el else ""

        name = og("og:novel:book_name") or og("og:title")
        if not name:
            h1 = soup.select_one("div.booknav2 h1, h1")
            name = self._norm(h1.get_text()) if h1 else "未知"
        author = og("og:novel:author")
        if not author:
            a = soup.select_one('.booknav2 p a[href*="author"]')
            author = self._norm(a.get_text()) if a else ""
        desc = og("og:description")
        if desc:
            desc = re.sub(r"<br\s*/?>", "\n", desc, flags=re.I)
            desc = self._norm(desc)
        if not desc:
            intro = soup.select_one("div.navtxt, #intro")
            desc = self._norm(intro.get_text(" ", strip=True)) if intro else ""
        if len(desc) > 120:
            desc = desc[:120] + "…"
        status = og("og:novel:status") or ""
        remark = " · ".join(p for p in (author, status) if p)
        return {
            "id": bid,
            "name": name or "未知",
            "url": f"/book/{bid}.htm",
            "author": author,
            "remark": remark,
            "desc": desc,
        }

    def _is_noise_line(self, line: str, title: str) -> bool:
        s = line.strip()
        if not s:
            return True
        if title and self._clean_title(s) == self._clean_title(title):
            return True
        return any(s.startswith(p) for p in _NOISE_PREFIXES)

    def search(self, keyword: str) -> list[dict[str, Any]]:
        kw = (keyword or "").strip()
        if not kw:
            return []

        bid = self._book_id(kw)
        if not bid and re.fullmatch(r"\d+", kw):
            bid = kw
        if bid and (
            kw.startswith("http")
            or re.fullmatch(r"\d+", kw)
            or "/book/" in kw
            or "/txt/" in kw
        ):
            try:
                html = self._get_html(self._info_url(bid))
                return [self._parse_meta(html, bid)]
            except Exception:
                return []

        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        try:
            encoded = quote(kw.encode("gbk", errors="ignore"))
            data = f"searchkey={encoded}&submit=Search"
            r = self.session.post(
                f"{ORIGIN}/modules/article/search.php",
                data=data,
                headers={
                    **self.headers,
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": ORIGIN,
                    "Referer": f"{ORIGIN}/modules/article/search.php",
                },
                timeout=25,
            )
            if r.status_code == 403:
                return []
            r.raise_for_status()
            html = self._decode(r)
            soup = BeautifulSoup(html, "html.parser")

            items = soup.select("div.newbox ul li") or soup.select(".newbox li")
            for li in items:
                a = li.select_one("h3 a[href], a[href*='/book/'], a[href*='/txt/']")
                if not a:
                    continue
                href = a.get("href") or ""
                book_id = self._book_id(href)
                if not book_id or book_id in seen:
                    continue
                name = self._norm(a.get_text())
                if not name or len(name) > 60:
                    continue
                latest_el = li.select_one("div.zxzj p, .zxzj")
                latest = self._norm(latest_el.get_text()) if latest_el else ""
                seen.add(book_id)
                results.append(
                    {
                        "id": book_id,
                        "name": name,
                        "url": f"/book/{book_id}.htm",
                        "author": "",
                        "remark": latest[:40] if latest else "",
                        "desc": latest,
                    }
                )
                if len(results) >= 30:
                    break
        except Exception:
            pass
        return results

    def get_chapters(self, card: dict) -> list[dict[str, Any]]:
        bid = str(card.get("id") or "").strip()
        if not bid:
            bid = self._book_id(card.get("url") or "") or ""
        if not bid:
            return []

        html = self._get_html(self._toc_url(bid))
        soup = BeautifulSoup(html, "html.parser")
        chapters: list[dict[str, Any]] = []
        seen: set[str] = set()
        for a in soup.select(SEL_TOC):
            href = (a.get("href") or "").strip()
            m = _CHAP_RE.search(href) or re.search(r"/txt/(\d+)/(\d+)", href)
            if not m:
                continue
            book_id, cid = m.group(1), m.group(2)
            if book_id != bid or cid in seen:
                continue
            seen.add(cid)
            name = self._clean_title(self._norm(a.get_text())) or f"第{cid}章"
            full = href if href.startswith("http") else urljoin(ORIGIN, href)
            chapters.append(
                {
                    "id": cid,
                    "name": name,
                    "url": full,
                    "book_id": book_id,
                }
            )
        return chapters

    def resolve_read(self, chap: dict, comic: dict | None = None) -> list[str]:
        url = chap.get("url") or ""
        if not url.startswith("http"):
            bid = chap.get("book_id") or (comic or {}).get("id")
            cid = chap.get("id")
            if bid and cid:
                url = self._chap_url(str(bid), str(cid))
            else:
                return []

        html = self._get_html(url)
        soup = BeautifulSoup(html, "html.parser")
        container = None
        for sel in SEL_CONTENT.split(", "):
            container = soup.select_one(sel)
            if container is not None:
                break
        if container is None:
            return []

        for el in container.select(SEL_CHROME):
            el.decompose()
        for a in container.select("a"):
            t = a.get_text(strip=True)
            if t in {"上一章", "下一章", "目录", "返回书页"}:
                a.decompose()

        title = chap.get("name") or ""
        return [
            line.strip()
            for line in container.get_text("\n").split("\n")
            if line.strip() and not self._is_noise_line(line, title)
        ]
