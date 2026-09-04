# https://github.com/doyayaa/aidoku-source-zh/tree/4501ad192e7a2cf4bcae38daa9811f1de7e22ee0/sources/zh.hipmh
from __future__ import annotations

import base64
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote

import requests

BASE_URL = "https://m.hipmh.com"
API_URL = "https://hipapi1.s3file.top/v1/mangas"
SEARCH_URL = "https://hipapi1.s3file.top/v1/search"
CHAPTERS_URL = "https://hipapi1.s3file.top/v1/manga/chapters"
CHAPTER_API = "https://hipapi1.s3file.top/v2/chapter"
READER_ORIGIN = "https://reader.hipmh.top"
COVER_CDN = "https://cover.s3imgs.top"
IMAGE_BASE = "https://hip-tx-1.s3imgs.top"
IMAGE_BASE_SECURE = "https://hip-tx-s1.s3imgs.top"

_FROM = b"_-9876543210abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
_TO = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
_TRANSLATE = bytes.maketrans(_FROM, _TO)


def _b64_decode_padded(s: str) -> bytes:
    stripped = s.rstrip("=")
    pad = (4 - len(stripped) % 4) % 4
    return base64.b64decode(stripped + ("=" * pad))


def _b64_encode_nopad(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode()
    return base64.b64encode(data).decode().rstrip("=")


def decode_work_id(encoded: str) -> str:
    try:
        return _b64_decode_padded(encoded).decode("utf-8")
    except Exception:
        return encoded


def works_slug_to_key(slug: str) -> str:
    encoded = slug.split("-")[0] if slug else slug
    return decode_work_id(encoded)


def key_to_works_id(key: str) -> str:
    return _b64_encode_nopad(key)


def image_base(line: int) -> str:
    return IMAGE_BASE_SECURE if line == 9 else IMAGE_BASE


def decode_images(encrypted: str) -> list[str]:
    raw = encrypted.encode("ascii", errors="ignore")
    if len(raw) < 8 or not raw.startswith(b"qM9") or not raw.endswith(b"Z7"):
        raise ValueError("Invalid images payload")
    inner = raw[3:-2]
    total = len(inner) - 5
    k_len = total // 3
    a_len = (total - k_len) // 2
    b_len = total - k_len - a_len

    if (
        inner[a_len : a_len + 2] != b"Vx"
        or inner[a_len + 2 + b_len : a_len + 2 + b_len + 3] != b"pL0"
    ):
        raise ValueError("Unexpected images layout")

    seg_a = inner[:a_len]
    seg_b = inner[a_len + 2 : a_len + 2 + b_len]
    seg_k = inner[a_len + 2 + b_len + 3 :]
    combined = seg_k + seg_a + seg_b

    substituted = bytearray()
    for idx in range(0, len(combined), 7):
        chunk = combined[idx : idx + 7]
        if (idx // 7) % 2 == 1:
            chunk = chunk[::-1]
        substituted.extend(chunk.translate(_TRANSLATE))

    pad = (4 - len(substituted) % 4) % 4
    decoded = base64.urlsafe_b64decode(bytes(substituted) + b"=" * pad)
    arr = json.loads(decoded.decode("utf-8"))
    return [p for p in arr if isinstance(p, str)]


def derive_api_hid(chapter_key: str) -> str:
    if "-" not in chapter_key:
        raise ValueError("Invalid chapter key")
    seg1, seg2 = chapter_key.rsplit("-", 1)
    decoded = _b64_decode_padded(seg1).decode("utf-8")
    if "-c:" not in decoded:
        raise ValueError(f"Unexpected hid segment: {decoded}")
    cid = decoded.rsplit("-c:", 1)[1]
    return f"{_b64_encode_nopad(f'c:{cid}')}-{seg2}"


class Provider:
    name = "hip"
    #name = "嬉皮漫畫"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_7 like Mac OS X) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.7 "
                    "Mobile/15E148 Safari/604.1"
                ),
                "Accept": "application/json, text/plain, */*",
                "Origin": BASE_URL,
                "Referer": BASE_URL + "/",
            }
        )

    def _get_json(self, url: str, **headers) -> dict:
        h = dict(self.session.headers)
        h.update(headers)
        r = self.session.get(url, headers=h, timeout=20)
        r.raise_for_status()
        return r.json()

    def _cover(self, path: str | None) -> str:
        if not path:
            return ""
        if path.startswith("http"):
            return path
        return f"{COVER_CDN}{path}"

    def _mid(self, comic) -> str:
        if isinstance(comic, dict):
            key = comic.get("id") or comic.get("comic_id") or ""
        else:
            key = str(comic or "")
        return key[2:] if key.startswith("m:") else key

    def search(self, query: str, limit: int = 20, offset: int = 0) -> list[dict]:
        page = max(1, (offset // max(limit, 1)) + 1)
        url = f"{SEARCH_URL}?q={quote(query)}&page={page}&page_size={limit}"
        data = self._get_json(url).get("data") or {}
        items = data.get("items") or data.get("data") or []
        out = []
        for item in items:
            mid = item.get("mid") or item.get("id") or ""
            title = item.get("title") or ""
            cover = self._cover(
                item.get("vertical_image_url") or item.get("cover_image_url")
            )
            authors = item.get("authors") or []
            remark = ", ".join(
                a.get("name")
                for a in authors
                if isinstance(a, dict) and a.get("name")
            )
            key = works_slug_to_key(str(mid))
            out.append(
                {
                    "id": key,
                    "name": title,
                    "cover": cover,
                    "remark": remark,
                }
            )
            if len(out) >= limit:
                break
        return out

    def get_chapters(self, comic, **kwargs) -> list[dict]:
        mid = self._mid(comic)
        if not mid:
            return []
        base = f"{CHAPTERS_URL}?mid={mid}"
        page1 = self._get_json(f"{base}&page=1&per_page=50&order=desc")
        data1 = page1.get("data") or {}
        total_pages = max(1, int(data1.get("total_pages") or 1))

        pages_json = [page1]
        if total_pages > 1:

            def fetch(p):
                return self._get_json(f"{base}&page={p}&per_page=50&order=desc")

            with ThreadPoolExecutor(max_workers=min(8, total_pages - 1)) as pool:
                futs = {pool.submit(fetch, p): p for p in range(2, total_pages + 1)}
                by_page = {}
                for fut in as_completed(futs):
                    by_page[futs[fut]] = fut.result()
                for p in range(2, total_pages + 1):
                    pages_json.append(by_page[p])

        chapters = []
        comic_id = f"m:{mid}"
        for pj in pages_json:
            items = (pj.get("data") or {}).get("items") or []
            for item in items:
                hid = item.get("hid") or ""
                title = item.get("title") or ""
                num = item.get("chapter_number")
                name = title or (f"第{num}话" if num is not None else hid)
                chapters.append(
                    {
                        "id": hid,
                        "name": name,
                        "comic_id": comic_id,
                    }
                )

        chapters.reverse()
        return chapters

    def resolve_read(self, chapter, comic=None) -> list[str]:
        if isinstance(chapter, dict):
            chap_key = chapter.get("id") or chapter.get("uuid") or ""
        else:
            chap_key = str(chapter or "")
        if not chap_key:
            raise ValueError("Missing chapter id")

        api_hid = derive_api_hid(chap_key)
        data = (
            self._get_json(
                f"{CHAPTER_API}?hid={quote(api_hid, safe='')}",
                Origin=READER_ORIGIN,
                Referer=READER_ORIGIN + "/",
            ).get("data")
            or {}
        )

        images_blob = data.get("images") or ""
        line = int(data.get("line") or 1)
        base = image_base(line)
        paths = decode_images(images_blob)
        return [f"{base}{p}" for p in paths]

    def fetch_image(self, url: str) -> bytes:
        r = self.session.get(
            url,
            headers={
                "Referer": BASE_URL + "/",
                "Accept": "image/avif,image/webp,image/*,*/*;q=0.8",
            },
            timeout=30,
        )
        r.raise_for_status()
        return r.content
