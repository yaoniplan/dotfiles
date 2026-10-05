"""OPDS / Atom catalog provider (bookdrop-style).

Built-in sources: Project Gutenberg, Standard Ebooks, textos.info.
Override with env:
  OPDS_SOURCES=gutenberg,standardebooks
  OPDS_SEARCH_URL='https://example.org/search.opds?q=%s'  # single custom catalog
"""

from __future__ import annotations

import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import re
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin, urlparse
from xml.etree import ElementTree as ET

import requests

from downloadutil import download_file
from envutil import load_dotenv

load_dotenv()

ATOM = "{http://www.w3.org/2005/Atom}"
OPDS_NS = "{http://opds-spec.org/2010/catalog}"
DC = "{http://purl.org/dc/terms/}"

DEFAULT_UA = "pub-opds/0.1 (+https://github.com/local/pub)"

# bookdrop-compatible defaults
SOURCES: dict[str, dict[str, str]] = {
    "gutenberg": {
        "name": "Project Gutenberg",
        "search": "https://www.gutenberg.org/ebooks/search.opds/?query=%s",
    },
    "standardebooks": {
        "name": "Standard Ebooks",
        "search": "https://standardebooks.org/feeds/opds/all?query=%s&per-page=25&page=1",
    },
    "textos": {
        "name": "textos.info",
        "search": "https://www.textos.info/busqueda.atom?query=%s",
    },
}

FORMAT_ORDER = ("epub", "azw3", "mobi", "pdf", "txt", "djvu", "cbz")
MIME_EXT = {
    "application/epub+zip": "epub",
    "application/x-mobipocket-ebook": "mobi",
    "application/pdf": "pdf",
    "text/plain": "txt",
    "image/vnd.djvu": "djvu",
    "application/x-cbz": "cbz",
}


def _text(el: ET.Element | None) -> str:
    if el is None or el.text is None:
        return ""
    return re.sub(r"\s+", " ", el.text).strip()


def _child(el: ET.Element, tag: str) -> ET.Element | None:
    # Do not use `or` on Elements — empty nodes are falsy in ElementTree.
    found = el.find(f"{ATOM}{tag}")
    if found is not None:
        return found
    return el.find(tag)


def _children(el: ET.Element, tag: str) -> list[ET.Element]:
    out = el.findall(f"{ATOM}{tag}")
    if not out:
        out = el.findall(tag)
    return list(out)


def _itertext(el: ET.Element | None) -> str:
    if el is None:
        return ""
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip()


def _ext_from_link(typ: str, href: str, title: str = "") -> str | None:
    typ = (typ or "").lower()
    href_l = (href or "").lower().split("?")[0]
    title_l = (title or "").lower()
    for mime, ext in MIME_EXT.items():
        if mime in typ:
            return ext
    for ext in FORMAT_ORDER:
        if f".{ext}" in href_l or ext in typ or ext in title_l:
            return ext
    if "epub" in typ or "epub" in href_l:
        return "epub"
    return None


def _acq_score(ext: str, title: str, typ: str) -> int:
    score = FORMAT_ORDER.index(ext) if ext in FORMAT_ORDER else 50
    t = (title or "").lower() + " " + (typ or "").lower()
    if "noimages" in t or "none" in t:
        score += 3
    if "epub3" in t or "images" in t:
        score -= 1
    if ext == "epub":
        score -= 2
    return score


class Provider:
    name = "opds"

    def __init__(self, sources: list[str] | None = None) -> None:
        load_dotenv()
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": DEFAULT_UA,
                "Accept": "application/atom+xml,application/xml,text/xml,*/*;q=0.8",
            }
        )
        custom = (os.environ.get("OPDS_SEARCH_URL") or "").strip()
        if custom:
            self._source_list = [("custom", {"name": "OPDS", "search": custom})]
        else:
            names = sources
            if not names:
                env = (os.environ.get("OPDS_SOURCES") or "gutenberg,standardebooks").strip()
                names = [x.strip() for x in env.split(",") if x.strip()]
            self._source_list = []
            for n in names:
                if n in SOURCES:
                    self._source_list.append((n, SOURCES[n]))
            if not self._source_list:
                self._source_list = [("gutenberg", SOURCES["gutenberg"])]

        self._file_cache: dict[str, Path] = {}
        self._cache_dir = Path(
            os.environ.get("PUB_CACHE")
            or (Path(tempfile.gettempdir()) / "pub-epub-cache")
        )
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def _fetch_xml(self, url: str, timeout: float = 20) -> ET.Element:
        r = self.session.get(url, timeout=timeout)
        r.raise_for_status()
        return ET.fromstring(r.content)

    def _parse_acquisitions(
        self, entry: ET.Element, base_url: str
    ) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        for link in _children(entry, "link"):
            rel = link.attrib.get("rel") or ""
            if "acquisition" not in rel:
                continue
            href = link.attrib.get("href") or ""
            if not href:
                continue
            href = urljoin(base_url, href)
            typ = link.attrib.get("type") or ""
            title = link.attrib.get("title") or ""
            ext = _ext_from_link(typ, href, title)
            if not ext:
                continue
            found.append(
                {
                    "url": href,
                    "extension": ext,
                    "type": typ,
                    "title": title,
                    "score": _acq_score(ext, title, typ),
                }
            )
        found.sort(key=lambda x: x["score"])
        return found

    def _entry_to_card(
        self,
        entry: ET.Element,
        *,
        base_url: str,
        source_id: str,
        source_name: str,
    ) -> dict | None:
        title = _itertext(_child(entry, "title"))
        if not title:
            return None

        authors = []
        for a in _children(entry, "author"):
            name = _itertext(_child(a, "name")) or _itertext(a)
            if name:
                authors.append(name)
        author = ", ".join(authors)

        entry_id = _text(_child(entry, "id")) or title
        year = ""
        for tag in ("issued", "published", "updated"):
            el = entry.find(f"{DC}{tag}") or _child(entry, tag)
            if el is not None and el.text:
                m = re.search(r"(19|20)\d{2}", el.text)
                if m:
                    year = m.group(0)
                    break

        acquisitions = self._parse_acquisitions(entry, base_url)

        # Gutenberg: search hits are often catalog subsections → follow once
        if not acquisitions:
            for link in _children(entry, "link"):
                rel = link.attrib.get("rel") or ""
                typ = (link.attrib.get("type") or "").lower()
                href = link.attrib.get("href") or ""
                if not href:
                    continue
                if rel in ("subsection", "alternate", "http://opds-spec.org/acquisition/open-access") or (
                    "opds" in typ and href.endswith(".opds")
                ):
                    try:
                        sub_url = urljoin(base_url, href)
                        root = self._fetch_xml(sub_url, timeout=6)
                        # feed with entries, or single entry document
                        sub_entries = root.findall(f"{ATOM}entry") or root.findall("entry")
                        if not sub_entries and (root.tag.endswith("entry") or root.tag == "entry"):
                            sub_entries = [root]
                        for se in sub_entries:
                            acq = self._parse_acquisitions(se, sub_url)
                            if acq:
                                acquisitions = acq
                                # prefer title from detail if richer
                                t2 = _itertext(_child(se, "title"))
                                if t2:
                                    title = t2
                                entry_id = _text(_child(se, "id")) or entry_id
                                break
                        if acquisitions:
                            break
                    except Exception:
                        continue

        if not acquisitions:
            return None

        best = acquisitions[0]
        ext = best["extension"]
        hid = hashlib.sha1(f"{source_id}:{entry_id}:{ext}".encode()).hexdigest()[:16]

        return {
            "id": hid,
            "name": title,
            "author": author,
            "year": year,
            "extension": ext,
            "size": "",
            "language": "",
            "hash": hid,
            "cover": "",
            "url": entry_id if entry_id.startswith("http") else base_url,
            "downloadUrl": best["url"],
            "downloadLinks": [a["url"] for a in acquisitions],
            "readOnlineUrl": "",
            "remark": " · ".join(
                p for p in (ext.upper(), source_name, year, author) if p
            ),
            "source": source_id,
            "opds_id": entry_id,
        }

    def _resolve_entry(
        self,
        entry: ET.Element,
        *,
        base_url: str,
        source_id: str,
        source_name: str,
    ) -> dict | None:
        return self._entry_to_card(
            entry,
            base_url=base_url,
            source_id=source_id,
            source_name=source_name,
        )

    def search(self, keyword: str, *, limit: int = 30) -> list[dict]:
        """Search OPDS sources; resolve Gutenberg-style subsections in parallel."""
        out: list[dict] = []
        seen: set[str] = set()
        q = quote(keyword)
        jobs: list[tuple] = []

        # 1) Fetch all source feeds (parallel)
        def fetch_source(item: tuple[str, dict]):
            source_id, cfg = item
            tmpl = cfg["search"]
            try:
                url = tmpl % q if "%s" in tmpl else tmpl.replace("{query}", q)
            except TypeError:
                url = tmpl.format(query=q)
            try:
                root = self._fetch_xml(url, timeout=10)
            except Exception:
                return source_id, cfg, None, None
            base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
            entries = root.findall(f"{ATOM}entry") or root.findall("entry")
            return source_id, cfg, base, entries

        feed_results = []
        with ThreadPoolExecutor(max_workers=max(1, len(self._source_list))) as pool:
            futs = [pool.submit(fetch_source, s) for s in self._source_list]
            for fut in as_completed(futs):
                try:
                    feed_results.append(fut.result())
                except Exception:
                    continue

        # 2) Resolve entries (subsection follow) in parallel — main cost on Gutenberg
        tasks: list[tuple] = []
        for source_id, cfg, base, entries in feed_results:
            if base is None or not entries:
                continue
            name = cfg.get("name") or source_id
            for entry in entries:
                tasks.append((entry, base, source_id, name))

        if not tasks:
            return []

        workers = min(12, max(4, len(tasks)))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = {
                pool.submit(
                    self._resolve_entry,
                    entry,
                    base_url=base,
                    source_id=source_id,
                    source_name=name,
                ): i
                for i, (entry, base, source_id, name) in enumerate(tasks)
            }
            for fut in as_completed(futs):
                if len(out) >= limit:
                    break
                try:
                    card = fut.result()
                except Exception:
                    continue
                if not card:
                    continue
                key = (card.get("opds_id") or "") + "|" + (card.get("extension") or "")
                if key in seen:
                    continue
                seen.add(key)
                out.append(card)
                if len(out) >= limit:
                    break
        return out[:limit]

    def resolve_file(self, card: dict) -> dict[str, Any]:
        urls = list(card.get("downloadLinks") or [])
        if card.get("downloadUrl"):
            urls = [card["downloadUrl"]] + [u for u in urls if u != card["downloadUrl"]]
        if not urls:
            raise RuntimeError("opds card has no acquisition link")
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
        book_id = str(card.get("id") or card.get("hash") or "opds")
        ext = (card.get("extension") or "epub").lower()
        if ext == "epub3":
            ext = "epub"
        key = f"opds-{book_id}.{ext}"
        cached = self._file_cache.get(key)
        if cached and cached.is_file():
            return cached
        disk = self._cache_dir / key
        if disk.is_file() and disk.stat().st_size > 1000:
            self._file_cache[key] = disk
            return disk

        meta = self.resolve_file(card)
        last_err: Exception | None = None
        for ddl in meta.get("downloadLinks") or [meta["downloadLink"]]:
            try:
                download_file(
                    ddl,
                    disk,
                    headers={"User-Agent": DEFAULT_UA},
                    session=self.session,
                    min_bytes=1000,
                )
                self._file_cache[key] = disk
                return disk
            except Exception as e:
                last_err = e
                disk.unlink(missing_ok=True)
        raise RuntimeError(f"opds download failed: {last_err}")

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
