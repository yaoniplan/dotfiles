# https://github.com/keiyoushi/extensions-source/blob/main/src/zh/dm5/src/eu/kanade/tachiyomi/extension/zh/dm5/Dm5.kt
# Because there are too many watermark advertisements (which detract from the visual experience) and it requires payment.
from __future__ import annotations

import re
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

import requests
from bs4 import BeautifulSoup


def _unpack_packer(source: str) -> str:
    """Unpack Dean Edwards' P.A.C.K.E.R. packed JavaScript (DM5 variant)."""
    if "eval(function(p,a,c,k,e" not in source.replace(" ", ""):
        return source
    match = re.search(
        r"}\('(.*?)\',(\d+),(\d+),'(.*?)'\.split\('\|'\)",
        source,
        re.DOTALL,
    )
    if not match:
        match = re.search(
            r'}\("(.*?)",(\d+),(\d+),"(.*?)"\.split\(\'\|\'\)',
            source,
            re.DOTALL,
        )
    if not match:
        raise ValueError("Failed to parse P.A.C.K.E.R. payload")
    payload, radix, count, keywords_s = (
        match.group(1),
        int(match.group(2)),
        int(match.group(3)),
        match.group(4),
    )
    keywords = keywords_s.split("|")

    def js_e(c: int, a: int = radix) -> str:
        prefix = "" if c < a else js_e(c // a, a)
        rem = c % a
        if rem > 35:
            return prefix + chr(rem + 29)
        return prefix + "0123456789abcdefghijklmnopqrstuvwxyz"[rem]

    symbol_map = {}
    for c in range(count - 1, -1, -1):
        key = js_e(c)
        symbol_map[key] = (
            keywords[c] if c < len(keywords) and keywords[c] else key
        )
    result = re.sub(
        r"\b\w+\b", lambda m: symbol_map.get(m.group(0), m.group(0)), payload
    )
    return result.replace("\\'", "'").replace('\\"', '"').replace("\\\\", "\\")


class Provider:
    """动漫屋 (DM5) — HTML + chapterfun.ashx packed JS."""

    name = "dm5"

    def __init__(self, base_url: str = "https://www.dm5.com"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/139.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "zh-TW",
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;q=0.9,"
                    "image/avif,image/webp,image/apng,*/*;q=0.8"
                ),
                "Referer": f"{self.base_url}/",
            }
        )

    # ── internal ──────────────────────────────────────────────────────
    def _get(self, url: str, **kwargs) -> requests.Response:
        if not url.startswith("http"):
            url = urljoin(self.base_url + "/", url.lstrip("/"))
        resp = self.session.get(url, timeout=kwargs.pop("timeout", 15), **kwargs)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp

    def _soup(self, url: str, **kwargs) -> BeautifulSoup:
        return BeautifulSoup(self._get(url, **kwargs).text, "html.parser")

    @staticmethod
    def _extract_id(href: str) -> str:
        if not href:
            return ""
        path = urlparse(href).path.strip("/")
        parts = [p for p in path.split("/") if p]
        return parts[-1] if parts else path

    def _id(self, obj, *keys):
        if isinstance(obj, dict):
            for k in keys:
                if obj.get(k):
                    return str(obj[k])
        return str(obj) if obj else None

    # ── required public API ───────────────────────────────────────────
    def search(self, query: str, limit: int = 21, offset: int = 0) -> list[dict]:
        page = max(1, (offset // max(limit, 1)) + 1)
        url = (
            f"{self.base_url}/search"
            f"?title={requests.utils.quote(query)}&language=1&page={page}"
        )
        soup = self._soup(url)
        out = []
        for el in soup.select("ul.mh-list > li, div.banner_detail_form"):
            a = el.select_one(".title > a") or el.select_one("h2.title > a")
            if not a:
                continue
            href = a.get("href") or ""
            title = a.get_text(strip=True)
            comic_id = self._extract_id(href)
            thumb = None
            img = el.select_one("img")
            if img and img.get("src"):
                thumb = img["src"]
            else:
                cover_p = el.select_one("p.mh-cover")
                if cover_p and cover_p.get("style"):
                    m = re.search(r"url\(([^)]+)\)", cover_p["style"])
                    if m:
                        thumb = m.group(1).strip("'\"")
            out.append(
                {
                    "id": comic_id,
                    "name": title,
                    "cover": thumb,
                    "remark": "",
                    "url": urljoin(self.base_url, href),
                }
            )
            if len(out) >= limit:
                break
        return out

    def get_chapters(self, comic, **kwargs) -> list[dict]:
        comic_id = self._id(comic, "id", "comic_id")
        if not comic_id:
            return []
        if str(comic_id).startswith("http"):
            url = str(comic_id)
        else:
            cid = str(comic_id)
            if cid.isdigit() or cid.startswith("m"):
                url = f"{self.base_url}/m{cid.lstrip('m')}/"
            else:
                url = f"{self.base_url}/{cid}/"

        soup = self._soup(url)
        warning = soup.select_one(".warning-bar")
        if warning:
            raise ValueError(warning.get_text(strip=True))

        container = soup.select_one("div#chapterlistload")
        if not container:
            raise ValueError(
                "无法加载章节列表，请确认页面可访问；切换网络后可尝试清除 Cookie"
            )

        titles = [
            a.get_text(strip=True).split("（")[0]
            for a in soup.select(".detail-list-title > a.block")
        ]
        chapters: list[dict] = []
        uls = container.select(":scope > ul") or container.find_all(
            "ul", recursive=False
        )
        for i, ul in enumerate(uls):
            scanlator = titles[i] if i < len(titles) else None
            for a in ul.select("li > a"):
                href = a.get("href") or ""
                name_el = a.select_one("p.title")
                name = (
                    name_el.get_text(strip=True)
                    if name_el
                    else a.get_text(strip=True)
                )
                if a.select_one(".detail-lock, .view-lock"):
                    name = f"🔒 {name}"
                chap_id = self._extract_id(href)
                chapters.append(
                    {
                        "id": chap_id,
                        "name": name,
                        "comic_id": str(comic_id),
                        "url": urljoin(self.base_url, href),
                        "scanlator": scanlator,
                    }
                )

        # Prefer oldest-first for reading UX
        order_el = soup.select_one("div.detail-list-title a.order")
        if order_el and order_el.get_text(strip=True) == "正序":
            chapters = list(reversed(chapters))
        else:
            # site default is often newest-first → reverse
            chapters = list(reversed(chapters))

        return chapters

    def resolve_read(self, chapter, comic=None) -> list[str]:
        chapter_uuid = self._id(chapter, "id", "uuid", "url")
        if not chapter_uuid:
            raise ValueError("Missing chapter id")
        return self._get_chapter_images(chapter_uuid)

    # ── optional (anti-hotlink CDN) ────────────────────────────────────
    def fetch_image(self, url: str) -> bytes:
        headers = self._image_headers(url)
        resp = self.session.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        return resp.content

    # ── image resolution (private) ────────────────────────────────────
    def _image_headers(self, image_url: str) -> dict:
        headers = {
            "User-Agent": self.session.headers.get("User-Agent", ""),
            "Accept": "*/*",
            "Accept-Language": "zh-TW",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Cache-Control": "max-age=600",
            "Referer": f"{self.base_url}/",
        }
        try:
            qs = parse_qs(urlparse(image_url).query)
            cid = (qs.get("cid") or [None])[0]
            if cid:
                headers["Referer"] = f"{self.base_url}/m{cid}"
        except Exception:
            pass
        return headers

    def _get_chapter_images(self, chapter_uuid: str) -> list[str]:
        if chapter_uuid.startswith("http"):
            chapter_url = chapter_uuid
        else:
            cid = str(chapter_uuid).lstrip("/")
            if not cid.startswith("m"):
                cid = f"m{cid}"
            chapter_url = f"{self.base_url}/{cid}/"

        resp = self._get(chapter_url)
        soup = BeautifulSoup(resp.text, "html.parser")
        page_url = resp.url

        # Some chapters preload via data-src
        images = soup.select("div#barChapter > img.load-src")
        if images:
            result = []
            for img in images:
                src = img.get("data-src") or img.get("src")
                if src:
                    result.append(urljoin(page_url, src))
            return result

        script_el = soup.find("script", string=re.compile(r"DM5_MID"))
        if not script_el or not script_el.string:
            pay = soup.select_one("div.view-pay-form p.subtitle")
            msg = (
                pay.get_text(strip=True)
                if pay
                else "Required viewsign data missing from script"
            )
            raise ValueError(msg)

        script = script_el.string
        if "DM5_VIEWSIGN_DT" not in script:
            pay = soup.select_one("div.view-pay-form p.subtitle")
            msg = (
                pay.get_text(strip=True)
                if pay
                else "Required viewsign data missing from script"
            )
            raise ValueError(msg)

        def _extract(var: str, quoted: bool = False) -> str:
            if quoted:
                m = re.search(rf'var\s+{var}\s*=\s*"([^"]*)"', script)
            else:
                m = re.search(rf"var\s+{var}\s*=\s*([^;]+);", script)
            return m.group(1).strip() if m else ""

        cid = _extract("DM5_CID")
        mid = _extract("DM5_MID")
        dt = _extract("DM5_VIEWSIGN_DT", quoted=True)
        sign = _extract("DM5_VIEWSIGN", quoted=True)
        image_count = int(_extract("DM5_IMAGE_COUNT") or "0")

        parsed = urlparse(page_url)
        base_path = parsed.path.rstrip("/")
        referer = page_url

        result: list[str] = []
        seen: set[str] = set()
        for page in range(1, image_count + 1):
            params = {
                "cid": cid,
                "page": str(page),
                "key": "",
                "language": "1",
                "gtk": "6",
                "_cid": cid,
                "_mid": mid,
                "_dt": dt,
                "_sign": sign,
            }
            fun_url = (
                f"{parsed.scheme}://{parsed.netloc}{base_path}/chapterfun.ashx"
                f"?{urlencode(params)}"
            )
            for img_url in self._resolve_image_urls(fun_url, referer=referer):
                if img_url not in seen:
                    seen.add(img_url)
                    result.append(img_url)
            if len(result) >= image_count:
                break
        return result[:image_count] if image_count else result

    def _resolve_image_urls(self, fun_url: str, referer: str) -> list[str]:
        headers = {"Referer": referer}
        resp = self.session.get(fun_url, headers=headers, timeout=15)
        resp.raise_for_status()
        body = resp.text
        try:
            unpacked = _unpack_packer(body)
        except Exception:
            unpacked = body

        pix_m = re.search(r'var\s+pix\s*=\s*"([^"]*)"', unpacked)
        if not pix_m:
            return []
        pix = pix_m.group(1)

        arr_m = re.search(r"var\s+pvalue\s*=\s*\[(.*?)\]", unpacked, re.DOTALL)
        if not arr_m:
            return []
        pvalues = re.findall(r'"([^"]+)"', arr_m.group(1))

        query_m = re.search(r"""['"](\?cid=[^'"]*)['"]""", unpacked) or re.search(
            r"\+'(\?[^']*)'", unpacked
        )
        query = query_m.group(1) if query_m else ""

        urls = []
        for pv in pvalues:
            if re.match(r"^(https?:)?//", pv):
                urls.append(pv if pv.startswith("http") else "https:" + pv)
            else:
                urls.append(pix + pv + query)
        return urls
