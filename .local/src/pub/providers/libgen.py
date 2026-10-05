"""Library Genesis provider (libgen.li-style search + ads.php download)."""

from __future__ import annotations

import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup

from downloadutil import download_file
from envutil import load_dotenv

load_dotenv()

MIRRORS = [
    "https://libgen.li",
    "https://libgen.vg",
    "https://libgen.la",
    "https://libgen.bz",
    "https://libgen.gl",
    "https://libgen.is",
    "https://libgen.rs",
    "https://libgen.st",
]

DEFAULT_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _looks_like_book(path: Path, ext: str) -> bool:
    """Reject HTML error pages saved as .epub/.pdf."""
    try:
        if not path.is_file() or path.stat().st_size < 10_000:
            return False
        head = path.read_bytes()[:8]
    except OSError:
        return False
    e = (ext or "").lower()
    if e == "pdf":
        return head.startswith(b"%PDF")
    if e in ("epub", "epub3", "zip"):
        return head.startswith(b"PK")
    # mobi/azw often start with various magic; accept non-HTML
    if head.lstrip().startswith(b"<") or head.lstrip().startswith(b"<!DOCTYPE"):
        return False
    return True


class Provider:
    name = "libgen"

    def __init__(self, base_url: str | None = None) -> None:
        load_dotenv()
        self.base_url = (base_url or os.environ.get("LIBGEN_BASE_URL") or "").rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": DEFAULT_UA,
                "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
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

    def _get_html(self, url: str, timeout: float = 12) -> str:
        r = self.session.get(url, timeout=timeout, allow_redirects=True)
        if r.status_code == 503:
            raise RuntimeError("503")
        r.raise_for_status()
        text = r.text
        head = text[:2000].lower()
        if "cf-browser-verification" in head or "just a moment" in head:
            raise RuntimeError("cloudflare")
        return text

    def search(self, keyword: str, *, limit: int = 30) -> list[dict]:
        q = quote(keyword)
        for base in self._mirrors():
            for path in (
                f"/index.php?req={q}&columns%5B%5D=t&columns%5B%5D=a&objects%5B%5D=f&objects%5B%5D=e&objects%5B%5D=s&objects%5B%5D=a&objects%5B%5D=p&objects%5B%5D=w&topics%5B%5D=l&topics%5B%5D=c&topics%5B%5D=f&topics%5B%5D=a&topics%5B%5D=m&topics%5B%5D=r&topics%5B%5D=s&res=25&filesuns=all",
                f"/index.php?req={q}",
                f"/search.php?req={q}&open=0&res=25&view=simple&phrase=1&column=def",
            ):
                try:
                    html = self._get_html(urljoin(base + "/", path.lstrip("/")), timeout=12)
                except Exception:
                    continue
                cards = self._parse_table(html, base, limit)
                if not cards:
                    cards = self._parse_loose(html, base, limit)
                if cards:
                    self.base_url = base
                    return cards
        return []

    def _parse_table(self, html: str, base: str, limit: int) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        out: list[dict] = []
        rows = soup.select("table.c tr") or soup.select("table.catalog tr") or soup.select("table tr")
        for tr in rows:
            cols = tr.find_all("td")
            if len(cols) < 5:
                continue
            title = ""
            author = ""
            year = ""
            size = ""
            ext = ""
            href = ""
            md5 = ""
            dl = ""
            texts = [_norm(c.get_text(" ", strip=True)) for c in cols]

            for c in cols[:3]:
                for a in c.find_all("a"):
                    t = _norm(a.get_text(" ", strip=True))
                    h = a.get("href") or ""
                    if t and len(t) > 2 and not t.isdigit() and (
                        "edition.php" in h or "md5=" in h or "book" in h or "ads.php" in h
                    ):
                        title = t
                        href = h
                        break
                if title:
                    break
            if not title and len(cols) > 2:
                a = cols[2].find_all("a")
                if a:
                    title = _norm(a[-1].get_text(" ", strip=True))
                    href = a[-1].get("href") or ""
            if not title or title.lower() in ("libgen", "search", "show covers"):
                continue

            if len(cols) > 1:
                author = texts[1]
                if author == title:
                    author = texts[2] if len(texts) > 2 else ""

            for t in texts:
                if not size:
                    sm = re.search(r"\d+(?:\.\d+)?\s*(KB|MB|GB)", t, re.I)
                    if sm:
                        size = sm.group(0)
                if re.fullmatch(r"[a-z0-9]{2,5}", t, re.I) and t.lower() in (
                    "epub", "pdf", "mobi", "azw3", "djvu", "txt", "zip", "rar", "fb2"
                ):
                    ext = t.lower()
                if re.fullmatch(r"(19|20)\d{2}", t):
                    year = t

            for c in cols:
                for a in c.find_all("a"):
                    h = a.get("href") or ""
                    m = re.search(r"md5=([a-f0-9]{32})", h, re.I)
                    if m and not md5:
                        md5 = m.group(1).lower()
                    m2 = re.search(r"/book/([a-f0-9]{32})", h, re.I)
                    if m2 and not md5:
                        md5 = m2.group(1).lower()
                    if any(x in h.lower() for x in ("ads.php", "get.php", "library.lol", "/file.php")):
                        if not dl:
                            dl = h if h.startswith("http") else urljoin(base + "/", h.lstrip("/"))

            if not href and md5:
                href = f"ads.php?md5={md5}"
            detail = href if href.startswith("http") else urljoin(base + "/", (href or "").lstrip("/"))

            out.append(
                {
                    "id": md5 or title[:32],
                    "name": title,
                    "author": author,
                    "year": year,
                    "extension": ext or "epub",
                    "size": size,
                    "language": "",
                    "hash": md5,
                    "cover": "",
                    "url": detail,
                    "downloadUrl": dl,
                    "readOnlineUrl": "",
                    "remark": " · ".join(p for p in ((ext or "").upper(), size, year, author) if p),
                    "base_url": base,
                }
            )
            if len(out) >= limit:
                break
        return out

    def _parse_loose(self, html: str, base: str, limit: int) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        out: list[dict] = []
        for a in soup.select('a[href*="md5="], a[href*="/book/index.php"]'):
            title = _norm(a.get_text(" ", strip=True))
            if not title or len(title) < 3:
                continue
            href = a.get("href") or ""
            md5 = ""
            m = re.search(r"md5=([a-f0-9]{32})", href, re.I)
            if m:
                md5 = m.group(1).lower()
            url = href if href.startswith("http") else urljoin(base + "/", href.lstrip("/"))
            out.append(
                {
                    "id": md5 or title[:32],
                    "name": title,
                    "author": "",
                    "year": "",
                    "extension": "epub",
                    "size": "",
                    "language": "",
                    "hash": md5,
                    "cover": "",
                    "url": url,
                    "downloadUrl": "",
                    "readOnlineUrl": "",
                    "remark": "",
                    "base_url": base,
                }
            )
            if len(out) >= limit:
                break
        return out

    def _collect_download_urls(self, card: dict) -> list[str]:
        base = (card.get("base_url") or self.base_url or self._mirrors()[0]).rstrip("/")
        md5 = (card.get("hash") or card.get("id") or "").lower()
        primary: list[str] = []
        secondary: list[str] = []
        seen: set[str] = set()

        def add(u: str, *, prefer: bool = False) -> None:
            if not u:
                return
            if not u.startswith("http"):
                u = urljoin(base + "/", u.lstrip("/"))
            u = u.replace("&amp;", "&")
            if u in seen:
                return
            seen.add(u)
            low = u.lower()
            # file.php alone is often an HTML interstitial — resolve later
            if prefer or "get.php" in low or "library.lol" in low:
                primary.append(u)
            else:
                secondary.append(u)

        def harvest(html: str, page_base: str) -> None:
            for mm in re.finditer(
                r'href=["\']([^"\']*get\.php\?md5=[a-f0-9]{32}[^"\']*)["\']',
                html,
                flags=re.I,
            ):
                u = mm.group(1)
                if not u.startswith("http"):
                    u = urljoin(page_base + "/", u.lstrip("/"))
                add(u, prefer=True)
            for mm in re.finditer(
                r'href=["\'](https?://[^"\']*library\.lol[^"\']*)["\']',
                html,
                flags=re.I,
            ):
                add(mm.group(1), prefer=True)
            for mm in re.finditer(
                r'href=["\']([^"\']*file\.php\?[^"\']+)["\']',
                html,
                flags=re.I,
            ):
                u = mm.group(1)
                if not u.startswith("http"):
                    u = urljoin(page_base + "/", u.lstrip("/"))
                add(u, prefer=False)

        add(card.get("downloadUrl") or "")

        # ads.php on several mirrors
        detail_pages: list[str] = []
        if md5 and len(md5) == 32:
            for b in [base] + [x for x in self._mirrors() if x != base][:4]:
                detail_pages.append(f"{b}/ads.php?md5={md5}")
                # library.lol classic
                detail_pages.append(f"http://library.lol/main/{md5}")
                detail_pages.append(f"https://library.lol/main/{md5}")
        u0 = (card.get("url") or "").strip()
        if u0:
            detail_pages.append(
                u0 if u0.startswith("http") else urljoin(base + "/", u0.lstrip("/"))
            )

        file_php_pages: list[str] = []
        for detail in detail_pages:
            try:
                html = self._get_html(detail, timeout=12)
            except Exception:
                continue
            page_base = detail.rsplit("/", 1)[0]
            # if this is already a host root path
            from urllib.parse import urlparse as _up

            page_base = f"{_up(detail).scheme}://{_up(detail).netloc}"
            harvest(html, page_base)
            # collect file.php to resolve
            for mm in re.finditer(
                r'href=["\']([^"\']*file\.php\?[^"\']+)["\']', html, flags=re.I
            ):
                u = mm.group(1)
                if not u.startswith("http"):
                    u = urljoin(page_base + "/", u.lstrip("/"))
                if u not in file_php_pages:
                    file_php_pages.append(u)
            if primary:
                break

        # Resolve file.php pages → often contain get.php or direct CDN link
        for fp in file_php_pages[:4]:
            try:
                html = self._get_html(fp, timeout=12)
            except Exception:
                continue
            from urllib.parse import urlparse as _up

            page_base = f"{_up(fp).scheme}://{_up(fp).netloc}"
            harvest(html, page_base)
            # meta refresh / window.location
            for mm in re.finditer(
                r'(?:content=["\']\d+;\s*url=|location(?:\.href)?\s*=\s*["\'])([^"\']+)',
                html,
                flags=re.I,
            ):
                add(mm.group(1), prefer=True)

        # IPFS last
        ipfs_gateways = (
            "https://cloudflare-ipfs.com/ipfs/",
            "https://gateway.pinata.cloud/ipfs/",
            "https://dweb.link/ipfs/",
            "https://ipfs.io/ipfs/",
        )
        expanded: list[str] = []
        for u in secondary:
            if "file.php" in u.lower():
                continue  # never download file.php HTML as book
            m_cid = re.search(r"/ipfs/([a-zA-Z0-9]+)", u)
            if m_cid:
                cid = m_cid.group(1)
                for g in ipfs_gateways:
                    cand = g + cid
                    if cand not in seen:
                        seen.add(cand)
                        expanded.append(cand)
            else:
                expanded.append(u)

        return primary + expanded

    def resolve_file(self
, card: dict) -> dict[str, Any]:
        urls = self._collect_download_urls(card)
        if not urls:
            raise RuntimeError("no download link on detail page")
        title = card.get("name") or "book"
        ext = (card.get("extension") or "epub").lower()
        return {
            "kind": "download",
            "url": urls[0],
            "downloadLink": urls[0],
            "downloadLinks": urls,
            "extension": ext,
            "title": title,
            "author": card.get("author") or "",
            "filename": f"{title}.{ext}",
            "card": card,
        }

    def ensure_file(self, card: dict) -> Path:
        book_id = str(card.get("id") or card.get("hash") or "x")
        ext = (card.get("extension") or "epub").lower()
        if ext == "epub3":
            ext = "epub"
        key = f"libgen-{book_id}.{ext}"
        disk = self._cache_dir / key
        if disk.is_file() and not _looks_like_book(disk, ext):
            disk.unlink(missing_ok=True)
        cached = self._file_cache.get(key)
        if cached and cached.is_file() and _looks_like_book(cached, ext):
            return cached
        if disk.is_file() and _looks_like_book(disk, ext):
            self._file_cache[key] = disk
            return disk

        md5 = (card.get("hash") or card.get("id") or "").lower()
        if not md5 or len(md5) != 32:
            # fall back to pre-collected links
            return self._ensure_from_candidates(card, disk, key, ext)

        last_err: Exception | None = None
        bases = []
        b0 = (card.get("base_url") or self.base_url or "").rstrip("/")
        if b0:
            bases.append(b0)
        for b in self._mirrors():
            if b not in bases:
                bases.append(b)

        for base in bases:
            ads = f"{base}/ads.php?md5={md5}"
            try:
                html = self._get_html(ads, timeout=12)
            except Exception as e:
                last_err = e
                continue
            # relative get.php?md5=...&key=... on THIS host only
            gets: list[str] = []
            for mm in re.finditer(
                r'href=["\']([^"\']*get\.php\?md5=' + re.escape(md5) + r'[^"\']*)["\']',
                html,
                flags=re.I,
            ):
                u = mm.group(1).replace("&amp;", "&")
                if not u.startswith("http"):
                    u = urljoin(base + "/", u.lstrip("/"))
                if u not in gets:
                    gets.append(u)
            # also any get.php with key
            if not gets:
                for mm in re.finditer(
                    r'href=["\']([^"\']*get\.php\?md5=[a-f0-9]{32}[^"\']*key=[A-Za-z0-9]+)["\']',
                    html,
                    flags=re.I,
                ):
                    u = mm.group(1).replace("&amp;", "&")
                    if not u.startswith("http"):
                        u = urljoin(base + "/", u.lstrip("/"))
                    if u not in gets:
                        gets.append(u)

            for ddl in gets:
                try:
                    headers = {
                        "User-Agent": DEFAULT_UA,
                        "Referer": f"{base}/",
                    }
                    download_file(
                        ddl,
                        disk,
                        headers=headers,
                        session=self.session,
                        min_bytes=10_000,
                    )
                    if not _looks_like_book(disk, ext):
                        last_err = RuntimeError(f"not a book file from {ddl}")
                        disk.unlink(missing_ok=True)
                        continue
                    self._file_cache[key] = disk
                    return disk
                except Exception as e:
                    last_err = e
                    disk.unlink(missing_ok=True)
                    continue

        # last resort: other candidates (ipfs, library.lol resolved links)
        try:
            return self._ensure_from_candidates(card, disk, key, ext)
        except Exception as e:
            last_err = e
        raise RuntimeError(f"download failed: {last_err}")

    def _ensure_from_candidates(
        self, card: dict, disk: Path, key: str, ext: str
    ) -> Path:
        meta = self.resolve_file(card)
        candidates = meta.get("downloadLinks") or [meta["downloadLink"]]
        last_err: Exception | None = None
        for ddl in candidates[:10]:
            if "file.php" in ddl.lower():
                continue
            try:
                from urllib.parse import urlparse

                p = urlparse(ddl)
                origin = f"{p.scheme}://{p.netloc}" if p.scheme and p.netloc else ""
                headers = {
                    "User-Agent": DEFAULT_UA,
                    "Referer": (origin + "/") if origin else "",
                }
                download_file(
                    ddl,
                    disk,
                    headers=headers,
                    session=self.session,
                    min_bytes=10_000,
                )
                if not _looks_like_book(disk, ext):
                    last_err = RuntimeError(f"not a book file from {ddl}")
                    disk.unlink(missing_ok=True)
                    continue
                self._file_cache[key] = disk
                return disk
            except Exception as e:
                last_err = e
                disk.unlink(missing_ok=True)
                time.sleep(0.2)
        raise RuntimeError(f"download failed: {last_err}")

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
