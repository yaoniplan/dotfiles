"""半夏小說 (xbanxia.cc) Provider

对齐 noveltrans scrapers/xbanxia.py：
  - 书页：/books/<id>.html（元数据 + 全文目录 .book-list）
  - 章节：/books/<id>/<cid>.html，正文 #nr1（<br> 分隔）
  - 搜索：POST /modules/article/search_t.php {searchkey}
  - 契约: search / get_chapters / resolve_read
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ORIGIN = "https://www.xbanxia.cc"

MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_7_2 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 "
    "Mobile/15E148 Safari/604.1"
)

_ID_RE = re.compile(r"/books/(\d+)")
_CHAP_RE = re.compile(r"/books/(\d+)/(\d+)\.html")
_WS_RE = re.compile(r"\s+")
_COLONS = r":：︰"

SEL_TITLE = ".book-describe h1"
SEL_INFO_ROWS = ".book-describe p"
SEL_DESCRIPTION = ".describe-html"
SEL_TOC_LINKS = ".book-list a[href]"
SEL_CONTENT = "#nr1"


class Provider:
    name = "bx"
    #name = "半夏小說"
    base = ORIGIN

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": MOBILE_UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Connection": "keep-alive",
            }
        )
        self.headers = dict(self.session.headers)

    # ------------------------------------------------------------------ network

    def _decode(self, resp: requests.Response) -> str:
        raw = resp.content
        for enc in ("utf-8", "gbk", "gb18030", resp.apparent_encoding or ""):
            if not enc:
                continue
            try:
                return raw.decode(enc)
            except (LookupError, UnicodeDecodeError):
                continue
        return raw.decode("utf-8", errors="replace")

    def _get_html(self, url: str) -> str:
        r = self.session.get(url, timeout=20)
        r.raise_for_status()
        return self._decode(r)

    def _book_id(self, text: str) -> str | None:
        m = _ID_RE.search(text or "")
        return m.group(1) if m else None

    @staticmethod
    def _norm(text: str) -> str:
        return _WS_RE.sub(" ", (text or "")).strip()

    def _clean_title(self, name: str) -> str:
        name = self._norm(name)
        for prefix in ("半夏小說", "半夏小说"):
            if name.startswith(prefix):
                name = name[len(prefix) :].strip()
        return name or "未知"

    def _parse_meta(self, html: str, bid: str) -> dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")
        title_el = soup.select_one(SEL_TITLE)
        name = self._clean_title(title_el.get_text()) if title_el else "未知"

        author = ""
        status = ""
        for row in soup.select(SEL_INFO_ROWS):
            text = self._norm(row.get_text(" "))
            if text.startswith("作者"):
                author = re.split(f"[{_COLONS}]", text, maxsplit=1)[-1].strip()
            elif text.startswith("狀態") or text.startswith("状态"):
                status = re.split(f"[{_COLONS}]", text, maxsplit=1)[-1].strip()

        desc_el = soup.select_one(SEL_DESCRIPTION)
        desc = self._norm(desc_el.get_text(" ", strip=True)) if desc_el else ""
        if len(desc) > 120:
            desc = desc[:120] + "…"

        remark = " · ".join(p for p in (author, status) if p)
        return {
            "id": bid,
            "name": name,
            "url": f"/books/{bid}.html",
            "author": author,
            "remark": remark,
            "desc": desc,
        }

    # ------------------------------------------------------------------ API

    def search(self, keyword: str) -> list[dict[str, Any]]:
        kw = (keyword or "").strip()
        if not kw:
            return []

        bid = self._book_id(kw)
        if not bid and re.fullmatch(r"\d+", kw):
            bid = kw
        if bid and (kw.startswith("http") or re.fullmatch(r"\d+", kw) or "/books/" in kw):
            try:
                html = self._get_html(f"{ORIGIN}/books/{bid}.html")
                return [self._parse_meta(html, bid)]
            except Exception:
                return []

        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        for endpoint in (
            f"{ORIGIN}/modules/article/search_t.php",
            f"{ORIGIN}/modules/article/search.php",
        ):
            try:
                r = self.session.post(
                    endpoint,
                    data={"searchkey": kw},
                    headers={
                        "User-Agent": MOBILE_UA,
                        "Referer": f"{ORIGIN}/",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    timeout=20,
                )
                r.raise_for_status()
                soup = BeautifulSoup(self._decode(r), "html.parser")
                for a in soup.select("a[href*='/books/']"):
                    href = a.get("href") or ""
                    if not re.search(r"/books/\d+\.html", href):
                        continue
                    if re.search(r"/books/\d+/\d+", href):
                        continue
                    book_id = self._book_id(href)
                    if not book_id or book_id in seen:
                        continue
                    name = self._clean_title(a.get_text())
                    if not name or name == "未知" or len(name) < 1:
                        continue
                    if len(name) > 60:
                        continue
                    seen.add(book_id)
                    results.append(
                        {
                            "id": book_id,
                            "name": name,
                            "url": f"/books/{book_id}.html",
                            "author": "",
                            "remark": "",
                            "desc": "",
                        }
                    )
                if results:
                    break
            except Exception:
                continue
        return results

    def get_chapters(self, card: dict) -> list[dict[str, Any]]:
        bid = str(card.get("id") or "").strip()
        if not bid:
            bid = self._book_id(card.get("url") or "") or ""
        if not bid:
            return []

        html = self._get_html(f"{ORIGIN}/books/{bid}.html")
        soup = BeautifulSoup(html, "html.parser")
        chapters: list[dict[str, Any]] = []
        seen: set[str] = set()
        for a in soup.select(SEL_TOC_LINKS):
            href = (a.get("href") or "").strip()
            m = _CHAP_RE.search(href)
            if not m:
                continue
            book_id, cid = m.group(1), m.group(2)
            if cid in seen:
                continue
            seen.add(cid)
            name = self._norm(a.get_text()) or f"第{cid}章"
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
                url = f"{ORIGIN}/books/{bid}/{cid}.html"
            else:
                return []

        html = self._get_html(url)
        soup = BeautifulSoup(html, "html.parser")
        container = soup.select_one(SEL_CONTENT)
        if container is None:
            return []

        for el in container.select("span, div, script, ins"):
            el.decompose()

        lines = [
            line.strip()
            for line in container.get_text("\n").split("\n")
            if line.strip()
        ]

        title = chap.get("name") or ""
        if lines and title and self._norm(lines[0]) == self._norm(title):
            lines = lines[1:]
        if lines and re.search(r"作者[：:︰]", lines[0]) and len(lines[0]) < 80:
            lines = lines[1:]
        return lines
