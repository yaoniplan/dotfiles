"""爱下电子书 (ixdzs8.com) Provider

对齐 noveltrans scrapers/ixdzs.py：
  - 章节页偶发 JS challenge：响应含 token +「正在验证」，需 ?challenge=<token> 再请求
  - 目录：POST /novel/clist/ {bid} → JSON
  - 正文：article > p
  - 搜索：GET /bsearch?q=
  - 契约: search / get_chapters / resolve_read
"""

from __future__ import annotations

import re
from typing import Any

import requests
from bs4 import BeautifulSoup

ORIGIN = "https://ixdzs8.com"

MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_7_2 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 "
    "Mobile/15E148 Safari/604.1"
)

_BID_RE = re.compile(r"/read/(\d+)")
_CHALLENGE_RE = re.compile(r'token\s*=\s*"([^"]+)"')
_WS_RE = re.compile(r"\s+")


class Provider:
    name = "ix"
    #name = "爱下电子书"
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

    def _get_html(self, url: str, **kwargs) -> str:
        """GET；若命中 challenge 页则带 token 重试一次。"""
        r = self.session.get(url, timeout=20, **kwargs)
        r.raise_for_status()
        r.encoding = r.apparent_encoding or "utf-8"
        html = r.text
        if "正在验证" in html:
            m = _CHALLENGE_RE.search(html)
            if m:
                r = self.session.get(
                    url, params={"challenge": m.group(1)}, timeout=20, **kwargs
                )
                r.raise_for_status()
                r.encoding = r.apparent_encoding or "utf-8"
                html = r.text
                if "正在验证" in html and _CHALLENGE_RE.search(html):
                    raise RuntimeError(f"challenge failed: {url}")
        return html

    def _book_id(self, text: str) -> str | None:
        m = _BID_RE.search(text or "")
        return m.group(1) if m else None

    @staticmethod
    def _norm(text: str) -> str:
        return _WS_RE.sub(" ", (text or "")).strip()

    def _parse_meta(self, html: str, bid: str) -> dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")

        def og(prop: str) -> str:
            el = soup.select_one(f"meta[property='{prop}']")
            return (el.get("content") or "").strip() if el else ""

        name = og("og:novel:book_name") or og("og:title")
        if not name:
            h1 = soup.select_one("h1")
            name = self._norm(h1.get_text()) if h1 else "未知"
        author = og("og:novel:author")
        desc = og("og:description")
        if len(desc) > 120:
            desc = desc[:120] + "…"
        status = og("og:novel:status") or ""
        remark = " · ".join(p for p in (author, status) if p)
        return {
            "id": bid,
            "name": name or "未知",
            "url": f"/read/{bid}/",
            "author": author,
            "remark": remark,
            "desc": desc,
        }

    # ------------------------------------------------------------------ API

    def search(self, keyword: str) -> list[dict[str, Any]]:
        kw = (keyword or "").strip()
        if not kw:
            return []

        # 直接 URL / 纯数字 id
        bid = self._book_id(kw)
        if not bid and re.fullmatch(r"\d+", kw):
            bid = kw
        if bid and (kw.startswith("http") or re.fullmatch(r"\d+", kw) or "/read/" in kw):
            try:
                html = self._get_html(f"{ORIGIN}/read/{bid}/")
                return [self._parse_meta(html, bid)]
            except Exception:
                return []

        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        try:
            r = self.session.get(
                f"{ORIGIN}/bsearch",
                params={"q": kw},
                timeout=20,
            )
            r.raise_for_status()
            r.encoding = r.apparent_encoding or "utf-8"
            soup = BeautifulSoup(r.text, "html.parser")
            for li in soup.select("li.burl"):
                title_a = li.select_one("h3.bname a[href*='/read/']") or li.select_one(
                    "a[href*='/read/']"
                )
                if not title_a:
                    continue
                href = title_a.get("href") or li.get("data-url") or ""
                book_id = self._book_id(href)
                if not book_id or book_id in seen:
                    continue
                name = self._norm(title_a.get("title") or title_a.get_text())
                author_el = li.select_one("span.bauthor a, span.bauthor")
                author = self._norm(author_el.get_text()) if author_el else ""
                status_el = li.select_one("span.lz")
                status = self._norm(status_el.get_text()) if status_el else ""
                desc_el = li.select_one("p.l-p2")
                desc = self._norm(desc_el.get_text()) if desc_el else ""
                if len(desc) > 80:
                    desc = desc[:80] + "…"
                remark = " · ".join(p for p in (author, status) if p)
                seen.add(book_id)
                results.append(
                    {
                        "id": book_id,
                        "name": name or "未知",
                        "url": f"/read/{book_id}/",
                        "author": author,
                        "remark": remark,
                        "desc": desc,
                    }
                )
        except Exception:
            pass
        return results

    def get_chapters(self, card: dict) -> list[dict[str, Any]]:
        bid = str(card.get("id") or "").strip()
        if not bid:
            bid = self._book_id(card.get("url") or "") or ""
        if not bid:
            return []

        r = self.session.post(
            f"{ORIGIN}/novel/clist/",
            data={"bid": bid},
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "User-Agent": MOBILE_UA,
                "Referer": f"{ORIGIN}/read/{bid}/",
            },
            timeout=20,
        )
        r.raise_for_status()
        payload = r.json()
        if payload.get("rs") != 200:
            return []

        chapters: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in payload.get("data") or []:
            if str(item.get("ctype")) == "1":
                continue  # 分卷标题
            order = str(item.get("ordernum") or "").strip()
            if not order or order in seen:
                continue
            seen.add(order)
            title = self._norm(str(item.get("title") or f"第{order}章"))
            chapters.append(
                {
                    "id": order,
                    "name": title,
                    "url": f"{ORIGIN}/read/{bid}/p{order}.html",
                    "book_id": bid,
                }
            )
        return chapters

    def resolve_read(self, chap: dict, comic: dict | None = None) -> list[str]:
        url = chap.get("url") or ""
        if not url.startswith("http"):
            bid = chap.get("book_id") or (comic or {}).get("id")
            cid = chap.get("id")
            if bid and cid:
                url = f"{ORIGIN}/read/{bid}/p{cid}.html"
            else:
                return []

        html = self._get_html(url)
        soup = BeautifulSoup(html, "html.parser")
        container = soup.select_one("article")
        if container is None:
            return []

        paragraphs: list[str] = []
        for p in container.select("p"):
            text = self._norm(p.get_text())
            if text:
                paragraphs.append(text)

        title = chap.get("name") or ""
        if paragraphs and title and self._norm(paragraphs[0]) == self._norm(title):
            paragraphs = paragraphs[1:]
        return paragraphs
