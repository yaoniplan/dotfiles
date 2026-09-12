# https://github.com/juliusnguyen/noveltrans/blob/main/src/noveltrans/scrapers/sto9.py
"""思兔閱讀 (sto9.com) Provider

对齐 noveltrans scrapers/sto9.py：
  - 详情页 /book/<id>.html：OpenGraph 元数据
  - 目录页 /book/<id>/index.html：仅前十几 + 最后十几章（截断），不可用
  - 完整目录：/ajax_novels/chapterlist/<id>.html
  - 正文：div.txtnav，<br> 分隔；去掉 txtcenter 等广告块
  - 搜索：/search/<kw>/1.html
  - 契约: search / get_chapters / resolve_read
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup

ORIGIN = "https://sto9.com"

MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_7_2 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 "
    "Mobile/15E148 Safari/604.1"
)

_ID_RE = re.compile(r"/(?:book|txt)/(\d+)")
_TOTAL_RE = re.compile(r"(\d+)\s*章")
_WS_RE = re.compile(r"\s+")

SEL_TOC_LINKS = "li[data-num] a[href]"
SEL_CONTENT = "div.txtnav"
SEL_CHROME = "h1, div.txtright, div.txtad, div.txtcenter, script, style, ins"

# 正文夹杂的站内广告
# 清洗：NFKC 同形字 → 去非字母数字查 sto9 → 短语黑名单
_NOISE_RE = re.compile(
    r"還有更新|还有更新|"
    r"最新最快|"
    r"提供最快更新|提供最快的|"
    r"為您提供|为您提供|為您帶來|为您带来|"
    r"本章節來源|本章节来源|"
    r"提醒你可以|提醒您查看|提醒你查看|"
    r"查看最新|觀看最新|观看最新|"
    r"想獲取本書|想获取本书|"
    r"請記住本站|请记住本站|"
    r"手機版閱讀|手机版阅读|"
    r"無彈窗|无弹窗|"
    r"純文字在線|纯文字在线|"
    r"訪問s|访问s|"
    r"最新章節訪問|最新章节访问",
    re.I,
)
# 只保留 a-z0-9，用于拆穿 s⛅to9 / st🎉o9 / 𝚜𝚝𝚘𝟿 等域名插入干扰
_ASCII_ALNUM_RE = re.compile(r"[^a-z0-9]+")


class Provider:
    name = "st"
    #name = "思兔閱讀"
    base = ORIGIN

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": MOBILE_UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
                "Connection": "keep-alive",
            }
        )
        self.headers = dict(self.session.headers)
        self._detail: tuple[str, str] | None = None

    # ------------------------------------------------------------------ network

    def _get_html(self, url: str) -> str:
        r = self.session.get(url, timeout=20)
        r.raise_for_status()
        r.encoding = r.apparent_encoding or "utf-8"
        return r.text

    def _book_id(self, text: str) -> str | None:
        m = _ID_RE.search(text or "")
        return m.group(1) if m else None

    @staticmethod
    def _norm(text: str) -> str:
        return _WS_RE.sub(" ", (text or "")).strip()

    def _detail_url(self, bid: str) -> str:
        return f"{ORIGIN}/book/{bid}.html"

    def _detail_page(self, bid: str) -> str:
        if self._detail is not None and self._detail[0] == bid:
            return self._detail[1]
        html = self._get_html(self._detail_url(bid))
        self._detail = (bid, html)
        return html

    def _parse_meta(self, html: str, bid: str) -> dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")

        def og(prop: str) -> str:
            el = soup.select_one(f"meta[property='{prop}']")
            return (el.get("content") or "").strip() if el else ""

        name = og("og:novel:book_name") or og("og:title")
        if not name:
            h1 = soup.select_one("div.booknav2 h1, h1")
            name = self._norm(h1.get_text()) if h1 else "未知"
        author = og("og:novel:author")
        if not author:
            for row in soup.select("div.booknav2 p"):
                text = self._norm(row.get_text(" "))
                if text.startswith("作者"):
                    author = re.split(r"[:：]", text, maxsplit=1)[-1].strip()
                    break
        desc = og("og:description")
        if len(desc) > 120:
            desc = desc[:120] + "…"
        status = og("og:novel:status") or ""
        remark = " · ".join(p for p in (author, status) if p)
        return {
            "id": bid,
            "name": name or "未知",
            "url": f"/book/{bid}/index.html",
            "author": author,
            "remark": remark,
            "desc": desc,
        }

    def _parse_toc(self, html: str) -> list[dict[str, Any]]:
        soup = BeautifulSoup(html, "html.parser")
        chapters: list[dict[str, Any]] = []
        seen: set[str] = set()
        for a in soup.select(SEL_TOC_LINKS):
            href = (a.get("href") or "").strip()
            if not href:
                continue
            m = re.search(r"/txt/(\d+)/(\d+)\.html", href)
            if not m:
                continue
            bid, cid = m.group(1), m.group(2)
            if cid in seen:
                continue
            seen.add(cid)
            name = self._norm(a.get_text()) or f"第{cid}章"
            full = href if href.startswith("http") else urljoin(ORIGIN, href)
            chapters.append(
                {
                    "id": cid,
                    "name": name,
                    "url": full,
                    "book_id": bid,
                }
            )
        return chapters

    def _is_noise(self, line: str) -> bool:
        """过滤夹在正文里的 sto9 推广句与章末尾巴。

        清洗思路（开源小说抓取常用）：
          1. NFKC：数学字母/全角 → ASCII（𝚜𝚝𝚘𝟿 → sto9）
          2. 只留 a-z0-9 再查 sto9（拆 s⛅to9 / st🎉o9）
          3. 短语黑名单兜底
          4. 短行且像站内尾巴则丢
        """
        raw = (line or "").strip()
        if not raw or raw in (">", "》", "…", "......"):
            return True

        nfkc = unicodedata.normalize("NFKC", raw)
        s = self._norm(nfkc)

        # 域名：去掉一切非 a-z0-9（emoji/点号/空白/装饰）
        letters = _ASCII_ALNUM_RE.sub("", s.lower())
        if "sto9" in letters:
            return True

        # （還有更新耶）等短尾巴
        if len(s) <= 28 and ("還有更新" in s or "还有更新" in s):
            return True
        if _NOISE_RE.search(s):
            return True

        # 短行 + 同时像推广（含「更新」「章節」+「訪問/提供/提醒」）
        if len(s) <= 40:
            if ("更新" in s or "章節" in s or "章节" in s) and (
                "訪問" in s
                or "访问" in s
                or "提供" in s
                or "提醒" in s
                or "觀看" in s
                or "观看" in s
            ):
                return True
        return False

    # ------------------------------------------------------------------ API

    def search(self, keyword: str) -> list[dict[str, Any]]:
        kw = (keyword or "").strip()
        if not kw:
            return []

        bid = self._book_id(kw)
        if not bid and re.fullmatch(r"\d+", kw):
            bid = kw
        if bid and (kw.startswith("http") or re.fullmatch(r"\d+", kw) or "/book/" in kw):
            try:
                return [self._parse_meta(self._detail_page(bid), bid)]
            except Exception:
                return []

        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        try:
            path_kw = quote(kw)
            html = self._get_html(f"{ORIGIN}/search/{path_kw}/1.html")
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.select("a[href*='/book/']"):
                href = a.get("href") or ""
                book_id = self._book_id(href)
                if not book_id or book_id in seen:
                    continue
                name = self._norm(a.get_text())
                if not name or name in ("點擊閱讀", "点击阅读", "加入書架", "加入书架"):
                    continue
                if len(name) > 60:
                    continue
                seen.add(book_id)
                results.append(
                    {
                        "id": book_id,
                        "name": name,
                        "url": f"/book/{book_id}/index.html",
                        "author": "",
                        "remark": "",
                        "desc": "",
                    }
                )
                if len(results) >= 30:
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

        try:
            ajax_html = self._get_html(f"{ORIGIN}/ajax_novels/chapterlist/{bid}.html")
            chapters = self._parse_toc(ajax_html)
            if chapters:
                return chapters
        except Exception:
            pass

        try:
            page_html = self._get_html(f"{ORIGIN}/book/{bid}/index.html")
            page_chapters = self._parse_toc(page_html)
            soup = BeautifulSoup(page_html, "html.parser")
            total = None
            btn = soup.select_one("#loadmore")
            if btn is not None:
                m = _TOTAL_RE.search(btn.get_text(" ", strip=True))
                if m:
                    total = int(m.group(1))
            if total is not None and total > len(page_chapters):
                return []
            return page_chapters
        except Exception:
            return []

    def resolve_read(self, chap: dict, comic: dict | None = None) -> list[str]:
        url = chap.get("url") or ""
        if not url.startswith("http"):
            bid = chap.get("book_id") or (comic or {}).get("id")
            cid = chap.get("id")
            if bid and cid:
                url = f"{ORIGIN}/txt/{bid}/{cid}.html"
            else:
                return []

        html = self._get_html(url)
        soup = BeautifulSoup(html, "html.parser")
        container = soup.select_one(SEL_CONTENT)
        if container is None:
            return []

        for el in container.select(SEL_CHROME):
            el.decompose()

        lines = [
            line.strip()
            for line in container.get_text("\n").split("\n")
            if line.strip()
        ]

        title = chap.get("name") or ""
        if lines and title and self._norm(lines[0]) == self._norm(title):
            lines = lines[1:]

        return [ln for ln in lines if not self._is_noise(ln)]
