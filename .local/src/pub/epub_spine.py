"""Minimal EPUB spine access — section-at-a-time (nov-style).

Index from OPF spine only; body + images loaded per section on demand.
"""

from __future__ import annotations

import mimetypes
import posixpath
import re
import zipfile
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote
from xml.etree import ElementTree as ET


def _local(tag: str) -> str:
    if isinstance(tag, str) and "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _join(base: str, href: str) -> str:
    href = href.split("#", 1)[0].split("?", 1)[0]
    if not base or base in (".", "/"):
        return posixpath.normpath(href).lstrip("/")
    return posixpath.normpath(posixpath.join(base, href)).lstrip("/")


class _SectionParser(HTMLParser):
    """Collect visible text + image refs; skip script/style/svg."""

    def __init__(self, section_dir: str):
        super().__init__(convert_charrefs=True)
        self.section_dir = section_dir
        self._chunks: list[str] = []
        self._skip = 0
        self._title: str | None = None
        self._in_title = False
        self.images: list[str] = []  # zip paths
        self._blocks: list[dict] = []  # ordered text|image for HTML rebuild
        self._text_buf: list[str] = []

    def _flush_text(self):
        text = "".join(self._text_buf)
        self._text_buf.clear()
        parts = []
        for block in re.split(r"\n+", text):
            b = re.sub(r" +", " ", block).strip()
            if b:
                parts.append(b)
                self._blocks.append({"type": "text", "text": b})
        return parts

    def handle_starttag(self, tag, attrs):
        t = tag.lower()
        if t in ("script", "style", "svg", "head"):
            self._skip += 1
            return
        if self._skip:
            return
        ad = {k.lower(): v for k, v in attrs}
        if t == "title":
            self._in_title = True
            return
        if t in ("p", "div", "li", "h1", "h2", "h3", "h4", "br", "tr", "section"):
            self._text_buf.append("\n")
        if t in ("img", "image"):
            src = ad.get("src") or ad.get("xlink:href") or ad.get("href")
            if src and not src.startswith(("data:", "http://", "https://")):
                zpath = _join(self.section_dir, src)
                self.images.append(zpath)
                self._flush_text()
                self._blocks.append({"type": "image", "path": zpath})
            elif src and src.startswith("data:"):
                self._flush_text()
                self._blocks.append({"type": "image_data", "src": src})

    def handle_endtag(self, tag):
        t = tag.lower()
        if t in ("script", "style", "svg", "head"):
            self._skip = max(0, self._skip - 1)
            return
        if self._skip:
            return
        if t == "title":
            self._in_title = False
            return
        if t in ("p", "div", "li", "h1", "h2", "h3", "h4", "tr", "section"):
            self._text_buf.append("\n")

    def handle_data(self, data):
        if self._skip:
            return
        if self._in_title:
            self._title = (self._title or "") + data
            return
        if data.strip():
            self._text_buf.append(re.sub(r"[ \t]+", " ", data))

    def finish(self):
        self._flush_text()


@dataclass
class EpubBook:
    path: Path
    title: str
    spine: list[str]
    labels: list[str]
    _zf: zipfile.ZipFile | None = field(default=None, repr=False)

    def section_count(self) -> int:
        return len(self.spine)

    def open_zip(self) -> zipfile.ZipFile:
        if self._zf is None:
            self._zf = zipfile.ZipFile(self.path)
        return self._zf

    def close(self):
        if self._zf is not None:
            self._zf.close()
            self._zf = None

    def resource_bytes(self, zpath: str) -> tuple[bytes, str]:
        """Return (bytes, content-type) for a path inside the epub."""
        z = self.open_zip()
        # try exact + common alternate encodings of path
        candidates = [zpath, zpath.lstrip("/")]
        data = None
        for c in candidates:
            try:
                data = z.read(c)
                zpath = c
                break
            except KeyError:
                continue
        if data is None:
            # case-insensitive fallback
            lower = {n.lower(): n for n in z.namelist()}
            real = lower.get(zpath.lower())
            if not real:
                raise FileNotFoundError(zpath)
            data = z.read(real)
            zpath = real
        ctype, _ = mimetypes.guess_type(zpath)
        if not ctype:
            if zpath.lower().endswith(".svg"):
                ctype = "image/svg+xml"
            else:
                ctype = "application/octet-stream"
        return data, ctype

    def section_payload(self, index: int) -> dict:
        """Title, paragraphs, and HTML with /api/resource image URLs."""
        if index < 0 or index >= len(self.spine):
            raise IndexError(index)
        name = self.spine[index]
        z = self.open_zip()
        raw = z.read(name)
        for enc in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
            try:
                html = raw.decode(enc)
                break
            except UnicodeDecodeError:
                html = None
        else:
            html = raw.decode("utf-8", errors="replace")

        section_dir = posixpath.dirname(name)
        parser = _SectionParser(section_dir)
        try:
            parser.feed(html)
            parser.close()
            parser.finish()
        except Exception:
            plain = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", html)
            plain = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", plain)
            plain = re.sub(r"(?s)<[^>]+>", "\n", plain)
            paras = [p.strip() for p in re.split(r"\n+", plain) if p.strip()]
            label = self.labels[index] if index < len(self.labels) else f"§ {index + 1}"
            return {
                "title": label,
                "paragraphs": paras,
                "html": "".join(f"<p>{_esc(p)}</p>" for p in paras),
                "images": [],
            }

        paras = [b["text"] for b in parser._blocks if b["type"] == "text"]
        label = (
            (parser._title or "").strip()
            or (self.labels[index] if index < len(self.labels) else "")
            or (paras[0][:48] if paras else f"§ {index + 1}")
        )

        parts = []
        for b in parser._blocks:
            if b["type"] == "text":
                parts.append(f"<p>{_esc(b['text'])}</p>")
            elif b["type"] == "image":
                q = quote(b["path"], safe="/")
                parts.append(
                    f'<figure class="img-wrap"><img src="/api/resource?path={q}" alt="" loading="lazy"/></figure>'
                )
            elif b["type"] == "image_data":
                parts.append(
                    f'<figure class="img-wrap"><img src="{b["src"]}" alt="" loading="lazy"/></figure>'
                )

        return {
            "title": label,
            "paragraphs": paras,
            "html": "\n".join(parts),
            "images": parser.images,
        }


def _esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )



def _text_of(el) -> str:
    parts = []
    if el.text:
        parts.append(el.text)
    for c in el:
        parts.append(_text_of(c))
        if c.tail:
            parts.append(c.tail)
    return re.sub(r"\s+", " ", "".join(parts)).strip()


def _toc_labels(z: zipfile.ZipFile, opf, opf_base: str, manifest: dict[str, str], spine: list[str]) -> list[str]:
    """Map spine entries to human titles from EPUB3 nav or EPUB2 NCX."""
    labels = [""] * len(spine)
    index_by_path: dict[str, int] = {}
    for i, p in enumerate(spine):
        index_by_path[p] = i
        index_by_path[posixpath.basename(p)] = i

    def assign(href: str, label: str):
        if not label:
            return
        href = href.split("#", 1)[0].split("?", 1)[0]
        if not href:
            return
        # try as-is relative to opf, and basename match
        full = _join(opf_base, href)
        for key in (full, href.lstrip("/"), posixpath.basename(href)):
            i = index_by_path.get(key)
            if i is not None and not labels[i]:
                labels[i] = label
                return
        # suffix match
        for i, p in enumerate(spine):
            if not labels[i] and (p.endswith("/" + href) or p.endswith(href)):
                labels[i] = label
                return

    # EPUB3 nav: item properties contains "nav"
    nav_href = None
    for el in opf.iter():
        if _local(el.tag) != "item":
            continue
        props = (el.get("properties") or "").split()
        if "nav" in props:
            nav_href = el.get("href")
            break
        media = (el.get("media-type") or "").lower()
        if media in ("application/xhtml+xml", "text/html") and "nav" in (el.get("id") or "").lower():
            nav_href = el.get("href")

    if nav_href:
        try:
            nav_path = _join(opf_base, nav_href)
            nav_xml = ET.fromstring(z.read(nav_path))
            nav_dir = posixpath.dirname(nav_path)
            for el in nav_xml.iter():
                if _local(el.tag) != "a":
                    continue
                href = el.get("href") or ""
                label = _text_of(el)
                if href and label:
                    # resolve relative to nav file
                    assign_path = _join(nav_dir, href) if not href.startswith("/") else href.lstrip("/")
                    # assign() joins with opf_base — pass path relative tricks
                    for key in (assign_path, _join(opf_base, href), href):
                        assign(key, label)
                    # direct index
                    full = _join(nav_dir, href.split("#", 1)[0])
                    i = index_by_path.get(full)
                    if i is not None and not labels[i]:
                        labels[i] = label
        except Exception:
            pass

    # EPUB2 NCX
    ncx_href = None
    for el in opf.iter():
        if _local(el.tag) == "spine" and el.get("toc"):
            ncx_id = el.get("toc")
            ncx_href = manifest.get(ncx_id)
            break
    if not ncx_href:
        for el in opf.iter():
            if _local(el.tag) != "item":
                continue
            media = (el.get("media-type") or "").lower()
            if media == "application/x-dtbncx+xml" or (el.get("href") or "").endswith(".ncx"):
                ncx_href = el.get("href")
                break
    if ncx_href:
        try:
            ncx_path = _join(opf_base, ncx_href)
            ncx = ET.fromstring(z.read(ncx_path))
            for np in ncx.iter():
                if _local(np.tag) != "navPoint":
                    continue
                label = ""
                src = ""
                for c in np:
                    ln = _local(c.tag)
                    if ln == "navLabel":
                        for t in c.iter():
                            if _local(t.tag) == "text" and (t.text or "").strip():
                                label = (t.text or "").strip()
                                break
                    elif ln == "content":
                        src = c.get("src") or ""
                if label and src:
                    full = _join(posixpath.dirname(ncx_path), src.split("#", 1)[0])
                    i = index_by_path.get(full)
                    if i is not None and not labels[i]:
                        labels[i] = label
                    else:
                        assign(src, label)
        except Exception:
            pass

    # fallback: basename cleaned
    for i, p in enumerate(spine):
        if not labels[i]:
            base = posixpath.splitext(posixpath.basename(p))[0]
            labels[i] = base
    return labels



def _looks_like_filename(label: str) -> bool:
    if not label:
        return True
    if re.search(r"epub_|part\d+|split_\d+|c\d{2}[A-Z]|A\d{3}", label):
        return True
    if re.fullmatch(r"[\w.-]{20,}", label) and "_" in label:
        return True
    return False


def _fill_labels_from_headings(
    z: zipfile.ZipFile, spine: list[str], labels: list[str], book_title: str = ""
) -> list[str]:
    """For spine items still using file-like / book-title labels, derive a heading."""
    out = list(labels)
    bt = (book_title or "").strip()

    def is_book_title(s: str) -> bool:
        s = (s or "").strip()
        if not s:
            return True
        if bt and (s == bt or s.startswith(bt) or bt.startswith(s)):
            return True
        if "Definitive Edition" in s and "Diary" in s:
            return True
        return False

    for i, p in enumerate(spine):
        if out[i] and not _looks_like_filename(out[i]) and not is_book_title(out[i]):
            continue
        try:
            raw = z.read(p)
        except KeyError:
            continue
        try:
            html = raw.decode("utf-8")
        except UnicodeDecodeError:
            html = raw.decode("utf-8", errors="replace")
        m2 = re.search(r"(?is)<h[12][^>]*>(.*?)</h[12]>", html)
        h = ""
        if m2:
            h = re.sub(r"<[^>]+>", "", m2.group(1))
            h = re.sub(r"\s+", " ", h).strip()
            if is_book_title(h):
                h = ""
        plain = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", html)
        plain = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", plain)
        plain = re.sub(r"(?s)<[^>]+>", "\n", plain)
        tokens = []
        for line in plain.splitlines():
            line = re.sub(r"\s+", " ", line).strip()
            if not line or is_book_title(line):
                continue
            tokens.append(line)
        # rejoin letter-split / comma-split tokens (T+UESDAY, ,+A+UGUST)
        merged: list[str] = []
        acc = ""
        for t in tokens:
            if len(t) <= 2 or re.fullmatch(r"[,:;]?\s*[A-Za-z]", t or ""):
                acc += t.replace(" ", "")
                continue
            if acc:
                t = acc + t
                acc = ""
            if merged and re.fullmatch(r"[,:;A-Za-z]{1,3}", merged[-1] or ""):
                merged[-1] = merged[-1] + t
            else:
                merged.append(t)
        if acc:
            if merged:
                merged[-1] = merged[-1] + acc
            else:
                merged.append(acc)
        # prefer a date-like heading when present
        date_re = re.compile(
            r"(?i)\b(mon|tues|wednes|thurs|fri|satur|sun)day\b|\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\b.*\d{4}|\d{1,2},\s*\d{4}"
        )
        first_line = ""
        dated = ""
        for t in merged:
            if is_book_title(t) or _looks_like_filename(t) or len(t) < 3:
                continue
            if not first_line:
                first_line = t[:80]
            if date_re.search(t) and not dated:
                dated = t[:80]
        first_line = dated or first_line
        if first_line:
            first_line = first_line.lstrip(" ,:;.-")
        pick = h or first_line
        if pick and not is_book_title(pick) and len(pick) < 120:
            out[i] = pick
    return out


def open_epub(path: str | Path, title_hint: str = "") -> EpubBook:
    path = Path(path)
    with zipfile.ZipFile(path) as z:
        try:
            container = ET.fromstring(z.read("META-INF/container.xml"))
        except Exception as e:
            raise ValueError(f"not a valid EPUB (container): {e}") from e

        opf_path = None
        for el in container.iter():
            if _local(el.tag) == "rootfile":
                opf_path = el.get("full-path")
                break
        if not opf_path:
            raise ValueError("EPUB missing rootfile")

        opf = ET.fromstring(z.read(opf_path))
        opf_base = posixpath.dirname(opf_path)

        manifest: dict[str, str] = {}
        for el in opf.iter():
            if _local(el.tag) == "item":
                iid, href = el.get("id"), el.get("href")
                if iid and href:
                    manifest[iid] = href

        spine: list[str] = []
        for el in opf.iter():
            if _local(el.tag) != "itemref":
                continue
            if (el.get("linear") or "yes").lower() == "no":
                continue
            href = manifest.get(el.get("idref") or "")
            if not href:
                continue
            full = _join(opf_base, href)
            if full.lower().endswith((".xhtml", ".html", ".htm", ".xml")):
                spine.append(full)

        title = title_hint or ""
        for el in opf.iter():
            if _local(el.tag) == "title" and (el.text or "").strip():
                title = el.text.strip()
                break
        if not title:
            title = path.stem

        labels = _toc_labels(z, opf, opf_base, manifest, spine)
        labels = _fill_labels_from_headings(z, spine, labels, book_title=title)

    if not spine:
        raise ValueError("EPUB has empty spine")

    return EpubBook(path=path, title=title, spine=spine, labels=labels)
