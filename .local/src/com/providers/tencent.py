# https://github.com/keiyoushi/extensions-source/tree/aa14252caaba8bfe676eaf62095819745a2138ec/src/zh/tencentcomics
"""腾讯动漫 (ac.qq.com) — unified: search / get_chapters / resolve_read.

Desktop chapter pages embed ``var DATA`` + a browser-probe nonce. Decode
matches keiyoushi TencentComics.kt (splice noise by nonce, then base64 JSON)
in pure Python — no QuickJS/Node.
"""
from __future__ import annotations

import base64
import json
import math
import re

import requests
from bs4 import BeautifulSoup

DESKTOP = "https://ac.qq.com"
MOBILE = "https://m.ac.qq.com"
DESKTOP_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/139.0.0.0 Safari/537.36"
)
MOBILE_UA = (
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/140.0.0.0 Mobile Safari/537.36"
)


def _js_round(x: float) -> int:
    if x >= 0:
        return int(math.floor(x + 0.5))
    return int(math.ceil(x - 0.5))


def _safe_arith(e: str):
    e = e.strip()
    if not re.match(r"^[\d\s+\-*/%.\(\)&|<>!=]+$", e):
        raise ValueError(f"unparsed js expr: {e!r}")
    result = eval(e, {"__builtins__": {}}, {})  # noqa: S307 — digits/ops only
    if isinstance(result, bool):
        return int(result)
    if isinstance(result, float) and result == int(result):
        return int(result)
    return result


def _eval_nonce_piece(expr: str):
    e = expr.strip()
    e = re.sub(
        r"""(['"])(.*?)\1\.charCodeAt\(\s*(\d*)\s*\)""",
        lambda m: str(
            ord(m.group(2)[int(m.group(3) or 0)])
            if int(m.group(3) or 0) < len(m.group(2))
            else 0
        ),
        e,
    )
    e = re.sub(
        r"""(['"])(.*?)\1\.substring\(\s*(\d+)\s*\)""",
        lambda m: (
            lambda v: v if re.match(r"^-?\d+$", v) else json.dumps(v)
        )(m.group(2)[int(m.group(3)) :]),
        e,
    )
    e = re.sub(r"document(\s*\.\s*\w+|\s*\[[^\]]*\]|\s*\([^)]*\))+", "1", e)
    e = re.sub(r"window(\s*\.\s*\w+|\s*\[[^\]]*\])+", "1", e)

    for _ in range(8):
        n = e
        n = re.sub(
            r"Math\.pow\s*\(\s*([^,()]+)\s*,\s*([^()]+)\s*\)",
            lambda m: str(float(m.group(1)) ** float(m.group(2))),
            n,
        )
        n = re.sub(
            r"Math\.round\s*\(\s*([^()]+)\s*\)",
            lambda m: str(_js_round(float(_safe_arith(m.group(1))))),
            n,
        )
        n = re.sub(
            r"Math\.floor\s*\(\s*([^()]+)\s*\)",
            lambda m: str(math.floor(float(_safe_arith(m.group(1))))),
            n,
        )
        n = re.sub(
            r"Math\.ceil\s*\(\s*([^()]+)\s*\)",
            lambda m: str(math.ceil(float(_safe_arith(m.group(1))))),
            n,
        )
        n = re.sub(
            r"parseInt\s*\(\s*([^()]+)\s*\)",
            lambda m: str(int(float(_safe_arith(m.group(1))))),
            n,
        )
        if n == e:
            break
        e = n

    for _ in range(5):
        n = re.sub(
            r"~~\s*\(?\s*([\d.]+)\s*\)?",
            lambda m: str(int(float(m.group(1)))),
            e,
        )
        if n == e:
            break
        e = n

    def _reduce_bangs(s: str) -> str:
        def repl(m):
            truth = float(m.group(2)) != 0
            for _ in range(len(m.group(1))):
                truth = not truth
            return "1" if truth else "0"

        return re.sub(r"(!+)([\d.]+)", repl, s)

    for _ in range(10):
        n = _reduce_bangs(e)
        if n == e:
            break
        e = n

    for _ in range(5):
        m = re.search(r"(.+?)\?([^:]+):(.+)", e)
        if not m:
            break
        cond, a, b = m.group(1), m.group(2), m.group(3)
        e = (a if _safe_arith(cond) else b).strip()

    e = e.replace("true", "1").replace("false", "0")
    e = re.sub(r"""(['"])(-?\d+)\1""", r"\2", e)
    return _safe_arith(e)


def _compute_nonce(nonce_expr: str) -> str:
    def repl(m):
        val = _eval_nonce_piece(m.group(2))
        if isinstance(val, float) and val == int(val):
            val = int(val)
        return str(val)

    out = re.sub(
        r"""\(\s*\+\s*eval\s*\(\s*(["'])(.*?)\1\s*\)\s*\)(?:\.toString\(\))?""",
        repl,
        nonce_expr,
    )
    parts = re.findall(r'"(.*?)"|\'(.*?)\'|(-?\d+(?:\.\d+)?)', out)
    return "".join(a or b or c for a, b, c in parts)


def _decode_chapter_data(raw: str, nonce: str) -> dict:
    chars = list(raw)
    for part in reversed(re.findall(r"\d+[a-zA-Z]+", nonce)):
        offset = int(re.match(r"\d+", part).group(0)) & 255
        noise = re.sub(r"\d+", "", part)
        del chars[offset : offset + len(noise)]
    b64 = "".join(chars)
    b64 += "=" * ((-len(b64)) % 4)
    return json.loads(base64.b64decode(b64))


class Provider:
    name = "tencent"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": DESKTOP_UA,
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;"
                    "q=0.9,*/*;q=0.8"
                ),
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": DESKTOP + "/",
            }
        )
        self._last_chapter_url: str | None = None

    def search(self, query: str, limit: int = 20, offset: int = 0) -> list[dict]:
        page = offset // max(limit, 1) + 1
        r = self.session.get(
            f"{MOBILE}/search/result",
            params={"word": query, "page": page},
            headers={**self.session.headers, "User-Agent": MOBILE_UA},
            timeout=20,
        )
        r.raise_for_status()
        r.encoding = r.apparent_encoding or "utf-8"
        soup = BeautifulSoup(r.text, "html.parser")
        out: list[dict] = []
        for a in soup.select("ul > li.comic-item > a"):
            href = (a.get("href") or "").strip()
            m = re.search(r"/id/(\d+)", href)
            if not m:
                continue
            cid = m.group(1)
            title_el = a.select_one("div > strong, .comic-title")
            title = title_el.get_text(strip=True) if title_el else ""
            if not title:
                continue
            img = a.select_one("div > img")
            cover = ""
            if img:
                cover = (img.get("src") or img.get("data-src") or "").strip()
            # short tag only — not comic-desc (too long)
            tag = a.select_one("div > small.comic-update")
            remark = tag.get_text(strip=True) if tag else ""
            out.append(
                {
                    "id": cid,
                    "name": title,
                    "cover": cover,
                    "remark": remark,
                }
            )
            if len(out) >= limit:
                break
        return out

    def get_chapters(self, comic, **kwargs) -> list[dict]:
        cid = comic.get("id") if isinstance(comic, dict) else comic
        if not cid:
            return []
        cid = str(cid).strip()
        r = self.session.get(f"{DESKTOP}/Comic/comicInfo/id/{cid}", timeout=20)
        r.raise_for_status()
        r.encoding = r.apparent_encoding or "utf-8"
        soup = BeautifulSoup(r.text, "html.parser")

        chapters: list[dict] = []
        for el in soup.select(".chapter-page-all .works-chapter-item"):
            a = el.select_one("a")
            if not a:
                continue
            href = (a.get("href") or "").strip()
            m = re.search(r"/cid/(\d+)", href)
            if not m:
                continue
            name = el.get_text(strip=True)
            if el.select_one(".ui-icon-pay"):
                name = "🔒 " + name
            chapters.append(
                {
                    "id": m.group(1),
                    "name": name,
                    "comic_id": cid,
                }
            )

        # DOM is oldest → newest; keep that for reading (no reverse)
        return chapters

    def resolve_read(self, chapter, comic=None) -> list[str]:
        if isinstance(chapter, dict):
            chap_id = chapter.get("id") or ""
            comic_id = chapter.get("comic_id") or (
                comic.get("id") if isinstance(comic, dict) else comic
            )
        else:
            chap_id = str(chapter or "")
            comic_id = comic.get("id") if isinstance(comic, dict) else comic

        chap_id = str(chap_id).strip()
        comic_id = str(comic_id or "").strip()
        if not comic_id or not chap_id:
            raise ValueError("Need comic_id and chapter id")

        url = f"{DESKTOP}/ComicView/index/id/{comic_id}/cid/{chap_id}"
        self._last_chapter_url = url
        r = self.session.get(url, timeout=30)
        r.raise_for_status()
        html = r.text

        if "var DATA" not in html:
            raise RuntimeError("Chapter page missing DATA (blocked or changed)")

        raw = html.split("var DATA =")[-1].split("PRELOAD_NUM")[0].strip()
        raw = re.sub(r"^'|',\s*$", "", raw).strip().strip("'").strip(",")

        part = html.split("window[")[-1]
        nonce_expr = (
            part.split("] = ", 1)[-1].split("</script>")[0].strip().rstrip(";")
        )
        nonce = _compute_nonce(nonce_expr)
        data = _decode_chapter_data(raw, nonce)

        chapter_info = data.get("chapter") or {}
        if chapter_info.get("canRead") is False:
            raise RuntimeError("[此章节为付费内容]")

        urls: list[str] = []
        for pic in data.get("picture") or []:
            u = (pic.get("url") or "").strip()
            if u:
                urls.append(u)
        if not urls:
            raise RuntimeError("No images in chapter DATA")
        return urls

    def fetch_image(self, url: str) -> bytes:
        r = self.session.get(
            url,
            headers={
                "Referer": self._last_chapter_url or (DESKTOP + "/"),
                "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                "User-Agent": DESKTOP_UA,
            },
            timeout=30,
        )
        r.raise_for_status()
        return r.content
