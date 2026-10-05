"""Z-Library (z-lib.*) Provider

Uses the unofficial mobile EAPI (JSON) which is more stable than HTML scraping
and works on domains that front DiamWall for browsers.

Contract for publications (books) — mirrors nov:
  search(keyword) → list[dict]          # book cards
  get_sections(card) → list[dict]       # spine sections (downloads EPUB once)
  resolve_read(section) → dict          # one section body (html + paragraphs)

Login is required for search / download.
Credentials: never hard-coded. Load from (first match wins for single-account):
  - constructor email/password
  - ZLIB_EMAIL + ZLIB_PASSWORD
  - ZLIB_ACCOUNTS  ("email:pass,email2:pass2")
  - project .env (stdlib loader)
  - ZLIB_ACCOUNTS_FILE or ~/.config/pub/zlib_accounts
    (lines: "email password" or "email:password"; # comments ok)
On daily download limit, the provider rotates to the next account and retries.

References:
  - https://github.com/heartleo/zlib (EAPI docs & domain list)
  - https://github.com/bipinkrish/Zlibrary-API
  - https://github.com/SvnFrs/shadow-bridge/.../zlib.ts
  - https://github.com/codep-alt/bookdrop/.../bookdrop_zlibrary_provider.lua
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests

from downloadutil import download_file
from envutil import load_dotenv

load_dotenv()

# Prefer domains measured healthy for EAPI (2026-09).
# z-lib.sk / z-lib.fm / 1lib.sk are often DiamWall-blocked for automated traffic.
MIRRORS = [
    "https://z-lib.gd",
    "https://z-lib.gl",
    "https://z-library.ec",
    "https://article.sk",
    "https://articles.sk",
    "https://zlib.bz",
]

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

APP_VERSION = "2.5.1"


def _load_accounts(
    email: str | None = None,
    password: str | None = None,
) -> list[tuple[str, str]]:
    """Load (email, password) pairs from args / env / accounts file."""
    out: list[tuple[str, str]] = []

    if email and password:
        out.append((email.strip(), password))

    env_email = (os.environ.get("ZLIB_EMAIL") or "").strip()
    env_pass = os.environ.get("ZLIB_PASSWORD") or ""
    if env_email and env_pass and (env_email, env_pass) not in out:
        out.append((env_email, env_pass))

    multi = (os.environ.get("ZLIB_ACCOUNTS") or "").strip()
    if multi:
        for part in multi.split(","):
            part = part.strip()
            if not part:
                continue
            if ":" in part:
                e, p = part.split(":", 1)
            elif " " in part:
                e, p = part.split(None, 1)
            else:
                continue
            e, p = e.strip(), p.strip()
            if e and p and (e, p) not in out:
                out.append((e, p))

    paths = []
    if os.environ.get("ZLIB_ACCOUNTS_FILE"):
        paths.append(Path(os.environ["ZLIB_ACCOUNTS_FILE"]))
    paths.append(Path.home() / ".config" / "pub" / "zlib_accounts")
    for path in paths:
        try:
            if not path.is_file():
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if ":" in line and " " not in line.split(":", 1)[0]:
                    e, p = line.split(":", 1)
                else:
                    bits = line.split(None, 1)
                    if len(bits) != 2:
                        continue
                    e, p = bits
                e, p = e.strip(), p.strip()
                if e and p and (e, p) not in out:
                    out.append((e, p))
            break  # first existing file wins
        except OSError:
            continue

    return out



_SESSION_CACHE = Path(tempfile.gettempdir()) / "pub-zlib-session.json"
_DOMAIN_CACHE = Path(tempfile.gettempdir()) / "pub-zlib-domain"
# Process-wide reuse: one logged-in client per account email
_CLIENT_POOL: dict[str, "Provider"] = {}


def _load_session_cache() -> dict:
    try:
        if _SESSION_CACHE.is_file():
            data = json.loads(_SESSION_CACHE.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("userkey"):
                # 12h validity
                if time.time() - float(data.get("ts") or 0) < 12 * 3600:
                    return data
    except Exception:
        pass
    return {}


def _save_session_cache(domain: str, userid: str, userkey: str, email: str) -> None:
    try:
        _SESSION_CACHE.write_text(
            json.dumps(
                {
                    "domain": domain,
                    "userid": str(userid),
                    "userkey": userkey,
                    "email": email,
                    "ts": time.time(),
                }
            ),
            encoding="utf-8",
        )
        if domain:
            _DOMAIN_CACHE.write_text(domain, encoding="utf-8")
    except OSError:
        pass



def get_shared_provider(**kwargs) -> "Provider":
    """Reuse a logged-in Provider instance within this process."""
    key = kwargs.get("email") or os.environ.get("ZLIB_EMAIL") or "default"
    # incorporate first account from multi if needed
    p = _CLIENT_POOL.get(key)
    if p is not None and p._logged_in:
        return p
    p = Provider(**kwargs)
    if p._logged_in:
        _CLIENT_POOL[key] = p
    return p


class Provider:
    name = "zlib"

    def __init__(
        self,
        email: str | None = None,
        password: str | None = None,
        domain: str | None = None,
        accounts: list[tuple[str, str]] | None = None,
    ) -> None:
        load_dotenv()
        self.domain = (domain or os.environ.get("ZLIB_DOMAIN") or "").rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": DEFAULT_UA,
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Accept-Language": "en-US,en;q=0.9",
                "X-App-Version": APP_VERSION,
            }
        )
        self._userid: str | None = None
        self._userkey: str | None = None
        self._last_fetch_ts = 0.0
        self._epub_cache: dict[str, Path] = {}
        self._cache_dir = Path(
            os.environ.get("PUB_CACHE")
            or (Path(tempfile.gettempdir()) / "pub-epub-cache")
        )
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._logged_in = False

        self._accounts = accounts or _load_accounts(email, password)
        if not self._accounts:
            raise RuntimeError(
                "No Z-Library credentials. Set ZLIB_EMAIL/ZLIB_PASSWORD, "
                "ZLIB_ACCOUNTS, or ~/.config/pub/zlib_accounts"
            )
        self._account_index = 0
        self.email, self.password = self._accounts[0]
        # Restore cached session → skip login on subsequent searches
        self._restore_session()


    def _restore_session(self) -> bool:
        """Load domain + remix cookies from disk if still valid."""
        data = _load_session_cache()
        if not data:
            return False
        if data.get("email") and data["email"] != self.email:
            return False
        domain = (data.get("domain") or "").rstrip("/")
        userid = data.get("userid")
        userkey = data.get("userkey")
        if not (domain and userid and userkey):
            return False
        self.domain = domain
        self._set_auth_cookies(userid, userkey)
        return True

    # ------------------------------------------------------------------ network helpers

    def _throttle(self, min_interval: float = 0.0) -> None:
        now = time.monotonic()
        wait = min_interval - (now - self._last_fetch_ts)
        if wait > 0:
            time.sleep(wait)
        self._last_fetch_ts = time.monotonic()

    def _ensure_domain(self) -> str:
        if self.domain:
            return self.domain
        # Reuse last good mirror across process runs
        cache = _DOMAIN_CACHE
        try:
            if cache.is_file():
                cached = cache.read_text(encoding="utf-8").strip().rstrip("/")
                if cached:
                    try:
                        r = self.session.get(f"{cached}/eapi/info", timeout=3)
                        if r.status_code == 200 and r.json().get("success"):
                            self.domain = cached
                            return cached
                    except Exception:
                        pass
        except OSError:
            pass

        from concurrent.futures import ThreadPoolExecutor, as_completed

        def probe(cand: str) -> str | None:
            try:
                r = self.session.get(f"{cand}/eapi/info", timeout=3)
                if r.status_code == 200 and r.json().get("success"):
                    return cand
            except Exception:
                return None
            return None

        with ThreadPoolExecutor(max_workers=min(6, len(MIRRORS))) as pool:
            futs = [pool.submit(probe, c) for c in MIRRORS]
            for fut in as_completed(futs):
                hit = fut.result()
                if hit:
                    self.domain = hit
                    try:
                        cache.write_text(hit, encoding="utf-8")
                    except OSError:
                        pass
                    return hit
        raise RuntimeError("No healthy Z-Library EAPI mirror found")

    def _set_auth_cookies(self, userid: str, userkey: str) -> None:
        self._userid = str(userid)
        self._userkey = userkey
        self.session.cookies.set("remix_userid", self._userid)
        self.session.cookies.set("remix_userkey", self._userkey)
        self._logged_in = True

    def login(self) -> bool:
        """Login via EAPI. Returns True on success."""
        if self._logged_in and self._userid and self._userkey:
            return True
        base = self._ensure_domain()
        self._throttle()
        try:
            r = self.session.post(
                f"{base}/eapi/user/login",
                data={"email": self.email, "password": self.password},
                timeout=8,
            )
            data = r.json()
            if data.get("success") and data.get("user"):
                u = data["user"]
                self._set_auth_cookies(u["id"], u["remix_userkey"])
                _save_session_cache(base, u["id"], u["remix_userkey"], self.email)
                return True
            # Fallback: some domains reject /eapi/user/login but accept /rpc.php
            return self._login_rpc(base)
        except Exception:
            return self._login_rpc(base)

    def _login_rpc(self, base: str) -> bool:
        """HTML-form style login that still yields remix_* cookies usable by EAPI."""
        self._throttle()
        try:
            r = self.session.post(
                f"{base}/rpc.php",
                data={
                    "email": self.email,
                    "password": self.password,
                    "action": "login",
                    "gg_json_mode": 1,
                    "isSinglelogin": 1,
                    "site_mode": "books",
                },
                timeout=8,
            )
            data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            # Cookies may be set even when JSON shape varies
            userid = self.session.cookies.get("remix_userid")
            userkey = self.session.cookies.get("remix_userkey")
            if userid and userkey:
                self._set_auth_cookies(userid, userkey)
                _save_session_cache(base, userid, userkey, self.email)
                return True
            if data.get("success") and data.get("user"):
                u = data["user"]
                uk = u.get("remix_userkey") or u.get("userkey")
                self._set_auth_cookies(u["id"], uk)
                _save_session_cache(base, u["id"], uk, self.email)
                return True
        except Exception:
            pass
        return False

    def _reset_session_auth(self) -> None:
        self._logged_in = False
        self._userid = None
        self._userkey = None
        for k in ("remix_userid", "remix_userkey"):
            try:
                self.session.cookies.clear(domain=None, path=None, name=k)
            except Exception:
                pass
        # clear all remix cookies across domains
        try:
            jar = self.session.cookies
            for c in list(jar):
                if c.name in ("remix_userid", "remix_userkey"):
                    jar.clear(c.domain, c.path, c.name)
        except Exception:
            pass

    def _use_account(self, index: int) -> bool:
        if index < 0 or index >= len(self._accounts):
            return False
        self._account_index = index
        self.email, self.password = self._accounts[index]
        self._reset_session_auth()
        return self.login()

    def _rotate_account(self) -> bool:
        """Switch to the next configured account. Returns False if none left."""
        n = len(self._accounts)
        if n <= 1:
            return False
        start = self._account_index
        for step in range(1, n):
            idx = (start + step) % n
            if self._use_account(idx):
                return True
        return False


    def _request(
        self,
        method: str,
        path: str,
        *,
        data: dict | None = None,
        params: dict | None = None,
        retries: int = 3,
    ) -> dict[str, Any]:
        if not self._logged_in:
            if not self.login():
                raise RuntimeError("Z-Library login failed")
        base = self._ensure_domain()
        url = urljoin(base + "/", path.lstrip("/"))
        last_err: Exception | None = None
        for attempt in range(retries):
            try:
                self._throttle()
                if method.upper() == "POST":
                    r = self.session.post(url, data=data or {}, timeout=12)
                else:
                    r = self.session.get(url, params=params, timeout=12)
                if r.status_code in (401, 403):
                    self._logged_in = False
                    if self.login():
                        continue
                    raise RuntimeError("Auth expired and re-login failed")
                if r.status_code in (429, 502, 503, 517):
                    time.sleep(0.8 * (attempt + 1))
                    continue
                r.raise_for_status()
                return r.json()
            except Exception as e:
                last_err = e
                time.sleep(0.5 * (attempt + 1))
        raise RuntimeError(f"Request failed after retries: {last_err}")

    # ------------------------------------------------------------------ public API

    def search(self, keyword: str, *, limit: int = 30) -> list[dict]:
        """Search books. Returns list of cards compatible with selector.

        Card keys:
          id, name, author, year, extension, size, language, hash, cover,
          remark, url, readOnlineUrl, ...
        """
        data = self._request(
            "POST",
            "/eapi/book/search",
            data={
                "message": keyword,
                "limit": str(limit),
            },
        )
        if not data.get("success"):
            return []
        books = data.get("books") or data.get("result") or []
        out: list[dict] = []
        for b in books:
            title = (b.get("title") or "Untitled").strip()
            author = (b.get("author") or "").strip()
            ext = (b.get("extension") or "").lower()
            size = b.get("filesizeString") or ""
            year = b.get("year") or ""
            lang = (b.get("language") or "").strip()
            remark_parts = [p for p in (ext.upper() if ext else None, size, str(year) if year else None, lang) if p]
            card = {
                "id": str(b.get("id", "")),
                "name": title,
                "author": author,
                "year": year,
                "extension": ext,
                "size": size,
                "filesize": b.get("filesize"),
                "language": lang,
                "hash": b.get("hash") or "",
                "cover": b.get("cover") or "",
                "md5": b.get("md5") or "",
                "sha256": b.get("sha256") or "",
                "url": b.get("href") or "",
                "dl": b.get("dl") or "",
                "readOnlineUrl": b.get("readOnlineUrl") or "",
                "remark": " · ".join(remark_parts),
                "raw": b,
            }
            out.append(card)
        return out


    def resolve_file(self, card: dict) -> dict[str, Any]:
        """Resolve direct download link via EAPI /file.

        On daily limit / empty link, rotate through configured accounts.
        """
        book_id = card.get("id")
        book_hash = card.get("hash")
        if not book_id or not book_hash:
            raise ValueError("card missing id/hash; cannot resolve download")

        tried = 0
        last_msg = ""
        while tried < max(1, len(self._accounts)):
            data = self._request("GET", f"/eapi/book/{book_id}/{book_hash}/file")
            if not data.get("success") or not data.get("file"):
                raise RuntimeError(f"file resolve failed: {data}")

            f = data["file"]
            ddl = f.get("downloadLink") or ""
            allow = f.get("allowDownload")
            if ddl and allow is not False:
                title = card.get("name") or "book"
                author = card.get("author") or ""
                ext = (f.get("extension") or card.get("extension") or "epub").lower()
                filename = f.get("description") or title
                if author and author not in filename:
                    filename = f"{filename} ({author})"
                filename = f"{filename}.{ext}"
                return {
                    "kind": "download",
                    "url": ddl,
                    "extension": ext,
                    "title": title,
                    "author": author,
                    "filename": filename,
                    "downloadLink": ddl,
                    "card": card,
                }

            last_msg = f.get("disallowDownloadMessage") or "no download link"
            tried += 1
            if not self._rotate_account():
                break

        raise RuntimeError(f"no download link ({last_msg})")

    def ensure_file(self, card: dict) -> Path:
        """Download book file once and cache by id + extension."""
        book_id = str(card.get("id") or "")
        if not book_id:
            raise ValueError("card missing id")
        ext = (card.get("extension") or "epub").lower()
        if ext == "epub3":
            ext = "epub"

        cached = self._epub_cache.get(f"{book_id}.{ext}")
        if cached and cached.is_file():
            return cached

        disk = self._cache_dir / f"{book_id}.{ext}"
        if disk.is_file() and disk.stat().st_size > 0:
            self._epub_cache[f"{book_id}.{ext}"] = disk
            return disk

        meta = self.resolve_file(card)
        ddl = meta.get("downloadLink") or meta.get("url")
        if not ddl:
            raise RuntimeError("no download link")

        download_file(
            ddl,
            disk,
            headers={"User-Agent": self.session.headers.get("User-Agent", "")},
            session=self.session,
            min_bytes=1000,
        )
        self._epub_cache[f"{book_id}.{ext}"] = disk
        return disk

    def ensure_epub(self, card: dict) -> Path:
        """Download EPUB once, validate, cache. Returns local path."""
        from epub_spine import open_epub

        ext = (card.get("extension") or "epub").lower()
        if ext not in ("epub", "epub3"):
            raise ValueError(f"ensure_epub requires EPUB, got .{ext}")
        disk = self.ensure_file(card)
        open_epub(disk, title_hint=card.get("name") or "")
        return disk

    def iter_sections(self, card: dict):
        """Yield spine sections (EPUB) or pages (PDF) one-by-one."""
        from epub_spine import open_epub

        ext = (card.get("extension") or "epub").lower()
        if ext == "pdf":
            from pdf_util import page_count

            path = self.ensure_file(card)
            n = page_count(path)
            for i in range(n):
                yield {
                    "name": f"Page {i + 1}",
                    "index": i,
                    "path": str(path),
                    "id": str(card.get("id") or ""),
                    "title": card.get("name") or "",
                    "card": card,
                    "kind": "pdf",
                }
            return

        path = self.ensure_epub(card)
        book = open_epub(path, title_hint=card.get("name") or "")
        try:
            for i, href in enumerate(book.spine):
                name = book.labels[i] if i < len(book.labels) else f"§ {i + 1}"
                yield {
                    "name": name,
                    "index": i,
                    "href": href,
                    "path": str(path),
                    "id": str(card.get("id") or ""),
                    "title": book.title,
                    "card": card,
                }
        finally:
            book.close()

    def get_sections(self, card: dict) -> list[dict]:
        """Materialize full spine list (compat). Prefer iter_sections for streaming."""
        return list(self.iter_sections(card))

    def resolve_read(self, section: dict) -> dict[str, Any]:
        """Load one section body (html with image URLs + paragraphs)."""
        if section.get("kind") == "pdf":
            return {
                "kind": "pdf",
                "index": int(section.get("index", 0)),
                "path": section.get("path"),
                "name": section.get("name"),
            }
        from epub_spine import open_epub

        path = section.get("path")
        if not path:
            card = section.get("card")
            if not card:
                raise ValueError("section missing path/card")
            path = str(self.ensure_epub(card))
        index = int(section.get("index", 0))
        book = open_epub(path, title_hint=section.get("title") or "")
        try:
            payload = book.section_payload(index)
        finally:
            book.close()
        payload["index"] = index
        payload["name"] = section.get("name") or payload.get("title")
        payload["path"] = path
        return payload


    def get_profile(self) -> dict[str, Any]:
        """Return user profile (quota etc.)."""
        data = self._request("GET", "/eapi/user/profile")
        return data.get("user") or data

    def get_book_info(self, card: dict) -> dict[str, Any]:
        book_id = card.get("id")
        book_hash = card.get("hash")
        if not book_id or not book_hash:
            raise ValueError("card missing id/hash")
        data = self._request("GET", f"/eapi/book/{book_id}/{book_hash}")
        return data
