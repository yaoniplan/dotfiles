# https://github.com/fjcanyue/comic_downloader/blob/12032e0e9133e19c0432e33f9a99fd4c140f6acc/downloader/sources/adapters/dumanwu.py
# https://github.com/zhimouzhou/venera-manga-sources/blob/b3b22aaf832fb2382004b5be10a314e59c47e328/sources/dumanwu1.js
# https://github.com/xyrlsz/xcimoc-js-sources/blob/8026659b8a014fea586b49d357e02e251d51d4fd/sources/dumanwu.js
# https://github.com/x1Katari/scripts/blob/02fa62b3d7df2544afbbadca852966796754d499/dumanwu.py
"""读漫屋 (dumanwu / dumanwu1) — unified: search / get_chapters / resolve_read.

Flow:
  search  → POST /s  (HTML .itemnar; JSON fallback)
  chapters → detail HTML + POST /morechapter  (newest→oldest, then reverse)
  images  → chapter page packer → __c0rst96 → node + all2.js → data-src
            (same decode path as venera dumanwu1.js; needs ``node`` on PATH)

No Selenium. Pure requests + optional Node for image decode.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_CANDIDATES = [
    "http://www.dumanwu1.com",
    "http://dumanwu1.com",
    "http://m.dumanwu1.com",
    "https://www.dumanwu.com",
    "http://www.dumanwu.com",
    "https://dumanwu.com",
]

PACKER_RE = re.compile(
    r"<script[^>]*>\s*(eval\(function\(p,a,c,k,e,d\)[\s\S]*?)</script>",
    re.I,
)
PACKER_CALL_RE = re.compile(
    r"}\('((?:\\'|[^'])*)'\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*'([^']*)'\.split\('\|'\)",
    re.DOTALL,
)
C0RST96_RE = re.compile(r"""__c0rst96\s*=\s*["']([^"']+)""")
ALL2_SRC_RE = re.compile(r"""<script[^>]+src=["']([^"']*all2\.js[^"']*)["']""", re.I)
READER_ID_RE = re.compile(r"""readerContainer["'\s][^>]*data-id=["']?(\d+)""", re.I)
IMG_ATTR_RE = re.compile(r"""(?:data-src|src)=["']([^"']+)""", re.I)
SKIP_IMG_RE = re.compile(r"load\.gif|logo|favicon|static/images|track", re.I)
NAV_TITLE_RE = re.compile(
    r"^\s*(开始阅读|继续阅读|上一章|下一章|上一话|下一话)\s*$", re.I
)


def _to36(n: int) -> str:
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    if n == 0:
        return "0"
    out = ""
    while n:
        out = digits[n % 36] + out
        n //= 36
    return out


def _unpack_packer(js: str) -> str:
    """Dean-Edwards packer used on chapter pages."""
    m = PACKER_CALL_RE.search(js)
    if not m:
        return ""
    payload, a, c, kstr = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)
    k = kstr.split("|")

    def e(val: int) -> str:
        return ("" if val < a else e(val // a)) + (
            chr(val % a + 29) if val % a > 35 else _to36(val % a)
        )

    mapping = {
        e(i): (k[i] if i < len(k) and k[i] else e(i)) for i in range(c)
    }
    return re.sub(r"\b\w+\b", lambda mm: mapping.get(mm.group(0), mm.group(0)), payload)


class Provider:
    name = "dumanwu"

    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or BASE_CANDIDATES[0]).rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;q=0.9,"
                    "*/*;q=0.8"
                ),
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": self.base_url + "/",
            }
        )
        self._last_page_url: str | None = None
        self._all2_cache: str | None = None

    # ------------------------------------------------------------------ helpers
    def _request(
        self,
        method: str,
        path_or_url: str,
        *,
        data: dict | None = None,
        referer: str | None = None,
        timeout: int = 20,
    ) -> tuple[requests.Response, str]:
        """Try each mirror until one returns 200 with a body."""
        path = path_or_url
        if path.startswith("http://") or path.startswith("https://"):
            candidates = [path]
        else:
            if not path.startswith("/"):
                path = "/" + path
            candidates = [b.rstrip("/") + path for b in BASE_CANDIDATES]

        last_err: Exception | None = None
        for url in candidates:
            base = "{0.scheme}://{0.netloc}".format(requests.utils.urlparse(url))
            headers = {
                "Referer": referer or (base + "/"),
            }
            if data is not None:
                headers["Content-Type"] = (
                    "application/x-www-form-urlencoded; charset=UTF-8"
                )
                headers["X-Requested-With"] = "XMLHttpRequest"
            try:
                r = self.session.request(
                    method,
                    url,
                    data=data,
                    headers=headers,
                    timeout=timeout,
                    allow_redirects=True,
                )
                if r.status_code == 200 and r.content:
                    r.encoding = r.apparent_encoding or "utf-8"
                    self.base_url = base.rstrip("/")
                    return r, base.rstrip("/")
            except Exception as e:
                last_err = e
                continue
        raise RuntimeError(
            f"All dumanwu mirrors failed for {path_or_url}: {last_err}"
        )

    def _abs(self, url: str, base: str | None = None) -> str:
        if not url:
            return ""
        url = url.strip()
        if url.startswith("//"):
            return "http:" + url
        if url.startswith("http://") or url.startswith("https://"):
            return url
        return urljoin((base or self.base_url) + "/", url.lstrip("/"))

    # ------------------------------------------------------------------ search
    def search(self, query: str, limit: int = 20, offset: int = 0) -> list[dict]:
        # page>1 not supported by site search
        if offset:
            return []
        r, base = self._request("POST", "/s", data={"k": query})
        out: list[dict] = []

        # JSON form (some mirrors / older responses)
        try:
            j = r.json()
            if str(j.get("code")) == "200" and isinstance(j.get("data"), list):
                for item in j["data"]:
                    cid = str(item.get("id") or "").strip()
                    name = (item.get("name") or "").strip()
                    if not cid or not name:
                        continue
                    out.append(
                        {
                            "id": cid,
                            "name": name,
                            "cover": self._abs(item.get("imgurl") or "", base),
                            "remark": (item.get("remarks") or "").strip(),
                        }
                    )
                    if len(out) >= limit:
                        return out
                if out:
                    return out
        except Exception:
            pass

        # HTML .itemnar (current site)
        soup = BeautifulSoup(r.text, "html.parser")
        seen: set[str] = set()
        for item in soup.select(".itemnar"):
            a = item.select_one("a[title]") or item.select_one("p a[href]")
            if not a:
                continue
            href = (a.get("href") or "").strip()
            m = re.match(r"^/([^/]+)/?$", href)
            if not m:
                continue
            cid = m.group(1)
            if cid in seen:
                continue
            title = (a.get("title") or a.get_text(strip=True) or "").strip()
            if not title or NAV_TITLE_RE.match(title):
                continue
            seen.add(cid)
            img = item.select_one("img")
            cover = ""
            if img:
                cover = (
                    img.get("data-src")
                    or img.get("data-original")
                    or img.get("src")
                    or ""
                )
            remark = ""
            # often "第N话 title" text near the card
            texts = [
                t.strip()
                for t in item.stripped_strings
                if t.strip() and t.strip() != title
            ]
            if texts:
                remark = texts[0]
            out.append(
                {
                    "id": cid,
                    "name": title,
                    "cover": self._abs(cover, base),
                    "remark": remark,
                }
            )
            if len(out) >= limit:
                break
        return out

    # ---------------------------------------------------------------- chapters
    def get_chapters(self, comic, **kwargs) -> list[dict]:
        cid = comic.get("id") if isinstance(comic, dict) else comic
        if not cid:
            return []
        cid = str(cid).strip().strip("/")
        if cid.endswith(".html"):
            cid = cid.rsplit("/", 1)[0].strip("/")

        r, base = self._request("GET", f"/{cid}/")
        soup = BeautifulSoup(r.text, "html.parser")

        chapters: list[dict] = []
        seen: set[str] = set()

        def add(chap_id: str, name: str) -> None:
            chap_id = str(chap_id).strip().removesuffix(".html")
            name = (name or "").strip()
            if not chap_id or not name or NAV_TITLE_RE.match(name):
                return
            if chap_id in seen:
                return
            seen.add(chap_id)
            chapters.append(
                {
                    "id": chap_id,
                    "name": name,
                    "comic_id": cid,
                }
            )

        # initial list on detail page (newest first)
        for a in soup.select(".chapterlistload a, .chaplist-box a"):
            href = (a.get("href") or "").strip()
            m = re.match(rf"^/{re.escape(cid)}/([^/]+)\.html$", href)
            if not m:
                continue
            add(m.group(1), a.get_text(strip=True))

        # AJAX more chapters (often older ones)
        try:
            mr, _ = self._request(
                "POST",
                "/morechapter",
                data={"id": cid},
                referer=f"{base}/{cid}/",
            )
            mj = mr.json()
            data = mj.get("data") if str(mj.get("code")) == "200" else None
            if isinstance(data, list):
                for item in data:
                    add(item.get("chapterid") or "", item.get("chaptername") or "")
        except Exception:
            pass

        # site lists newest→oldest; reverse for reading order
        chapters.reverse()
        return chapters

    # ---------------------------------------------------------------- images
    def _run_all2(self, all2_js: str, encoded: str, data_id: int) -> str:
        """Execute obfuscated all2.js with a mock jQuery (venera approach)."""
        if not shutil.which("node"):
            raise RuntimeError(
                "dumanwu image decode requires `node` on PATH "
                "(all2.js is jsjiami-obfuscated)"
            )
        script = (
            "const encoded = "
            + json.dumps(encoded)
            + ";\n"
            + f"const dataId = {int(data_id)};\n"
            + "let appended = '';\n"
            + "global.__c0rst96 = encoded;\n"
            + "global.$ = function (arg) {\n"
            + "  if (typeof arg === 'function') { arg(); return {}; }\n"
            + "  return { data: () => dataId, append: (html) => { appended += html; } };\n"
            + "};\n"
            + "try {\n"
            + all2_js
            + "\n} catch (e) {\n"
            + "  console.error(String(e));\n"
            + "  process.exit(2);\n"
            + "}\n"
            + "process.stdout.write(appended);\n"
        )
        proc = subprocess.run(
            ["node", "-e", script],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"all2.js decode failed: {proc.stderr.strip() or proc.returncode}"
            )
        return proc.stdout or ""

    def resolve_read(self, chapter, comic=None) -> list[str]:
        if isinstance(chapter, dict):
            chap_id = chapter.get("id") or chapter.get("url") or ""
            comic_id = chapter.get("comic_id") or (
                comic.get("id") if isinstance(comic, dict) else comic
            )
        else:
            chap_id = str(chapter or "")
            comic_id = comic.get("id") if isinstance(comic, dict) else comic

        chap_id = str(chap_id).strip().strip("/")
        comic_id = str(comic_id or "").strip().strip("/")

        # accept full path "/cid/chap.html" as id
        if "/" in chap_id and chap_id.endswith(".html"):
            parts = chap_id.strip("/").split("/")
            if len(parts) >= 2:
                comic_id, chap_id = parts[0], parts[1].removesuffix(".html")

        if not comic_id or not chap_id:
            raise ValueError("Need comic_id and chapter id")

        page_path = f"/{comic_id}/{chap_id}.html"
        r, base = self._request("GET", page_path)
        self._last_page_url = r.url
        html = r.text

        # 1) try plain data-src already in HTML (rare / older pages)
        plain: list[str] = []
        soup = BeautifulSoup(html, "html.parser")
        for img in soup.select(".main_img img, .chapter-img-box img"):
            src = (
                img.get("data-src")
                or img.get("data-original")
                or img.get("src")
                or ""
            ).strip()
            if not src or SKIP_IMG_RE.search(src):
                continue
            plain.append(self._abs(src, base))
        if plain:
            return plain

        # 2) packer → __c0rst96 → all2.js (venera path)
        pm = PACKER_RE.search(html)
        if not pm:
            raise RuntimeError("No packed image script on chapter page")
        unpacked = _unpack_packer(pm.group(1))
        cm = C0RST96_RE.search(unpacked) or C0RST96_RE.search(html)
        if not cm:
            raise RuntimeError("Failed to extract __c0rst96")
        encoded = cm.group(1)

        rid_m = READER_ID_RE.search(html)
        data_id = int(rid_m.group(1)) if rid_m else 1

        am = ALL2_SRC_RE.search(html)
        all2_path = am.group(1) if am else "/static/js/all2.js?v=2.3"
        if self._all2_cache is None:
            ar, _ = self._request("GET", all2_path, referer=r.url)
            self._all2_cache = ar.text
        rendered = self._run_all2(self._all2_cache, encoded, data_id)

        out: list[str] = []
        seen: set[str] = set()
        for m in IMG_ATTR_RE.finditer(rendered):
            src = self._abs(m.group(1), base)
            if not src or SKIP_IMG_RE.search(src):
                continue
            if src in seen:
                continue
            seen.add(src)
            out.append(src)
        if not out:
            raise RuntimeError("all2.js produced no image URLs")
        return out

    def fetch_image(self, url: str) -> bytes:
        referer = self._last_page_url or (self.base_url + "/")
        r = self.session.get(
            url,
            headers={
                "Referer": referer,
                "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                "User-Agent": self.session.headers["User-Agent"],
            },
            timeout=30,
        )
        r.raise_for_status()
        return r.content
