import requests


class Provider:
    name = "copy"
    #name = "拷貝漫畫"

    def __init__(self, base_url: str = "https://api.manga2025.com"):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        }

    def _get(self, endpoint, params=None):
        r = requests.get(f"{self.base_url}{endpoint}", headers=self.headers, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get("code") != 200:
            raise ValueError(f"API Error ({data.get('code')}): {data.get('message')}")
        return data.get("results", {})

    def _id(self, obj, *keys):
        if isinstance(obj, dict):
            for k in keys:
                if obj.get(k):
                    return obj[k]
        return str(obj) if obj else None

    def search(self, query: str, limit: int = 21, offset: int = 0) -> list[dict]:
        results = self._get("/api/v3/search/comic", {
            "q": query, "q_type": "", "limit": limit, "offset": offset, "_update": "true"
        })
        out = []
        for item in results.get("list", []):
            authors = [a["name"] for a in item.get("author", []) if a.get("name")]
            out.append({
                "id": item.get("path_word"),
                "name": item.get("name"),
                "cover": item.get("cover"),
                "remark": ", ".join(authors) or "未知作者",
            })
        return out

    def get_chapters(self, comic, group: str = "default", limit: int = 100, fetch_all: bool = True) -> list[dict]:
        cid = self._id(comic, "id", "comic_id", "path_word")
        endpoint = f"/api/v3/comic/{cid}/group/{group}/chapters"
        chapters, offset = [], 0
        while True:
            results = self._get(endpoint, {"limit": limit, "offset": offset, "_update": "true"})
            items = results.get("list", [])
            for item in items:
                chapters.append({
                    "id": item.get("uuid"),
                    "name": item.get("name"),
                    "comic_id": cid,
                })
            total = results.get("total", 0)
            offset += len(items)
            if not fetch_all or offset >= total or not items:
                break
        return chapters

    def resolve_read(self, chapter, comic=None) -> list[str]:
        chap_id = self._id(chapter, "id", "uuid")
        comic_id = self._id(chapter, "comic_id") if isinstance(chapter, dict) else None
        if comic:
            comic_id = self._id(comic, "id", "comic_id", "path_word")
        if not comic_id or not chap_id:
            raise ValueError("comic_id and chapter_id required")
        results = self._get(f"/api/v3/comic/{comic_id}/chapter/{chap_id}")
        return [img["url"] for img in results.get("chapter", {}).get("contents", []) if img.get("url")]
