"""笔趣阁 (biquge8.xyz) 小说 Provider

契约 (对齐 com 的 Provider):
  search(keyword) -> list[dict]          # id, name, remark?, url?, author?
  get_chapters(card) -> list[dict]       # id, name, url?, book_id?
  resolve_read(chap, comic=None) -> list[str]  # 正文段落文本列表
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup


class Provider:
    name = "bqg"
    #name = "笔趣阁"
    base = "https://www.biquge8.xyz"

    def __init__(self) -> None:
        self.session = requests.Session()
        # 搜索用移动端结果更干净；目录/正文必须用桌面端才能拿到完整章节列表
        self.ua_mobile = (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 "
            "Mobile/15E148 Safari/604.1"
        )
        self.ua_pc = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/119.0.0.0 Safari/537.36"
        )
        self.session.headers.update(
            {
                "User-Agent": self.ua_mobile,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate",
            }
        )
        self.headers = dict(self.session.headers)

    def _get(self, path: str, *, pc: bool = False, **kwargs) -> BeautifulSoup:
        url = path if path.startswith("http") else urljoin(self.base, path)
        headers = {"User-Agent": self.ua_pc if pc else self.ua_mobile}
        r = self.session.get(url, headers=headers, timeout=15, **kwargs)
        r.raise_for_status()
        r.encoding = r.apparent_encoding or "utf-8"
        return BeautifulSoup(r.text, "html.parser")

    def search(self, keyword: str) -> list[dict[str, Any]]:
        if not keyword or not keyword.strip():
            return []
        soup = self._get(f"/search?keyword={quote(keyword.strip())}")
        results: list[dict[str, Any]] = []
        for li in soup.select("li.book-li"):
            a = li.select_one("a.book-layout") or li.select_one("a[href]")
            if not a or not a.get("href"):
                continue
            href = a["href"].strip()
            m = re.search(r"/(\d+)/?$", href)
            book_id = m.group(1) if m else href.strip("/")
            title_el = li.select_one(".book-title") or li.select_one("h4")
            name = title_el.get_text(strip=True) if title_el else "未知"
            name = re.sub(r"\s+", " ", name).strip()
            author_el = li.select_one(".book-author")
            author = author_el.get_text(strip=True) if author_el else ""
            desc_el = li.select_one(".book-desc")
            desc = desc_el.get_text(strip=True) if desc_el else ""
            tags = [em.get_text(strip=True) for em in li.select(".tag-small")]
            remark_parts = []
            if author:
                remark_parts.append(author)
            if tags:
                remark_parts.append(" / ".join(tags))
            remark = " · ".join(remark_parts) if remark_parts else (desc[:40] if desc else "")
            results.append(
                {
                    "id": book_id,
                    "name": name,
                    "url": href if href.startswith("/") else f"/{book_id}",
                    "author": author,
                    "remark": remark,
                    "desc": desc,
                }
            )
        return results

    def get_chapters(self, card: dict) -> list[dict[str, Any]]:
        book_id = str(card.get("id") or "").strip()
        if not book_id:
            url = card.get("url") or ""
            m = re.search(r"/(\d+)/?$", url)
            book_id = m.group(1) if m else ""
        if not book_id:
            return []
        # 必须用 PC UA，移动端目录几乎为空
        soup = self._get(f"/{book_id}", pc=True)
        chapters: list[dict[str, Any]] = []
        links = soup.select(".chapter_list li a")
        if not links:
            links = soup.select("div.section.chapter_list ul li a")
        seen: set[str] = set()
        for a in links:
            href = (a.get("href") or "").strip()
            if not href or href in seen:
                continue
            # 跳过锚点、听书等
            if "#" in href:
                continue
            m = re.search(rf"/{re.escape(book_id)}/(\d+)/?$", href)
            if not m:
                continue
            chap_id = m.group(1)
            name = (a.get("title") or a.get_text(strip=True) or f"第{chap_id}章").strip()
            # 过滤「开始阅读」之类非真实章节名
            if name in ("开始阅读", "立即阅读", "听书"):
                continue
            seen.add(href)
            chapters.append(
                {
                    "id": chap_id,
                    "name": name,
                    "url": href if href.startswith("/") else f"/{book_id}/{chap_id}",
                    "book_id": book_id,
                }
            )
        return chapters

    def resolve_read(self, chap: dict, comic: dict | None = None) -> list[str]:
        """返回章节正文段落列表（已清洗）。"""
        url = chap.get("url")
        if not url:
            book_id = chap.get("book_id") or (comic or {}).get("id")
            chap_id = chap.get("id")
            if book_id and chap_id:
                url = f"/{book_id}/{chap_id}"
            else:
                return []
        soup = self._get(url, pc=True)
        body = (
            soup.select_one("#bodybox")
            or soup.select_one("#content")
            or soup.select_one(".content-body")
        )
        if not body:
            return []
        paragraphs: list[str] = []
        for p in body.find_all("p"):
            text = p.get_text(separator="", strip=True)
            if not text:
                continue
            cleaned = re.sub(r"\s+", " ", text).strip()
            if len(cleaned) < 2:
                continue
            paragraphs.append(cleaned)
        if not paragraphs:
            raw = body.get_text(separator="\n", strip=True)
            for line in raw.splitlines():
                line = line.strip()
                if line:
                    paragraphs.append(line)
        return paragraphs
