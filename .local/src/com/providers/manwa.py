import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad


class Provider:
    name = "manwa"
    #name = "漫蛙漫画"
    AES_KEY = b"0B6666A0-BB59-1381-B746-a0E4C9AC"

    def __init__(self, base_url: str = "https://manwali.cc", cookie: str = None):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_7_2 like Mac OS X) AppleWebKit/605.1.15",
            "Accept": "application/json",
            "Origin": "https://www.manwali.cc",
            "Referer": "https://www.manwali.cc/cate/",
        })
        if cookie:
            for pair in cookie.split(";"):
                if "=" in pair:
                    k, v = pair.strip().split("=", 1)
                    self.session.cookies.set(k, v)

    def _get(self, endpoint, params=None):
        r = self.session.get(f"{self.base_url}{endpoint}", params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        if data.get("code") != 200:
            raise ValueError(f"API Error ({data.get('code')}): {data.get('msg')}")
        return data.get("data", {})

    @classmethod
    def decrypt_image(cls, data: bytes) -> bytes:
        if len(data) < 16 or data[:2] in (b"\xff\xd8", b"\x89P", b"GI", b"RI"):
            return data
        iv, ct = data[:16], data[16:]
        if len(ct) % 16:
            return data
        plain = AES.new(cls.AES_KEY, AES.MODE_CBC, iv).decrypt(ct)
        try:
            plain = unpad(plain, 16)
        except ValueError:
            pass
        return plain

    def search(self, query: str, limit: int = 20, offset: int = 0) -> list[dict]:
        page_size = 20
        start_page = offset // page_size + 1
        in_page = offset % page_size
        raw, page = [], start_page
        while len(raw) < limit:
            data = self._get("/api/search", {"type": "mh", "page": page, "pageSize": page_size, "keyword": query})
            items = data.get("list", [])
            if not items:
                break
            if page == start_page:
                items = items[in_page:]
            raw.extend(items)
            if len(items) < page_size:
                break
            page += 1
        out = []
        for item in raw[:limit]:
            author = item.get("author") or ""
            out.append({
                "id": item.get("id"),
                "name": item.get("title"),
                "cover": item.get("cover"),
                "remark": author,
            })
        return out

    def get_chapters(self, comic, **kwargs) -> list[dict]:
        cid = comic.get("id") if isinstance(comic, dict) else comic
        if not cid:
            return []
        data = self._get(f"/api/comic/{cid}/chapters")
        items = sorted(data.get("list", []), key=lambda x: float(x.get("sortId") or 0))
        seen, chapters = set(), []
        for item in items:
            iid = item.get("id")
            if iid in seen:
                continue
            seen.add(iid)
            chapters.append({
                "id": str(iid),
                "name": item.get("title") or f"第{len(chapters)+1}话",
                "comic_id": str(cid),
            })
        return chapters

    def resolve_read(self, chapter, comic=None) -> list[str]:
        chap_id = chapter.get("id") if isinstance(chapter, dict) else chapter
        if not chap_id:
            raise ValueError("Missing chapter id")
        data = self._get(f"/api/comic/image/{chap_id}", {"page": 1, "page_size": 9999})
        return [img["url"] for img in data.get("images", []) if img.get("url")]

    def fetch_image(self, url: str) -> bytes:
        r = self.session.get(url, timeout=30, headers={
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            "Referer": "https://www.manwali.cc/",
        })
        r.raise_for_status()
        return self.decrypt_image(r.content)
