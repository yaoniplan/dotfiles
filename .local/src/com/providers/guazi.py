import re
import requests
from bs4 import BeautifulSoup


class Provider:
    name = "guazi"
    #name = "瓜子漫画"

    def __init__(self, base_url: str = "https://www.guazimanhua.com"):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

    def _get(self, endpoint: str, params: dict = None) -> str:
        r = requests.get(
            f"{self.base_url}{endpoint}",
            headers=self.headers,
            params=params,
            timeout=15,
        )
        r.raise_for_status()
        r.encoding = r.apparent_encoding or "utf-8"
        return r.text

    def _id(self, obj, *keys):
        if isinstance(obj, dict):
            for k in keys:
                if obj.get(k):
                    return str(obj[k])
        return str(obj) if obj else None

    # ── required ──────────────────────────────────────────────────────
    def search(self, query: str, limit: int = 36, offset: int = 0) -> list[dict]:
        page = offset // 36 + 1 if offset else 1
        html = self._get("/category.php", {"keyword": query, "sort": "hits", "page": page})
        soup = BeautifulSoup(html, "html.parser")
        out = []
        for card in soup.select("article.card"):
            a = card.select_one("a.cover-wrap")
            if not a:
                continue
            m = re.search(r"id=(\d+)", a.get("href", ""))
            if not m:
                continue
            name_tag = card.select_one("h3 a")
            name = name_tag.get_text(strip=True) if name_tag else "未知漫画"
            cover_img = card.select_one("img.cover")
            meta = card.select_one(".meta")
            author = "未知作者"
            if meta:
                parts = [p.strip() for p in meta.get_text(" ", strip=True).split("·") if p.strip()]
                if parts:
                    author = parts[0]
            out.append({
                "id": m.group(1),
                "name": name,
                "cover": cover_img.get("src") if cover_img else "",
                "remark": author,
            })
            if len(out) >= limit:
                break
        return out

    def get_chapters(self, comic, **kwargs) -> list[dict]:
        cid = self._id(comic, "id", "comic_id")
        if not cid:
            return []
        html = self._get("/comic.php", {"id": cid})
        soup = BeautifulSoup(html, "html.parser")
        container = (
            soup.select_one("div[data-chapter-list]")
            or soup.select_one("div[data-mobile-chapter-list]")
            or soup.select_one(".all-chapter-grid")
        )
        links = container.select("a[href^='/chapter.php?id=']") if container else soup.select("a[href^='/chapter.php?id=']")
        chapters, seen = [], set()
        for a in links:
            m = re.search(r"id=(\d+)", a.get("href", ""))
            if not m:
                continue
            uid = m.group(1)
            if uid in seen:
                continue
            seen.add(uid)
            name = a.get_text(strip=True)
            if not name:
                continue
            chapters.append({"id": uid, "name": name, "comic_id": cid})
        chapters.reverse()  # site is newest-first
        return chapters

    def resolve_read(self, chapter, comic=None) -> list[str]:
        chap_id = self._id(chapter, "id", "uuid")
        if not chap_id:
            raise ValueError("Missing chapter id")
        html = self._get("/chapter.php", {"id": chap_id})
        soup = BeautifulSoup(html, "html.parser")
        imgs = soup.select("section.reader-images img.reading-image") or soup.select("img.reading-image")
        urls, seen = [], set()
        for img in imgs:
            src = img.get("src")
            if not src:
                continue
            fname = src.rsplit("/", 1)[-1]
            if fname in seen:
                continue
            seen.add(fname)
            urls.append(src)
        return urls
