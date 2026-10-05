# https://github.com/SvnFrs/shadow-bridge/blob/cbb3ee114900718863861ac8bbe9b00481606dcc/src/providers/annas.ts
# https://github.com/calibrain/shelfmark/blob/93210960326f99d731b3f3f91722cf2ebebf1bfd/shelfmark/release_sources/direct_download/annas_archive.py
# Because two human verifications are required when searching, users must wait half a minute before clicking the download button, and download speeds are virtually zero for non-donating users.
"""Anna's Archive provider.

Search scrapes /search HTML (shadow-bridge style).
Download: ANNAS_SECRET_KEY → fast API; else partner / slow links on md5 page.
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup

from downloadutil import download_file
from envutil import load_dotenv

load_dotenv()

MIRRORS = [
    "https://annas-archive.li",
    "https://annas-archive.gl",
    "https://annas-archive.gd",
    "https://annas-archive.pk",
    "https://annas-archive.gs",
    "https://annas-archive.se",
    "https://annas-archive.org",
]

DEFAULT_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


class Provider:
    name = "anna"

    def __init__(self, base_url: str | None = None) -> None:
        load_dotenv()
        self.base_url = (base_url or os.environ.get("ANNAS_BASE_URL") or "").rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": DEFAULT_UA,
                "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
        self._secret = (
            os.environ.get("ANNAS_SECRET_KEY")
            or os.environ.get("ANNAS_ARCHIVE_KEY")
            or ""
        ).strip()
        self._file_cache: dict[str, Path] = {}
        self._cache_dir = Path(
            os.environ.get("PUB_CACHE")
            or (Path(tempfile.gettempdir()) / "pub-epub-cache")
        )
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def _mirrors(self) -> list[str]:
        out: list[str] = []
        if self.base_url:
            out.append(self.base_url)
        for m in MIRRORS:
            if m not in out:
                out.append(m)
        return out

    def _get_html(self, url: str, timeout: float = 15) -> str:
        r = self.session.get(url, timeout=timeout, allow_redirects=True)
        r.raise_for_status()
        text = r.text
        head = text[:2500].lower()
        if (
            "cf-browser-verification" in head
            or "just a moment" in head
            or "ddos-guard" in head
            or "<title>loading...</title>" in head
        ):
            raise RuntimeError("challenge")
        return text

    def _parse_search(self, html: str, base: str, limit: int) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        out: list[dict] = []
        seen: set[str] = set()

        for a in soup.select('a[href*="/md5/"]'):
            href = a.get("href") or ""
            m = re.search(r"/md5/([a-f0-9]{32})", href, flags=re.I)
            if not m:
                continue
            md5 = m.group(1).lower()
            if md5 in seen:
                continue

            title = ""
            for sel in ("h3", ".line-clamp-2", "h2", "h1"):
                el = a.select_one(sel)
                if el:
                    title = _norm(el.get_text(" ", strip=True))
                    if title:
                        break
            if not title:
                # prefer first non-meta line of link text
                lines = [
                    _norm(x)
                    for x in a.get_text("\n", strip=True).splitlines()
                    if _norm(x)
                ]
                title = lines[0] if lines else ""
            if not title or len(title) < 3:
                continue

            author_el = a.select_one("div.italic, .italic")
            author = _norm(author_el.get_text(" ", strip=True)) if author_el else ""

            plain = _norm(a.get_text(" ", strip=True))
            fm = re.search(r"\[([a-z0-9]{2,5})\]", plain, flags=re.I)
            ext = (fm.group(1).lower() if fm else "") or "epub"
            sm = re.search(r"(\d+(?:\.\d+)?)\s*(KB|MB|GB)", plain, flags=re.I)
            size = f"{sm.group(1)} {sm.group(2).upper()}" if sm else ""

            seen.add(md5)
            url = href if href.startswith("http") else urljoin(base + "/", href.lstrip("/"))
            out.append(
                {
                    "id": md5,
                    "name": title,
                    "author": author,
                    "year": "",
                    "extension": ext,
                    "size": size,
                    "language": "",
                    "hash": md5,
                    "cover": "",
                    "md5": md5,
                    "url": url,
                    "readOnlineUrl": "",
                    "remark": " · ".join(p for p in (ext.upper(), size, author) if p),
                    "base_url": base,
                }
            )
            if len(out) >= limit:
                break

        # regex fallback if soup found nothing (markup drift)
        if not out:
            for m in re.finditer(r'href="(/md5/([a-f0-9]{32}))"', html, flags=re.I):
                href, md5 = m.group(1), m.group(2).lower()
                if md5 in seen:
                    continue
                start = max(0, m.start() - 1000)
                chunk = html[start : m.end() + 400]
                tm = re.search(r"<h3[^>]*>(.*?)</h3>", chunk, flags=re.I | re.S)
                title = _norm(re.sub(r"<[^>]+>", " ", tm.group(1))) if tm else ""
                if not title or len(title) < 3:
                    continue
                plain = _norm(re.sub(r"<[^>]+>", " ", chunk))
                fm = re.search(r"\[([a-z0-9]{2,5})\]", plain, flags=re.I)
                ext = (fm.group(1).lower() if fm else "") or "epub"
                sm = re.search(r"(\d+(?:\.\d+)?)\s*(KB|MB|GB)", plain, flags=re.I)
                size = f"{sm.group(1)} {sm.group(2).upper()}" if sm else ""
                seen.add(md5)
                out.append(
                    {
                        "id": md5,
                        "name": title,
                        "author": "",
                        "year": "",
                        "extension": ext,
                        "size": size,
                        "language": "",
                        "hash": md5,
                        "cover": "",
                        "md5": md5,
                        "url": urljoin(base + "/", href.lstrip("/")),
                        "readOnlineUrl": "",
                        "remark": " · ".join(p for p in (ext.upper(), size) if p),
                        "base_url": base,
                    }
                )
                if len(out) >= limit:
                    break
        return out

    def search(self, keyword: str, *, limit: int = 30) -> list[dict]:
        q = quote(keyword)
        errors: list[str] = []
        for base in self._mirrors():
            try:
                html = self._get_html(f"{base}/search?q={q}", timeout=8)
            except Exception as e:
                errors.append(f"{base}: {e}")
                continue
            cards = self._parse_search(html, base, limit)
            if cards:
                self.base_url = base
                return cards
            errors.append(f"{base}: 0 results")
        # leave empty; test.py / selector will show no rows
        return []

    def _fast_download_url(self, md5: str, base: str) -> str | None:
        if not self._secret:
            return None
        try:
            r = self.session.get(
                f"{base}/dyn/api/fast_download.json",
                params={
                    "md5": md5,
                    "key": self._secret,
                    "path_index": 0,
                    "domain_index": 0,
                },
                timeout=30,
            )
            data = r.json()
            return data.get("download_url") or data.get("url") or None
        except Exception:
            return None

    def _detail_download_url(self, md5: str, base: str) -> str | None:
        try:
            html = self._get_html(f"{base}/md5/{md5}", timeout=20)
        except Exception:
            return None
        for pat in (
            r'href="(https?://[^"]*library\.lol[^"]*)"',
            r'href="(https?://libgen\.[^"]+)"',
            r'href="(https?://[^"]*ipfs[^"]*)"',
            r'href="(/slow_download/[^"]+)"',
            r'href="(/fast_download/[^"]+)"',
        ):
            m = re.search(pat, html, flags=re.I)
            if m:
                u = m.group(1)
                return u if u.startswith("http") else urljoin(base + "/", u.lstrip("/"))
        return None

    def resolve_file(self, card: dict) -> dict[str, Any]:
        md5 = (card.get("md5") or card.get("id") or card.get("hash") or "").lower()
        if len(md5) != 32:
            raise ValueError("anna card missing md5")
        base = (card.get("base_url") or self.base_url or self._mirrors()[0]).rstrip("/")
        ddl = self._fast_download_url(md5, base) or self._detail_download_url(md5, base)
        if not ddl:
            for b in self._mirrors():
                if b == base:
                    continue
                ddl = self._fast_download_url(md5, b) or self._detail_download_url(md5, b)
                if ddl:
                    break
        if not ddl:
            raise RuntimeError(
                "no download link (set ANNAS_SECRET_KEY or open md5 page manually)"
            )
        title = card.get("name") or "book"
        ext = (card.get("extension") or "epub").lower()
        return {
            "kind": "download",
            "url": ddl,
            "downloadLink": ddl,
            "extension": ext,
            "title": title,
            "author": card.get("author") or "",
            "filename": f"{title}.{ext}",
            "card": card,
        }

    def ensure_file(self, card: dict) -> Path:
        md5 = (card.get("md5") or card.get("id") or "").lower()
        ext = (card.get("extension") or "epub").lower()
        if ext == "epub3":
            ext = "epub"
        key = f"anna-{md5}.{ext}"
        cached = self._file_cache.get(key)
        if cached and cached.is_file():
            return cached
        disk = self._cache_dir / key
        if disk.is_file() and disk.stat().st_size > 0:
            self._file_cache[key] = disk
            return disk
        meta = self.resolve_file(card)
        ddl = meta["downloadLink"]
        download_file(
            ddl,
            disk,
            headers={"User-Agent": DEFAULT_UA},
            session=self.session,
            min_bytes=1000,
        )
        self._file_cache[key] = disk
        return disk

    def ensure_epub(self, card: dict) -> Path:
        from epub_spine import open_epub

        ext = (card.get("extension") or "epub").lower()
        if ext not in ("epub", "epub3"):
            raise ValueError(f"ensure_epub requires EPUB, got .{ext}")
        path = self.ensure_file(card)
        open_epub(path, title_hint=card.get("name") or "")
        return path

    def iter_sections(self, card: dict):
        from epub_spine import open_epub
        from pdf_util import page_count

        ext = (card.get("extension") or "epub").lower()
        if ext == "pdf":
            path = self.ensure_file(card)
            n = page_count(path)
            for i in range(n):
                yield {
                    "name": f"Page {i + 1}",
                    "index": i,
                    "path": str(path),
                    "id": str(card.get("id") or ""),
                    "title": card.get("name") or "",
                    "card": card,
                    "kind": "pdf",
                }
            return

        path = self.ensure_epub(card)
        book = open_epub(path, title_hint=card.get("name") or "")
        try:
            for i, href in enumerate(book.spine):
                name = book.labels[i] if i < len(book.labels) else f"§ {i + 1}"
                yield {
                    "name": name,
                    "index": i,
                    "href": href,
                    "path": str(path),
                    "id": str(card.get("id") or ""),
                    "title": book.title,
                    "card": card,
                    "kind": "epub",
                }
        finally:
            book.close()

    def get_sections(self, card: dict) -> list[dict]:
        return list(self.iter_sections(card))

    def resolve_read(self, section: dict) -> dict[str, Any]:
        if section.get("kind") == "pdf":
            return {
                "kind": "pdf",
                "index": int(section.get("index", 0)),
                "path": section.get("path"),
                "name": section.get("name"),
            }
        from epub_spine import open_epub

        path = section.get("path") or str(self.ensure_epub(section.get("card") or {}))
        index = int(section.get("index", 0))
        book = open_epub(path, title_hint=section.get("title") or "")
        try:
            payload = book.section_payload(index)
        finally:
            book.close()
        payload["index"] = index
        payload["name"] = section.get("name") or payload.get("title")
        payload["path"] = path
        return payload
