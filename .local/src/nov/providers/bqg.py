"""笔趣阁 (bqg5.com) Provider

对齐 noveltrans scrapers/bqg5.py 的实测结论：
  - 必须用移动端 UA，桌面 UA 会 404（UA 白名单，非移动站）
  - 只读 www 布局：落地页一次拿齐元数据 + 全文目录（#list dl）
  - 目录有「最新章节」重复块，必须只取「正文」段
  - 正文在 #content，以 <br> 分隔，非 <p>
  - 响应无 charset，需按 gbk 解码
  - 搜索走 m.bqg5.com/s.php（POST + gbk），比 www search.php 可靠
  - 契约: search / get_chapters / resolve_read
"""

from __future__ import annotations

import re
import time
from typing import Any
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup

ORIGIN = "https://www.bqg5.com"
M_ORIGIN = "https://m.bqg5.com"

MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_7_2 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 "
    "Mobile/15E148 Safari/604.1"
)

_ID_RE = re.compile(r"(?:bqg5\.com/)?(\d+_\d+)", re.I)
_CHAPTER_HREF_RE = re.compile(r"/(\d+_\d+)/(\d+)(?:_(\d+))?\.html")
_WS_RE = re.compile(r"[ \t\u00a0\u3000]+")

SEL_LIST = "#list dl"
SEL_INFO = "#info"
SEL_INTRO = "#intro"
SEL_CONTENT = "#content"
SEL_CHROME = "script, style, ins, iframe, div.bottem1, div.bottem2, div.bookname, h1, a"

_BODY_SECTION = "正文"
_LATEST_SECTION = "最新章节"

_NOISE_RE = re.compile(
    r"(请收藏|加入书签|点击下一页|本章未完|笔趣阁|bqg5|上一页|下一页|返回目录)",
    re.I,
)


class Provider:
    name = "bqg"
    #name = "笔趣阁"
    base = ORIGIN

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": MOBILE_UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Connection": "keep-alive",
            }
        )
        self.headers = dict(self.session.headers)
        self._landing: tuple[str, str] | None = None
        self._last_fetch_ts = 0.0

    # ------------------------------------------------------------------ network

    def _throttle(self, min_interval: float = 0.12) -> None:
        """轻限速，避免连续瀑布加载触发站点拒绝。"""
        now = time.monotonic()
        wait = min_interval - (now - self._last_fetch_ts)
        if wait > 0:
            time.sleep(wait)
        self._last_fetch_ts = time.monotonic()

    def _decode(self, resp: requests.Response) -> str:
        raw = resp.content
        for enc in ("gbk", "gb18030", resp.apparent_encoding or "", "utf-8"):
            if not enc:
                continue
            try:
                return raw.decode(enc)
            except (LookupError, UnicodeDecodeError):
                continue
        return raw.decode("gbk", errors="replace")

    def _get_html(self, url: str, *, retries: int = 4) -> str:
        last_err: Exception | None = None
        for attempt in range(retries):
            try:
                self._throttle()
                r = self.session.get(url, timeout=20)
                if r.status_code in (429, 503, 502, 500):
                    time.sleep(0.6 * (attempt + 1))
                    continue
                r.raise_for_status()
                return self._decode(r)
            except Exception as e:
                last_err = e
                time.sleep(0.4 * (attempt + 1))
        raise RuntimeError(f"GET failed after {retries} tries: {url} ({last_err})")

    def _book_id(self, text: str) -> str | None:
        m = _ID_RE.search(text or "")
        return m.group(1) if m else None

    def _read_url(self, bid: str) -> str:
        return f"{ORIGIN}/{bid}/"

    def _landing_page(self, bid: str) -> str:
        if self._landing is not None and self._landing[0] == bid:
            return self._landing[1]
        html = self._get_html(self._read_url(bid))
        self._landing = (bid, html)
        return html

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _norm(text: str) -> str:
        return _WS_RE.sub(" ", text or "").strip()

    @classmethod
    def _chapter_dds(cls, dl) -> list:
        children = [t for t in dl.children if getattr(t, "name", None)]
        headings = [i for i, t in enumerate(children) if t.name == "dt"]
        real = [i for i in headings if _LATEST_SECTION not in children[i].get_text()]
        start = next(
            (i for i in headings if _BODY_SECTION in children[i].get_text()),
            real[-1] if real else None,
        )
        if start is None:
            return []
        return [t for t in children[start + 1 :] if t.name == "dd"]

    def _parse_meta_from_landing(self, html: str, bid: str) -> dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")
        info = soup.select_one(SEL_INFO)

        def og(prop: str) -> str:
            el = soup.select_one(f"meta[property='{prop}']") or soup.select_one(
                f"meta[name='{prop}']"
            )
            return (el.get("content") or "").strip() if el else ""

        name = og("og:novel:book_name") or og("og:title")
        if not name and info:
            h1 = info.select_one("h1")
            name = self._norm(h1.get_text()) if h1 else ""
        name = name or "未知"

        author = og("og:novel:author")
        if not author and info:
            for row in info.select("p"):
                text = self._norm(row.get_text(" "))
                if text.startswith("作") and len(text) < 40:
                    author = re.split(r"[:：]", text, maxsplit=1)[-1].strip()
                    break

        intro = soup.select_one(SEL_INTRO)
        desc = self._norm(intro.get_text(" ", strip=True)) if intro else og("og:description")
        if len(desc) > 120:
            desc = desc[:120] + "…"

        status = og("og:novel:status") or ""
        remark = " · ".join(p for p in (author, status) if p)

        return {
            "id": bid,
            "name": name,
            "url": f"/{bid}/",
            "author": author,
            "remark": remark,
            "desc": desc,
        }

    def _extract_lines(self, html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        container = soup.select_one(SEL_CONTENT) or soup.select_one(".content")
        if container is None:
            return []
        for junk in container.select(SEL_CHROME):
            junk.decompose()
        lines = [line.strip() for line in container.get_text("\n").split("\n")]
        return [line for line in lines if line]

    def _next_subpage_url(self, html: str, current_url: str) -> str | None:
        """若本章分页（移动站常见 cid_2.html），返回下一分页 URL；下一章不算。"""
        soup = BeautifulSoup(html, "html.parser")
        cur_m = _CHAPTER_HREF_RE.search(current_url)
        if not cur_m:
            return None
        bid, cid, page = cur_m.group(1), cur_m.group(2), cur_m.group(3)
        cur_page = int(page) if page else 1

        for a in soup.select("a#pt_next, a[href]"):
            text = a.get_text(strip=True)
            href = (a.get("href") or "").strip()
            if not href:
                continue
            m = _CHAPTER_HREF_RE.search(href)
            if not m:
                continue
            if m.group(1) != bid or m.group(2) != cid:
                continue  # 下一章，不是分页
            nxt_page = int(m.group(3) or "1")
            if nxt_page > cur_page:
                return urljoin(current_url, href)
            if text in ("下一页", "下页") and nxt_page >= cur_page:
                return urljoin(current_url, href)
        return None

    # ------------------------------------------------------------------ API

    def search(self, keyword: str) -> list[dict[str, Any]]:
        kw = (keyword or "").strip()
        if not kw:
            return []

        bid = self._book_id(kw)
        if bid and (kw.startswith("http") or re.fullmatch(r"\d+_\d+", kw)):
            try:
                html = self._landing_page(bid)
                return [self._parse_meta_from_landing(html, bid)]
            except Exception:
                return []

        results: list[dict[str, Any]] = []
        seen: set[str] = set()

        try:
            q = quote(kw.encode("gbk"))
            self._throttle(0.05)
            r = self.session.post(
                f"{M_ORIGIN}/s.php",
                data=f"keyword={q}&t=1",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Referer": f"{M_ORIGIN}/",
                    "User-Agent": MOBILE_UA,
                },
                timeout=20,
            )
            r.raise_for_status()
            html = self._decode(r)
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.select("a[href]"):
                href = a.get("href") or ""
                book_id = self._book_id(href)
                if not book_id or book_id in seen:
                    continue
                title = a.get_text(" ", strip=True)
                name = title
                author = ""
                if "作者" in title:
                    parts = re.split(r"\s*\|\s*", title)
                    name = parts[0]
                    name = re.sub(r"(玄幻|都市|仙侠|历史|网游|科幻|其他)?小说$", "", name).strip()
                    for p in parts[1:]:
                        if "作者" in p:
                            author = re.sub(r".*作者[:：]?\s*", "", p).strip()
                            author = re.split(r"连载|完本|更新", author)[0].strip()
                if not name or len(name) < 1:
                    continue
                seen.add(book_id)
                results.append(
                    {
                        "id": book_id,
                        "name": name,
                        "url": f"/{book_id}/",
                        "author": author,
                        "remark": author,
                        "desc": "",
                    }
                )
        except Exception:
            pass

        if not results and len(kw) >= 2:
            try:
                html = self._get_html(f"{ORIGIN}/paihangbang/")
                soup = BeautifulSoup(html, "html.parser")
                for a in soup.select("a[href]"):
                    href = a.get("href") or ""
                    book_id = self._book_id(href)
                    title = a.get_text(strip=True)
                    if not book_id or not title or book_id in seen:
                        continue
                    if kw in title or title in kw:
                        seen.add(book_id)
                        results.append(
                            {
                                "id": book_id,
                                "name": title,
                                "url": f"/{book_id}/",
                                "author": "",
                                "remark": "",
                                "desc": "",
                            }
                        )
                        if len(results) >= 15:
                            break
            except Exception:
                pass

        return results

    def get_chapters(self, card: dict) -> list[dict[str, Any]]:
        bid = str(card.get("id") or "").strip()
        if not bid:
            bid = self._book_id(card.get("url") or "") or ""
        if not bid:
            return []

        html = self._landing_page(bid)
        soup = BeautifulSoup(html, "html.parser")
        dl = soup.select_one(SEL_LIST)
        if dl is None:
            return []

        chapters: list[dict[str, Any]] = []
        seen: set[str] = set()
        for dd in self._chapter_dds(dl):
            for a in dd.select("a[href]"):
                href = (a.get("href") or "").strip()
                m = _CHAPTER_HREF_RE.search(href)
                if not m:
                    continue
                # 只要主页 cid.html，不要 cid_2.html 分页
                if m.group(3):
                    continue
                chap_id = m.group(2)
                if chap_id in seen:
                    continue
                seen.add(chap_id)
                name = a.get_text(strip=True) or f"第{chap_id}章"
                full = urljoin(ORIGIN, href)
                chapters.append(
                    {
                        "id": chap_id,
                        "name": name,
                        "url": full,
                        "book_id": bid,
                    }
                )

        # 站点常把同一章挂两次（不同 cid、标题相同；正文可能完全相同或一长一短）。
        # 按标题全局去重，保留首次出现（通常是较完整的那条）。
        seen_titles: set[str] = set()
        deduped: list[dict[str, Any]] = []
        for ch in chapters:
            key = self._norm(ch["name"])
            if key in seen_titles:
                continue
            seen_titles.add(key)
            deduped.append(ch)
        return deduped

    def resolve_read(self, chap: dict, comic: dict | None = None) -> list[str]:
        url = chap.get("url") or ""
        if not url.startswith("http"):
            bid = chap.get("book_id") or (comic or {}).get("id")
            cid = chap.get("id")
            if bid and cid:
                url = f"{ORIGIN}/{bid}/{cid}.html"
            else:
                return []
        # 统一走 www，避免移动站分页截断
        url = url.replace("://m.bqg5.com", "://www.bqg5.com")

        all_lines: list[str] = []
        seen_pages: set[str] = set()
        page_url: str | None = url
        max_pages = 8  # 防止异常环

        while page_url and page_url not in seen_pages and max_pages > 0:
            seen_pages.add(page_url)
            max_pages -= 1
            html = self._get_html(page_url)
            lines = self._extract_lines(html)
            all_lines.extend(lines)
            # www 通常整章一页；若仍出现分页则合并
            page_url = self._next_subpage_url(html, page_url)

        title = chap.get("name") or ""
        if all_lines and title and self._norm(all_lines[0]) == self._norm(title):
            all_lines = all_lines[1:]

        paragraphs = [
            ln for ln in all_lines if not (len(ln) <= 30 and _NOISE_RE.search(ln))
        ]
        return paragraphs
