"""Local section waterfall reader (nov-style) with image resources.

Provider supplies:
  get_sections(card) → [{name, index, path, ...}, ...]
  resolve_read(section) → {title, html, paragraphs, images}

HTTP:
  GET /                 → reader shell
  GET /api/section?i=N  → provider.resolve_read(sections[N])
  GET /api/resource?path=… → bytes from EPUB zip (images)
"""

from __future__ import annotations

import json
import mimetypes
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, unquote, urlparse

SHOW_BROWSER_LOGS = False
PRELOAD_MARGIN_PX = 3500

READER_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>__BOOK_TITLE__</title>
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
  <style>
    :root {
      --bg: #f7f7f5;
      --fg: #1c1c1e;
      --muted: #8e8e93;
    }
    @media (prefers-color-scheme: dark) {
      :root {
        --bg: #1c1c1e;
        --fg: #f2f2f7;
        --muted: #8e8e93;
      }
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    html, body {
      background: var(--bg);
      color: var(--fg);
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display",
                   "PingFang SC", "Hiragino Sans GB", "Helvetica Neue",
                   "Microsoft YaHei", system-ui, sans-serif;
      -webkit-font-smoothing: antialiased;
      -webkit-text-size-adjust: 100%;
      scroll-behavior: auto !important;
      min-height: 100vh;
      font-size: 18px;
      line-height: 1.65;
    }
    body {
      display: flex;
      flex-direction: column;
      align-items: center;
    }
    #container {
      width: 100%;
      max-width: 720px;
      min-height: 60vh;
      padding: 1.5rem 1.25rem 4rem;
    }
    .section {
      padding: 1.75rem 0 0.5rem;
      overflow-anchor: none;
    }
    .section:last-of-type { overflow-anchor: auto; }
    .section:first-child { padding-top: 0.5rem; }
    .section-title {
      font-size: 1.15rem;
      font-weight: 600;
      color: var(--fg);
      line-height: 1.4;
      text-align: center;
      margin: 0 0 1.25rem;
      letter-spacing: 0.02em;
    }
    .section-body p {
      text-indent: 2em;
      text-align: justify;
      word-break: break-word;
      margin: 0 0 1em;
    }
    .section-body p:last-child { margin-bottom: 0; }
    .section-body .img-wrap {
      margin: 1rem 0;
      text-align: center;
      text-indent: 0;
    }
    .section-body .img-wrap img {
      max-width: 100%;
      height: auto;
      border-radius: 4px;
      vertical-align: middle;
    }
    .loading-box {
      display: flex; align-items: center; justify-content: center;
      gap: 0.5rem; color: var(--muted); font-size: 0.9rem;
      padding: 1rem 0 2rem;
    }
    .spinner {
      width: 18px; height: 18px;
      border: 2px solid var(--muted);
      border-top-color: transparent;
      border-radius: 50%;
      animation: spin 0.7s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    #sentinel { height: 1px; width: 100%; }
    #end {
      text-align: center; color: var(--muted);
      font-size: 0.85rem; padding: 2rem 0 1rem;
      display: none;
    }
  </style>
</head>
<body>
  <div id="container"></div>
  <div id="sentinel"></div>
  <div id="end">— 全书完 —</div>
  <script>
    const TOTAL = __TOTAL_SECTIONS__;
    const PRELOAD_MARGIN = __PRELOAD_MARGIN__;
    // Prefer ?start=N so selection cannot be lost in HTML templating
    const START = (() => {
      const q = parseInt(new URLSearchParams(location.search).get('start') || '', 10);
      if (!Number.isNaN(q) && q >= 0) return q;
      return __START_INDEX__;
    })();
    const LABELS = __SECTION_LABELS__;
    const container = document.getElementById('container');
    const sentinel = document.getElementById('sentinel');
    const endEl = document.getElementById('end');

    let nextIndex = START;
    let loading = false;
    const cache = new Map();
    // Dynamic: only resolve_read from START forward; never pull 0..START-1

    async function fetchSection(index) {
      if (cache.has(index)) return cache.get(index);
      const res = await fetch('/api/section?index=' + index);
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      cache.set(index, data);
      return data;
    }

    async function appendNext() {
      if (loading) return;
      if (nextIndex >= TOTAL) {
        endEl.style.display = 'block';
        return;
      }
      loading = true;
      const index = nextIndex;
      const block = document.createElement('div');
      block.className = 'section';
      block.dataset.index = String(index);

      const titleEl = document.createElement('h2');
      titleEl.className = 'section-title';
      titleEl.textContent = LABELS[index] || ('§ ' + (index + 1));
      block.appendChild(titleEl);

      const loadingEl = document.createElement('div');
      loadingEl.className = 'loading-box';
      loadingEl.innerHTML = '<div class="spinner"></div><span>加载中…</span>';
      block.appendChild(loadingEl);
      container.appendChild(block);

      try {
        const data = await fetchSection(index);
        block.removeChild(loadingEl);
        if (data.title) titleEl.textContent = data.title;
        const body = document.createElement('div');
        body.className = 'section-body';
        if (data.html) {
          body.innerHTML = data.html;
        } else {
          const paras = data.paragraphs || [];
          for (let i = 0; i < paras.length; i++) {
            const p = document.createElement('p');
            p.textContent = paras[i];
            body.appendChild(p);
          }
          if (!paras.length) {
            const p = document.createElement('p');
            p.style.textIndent = '0';
            p.style.color = 'var(--muted)';
            p.textContent = '（本节无文本）';
            body.appendChild(p);
          }
        }
        block.appendChild(body);
        nextIndex++;
        if (nextIndex < TOTAL) fetchSection(nextIndex).catch(() => {});
      } catch (e) {
        loadingEl.innerHTML = '<span>加载失败，重试中…</span>';
        setTimeout(() => {
          if (block.parentNode) container.removeChild(block);
          loading = false;
          cache.delete(index);
          maybeLoadMore();
        }, 1200);
        return;
      } finally {
        loading = false;
      }
      maybeLoadMore();
    }

    let sentinelVisible = true;
    function maybeLoadMore() {
      if (!sentinelVisible || loading || nextIndex >= TOTAL) return;
      requestAnimationFrame(() => appendNext());
    }

    const obs = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        sentinelVisible = entry.isIntersecting;
        if (sentinelVisible) maybeLoadMore();
      });
    }, { rootMargin: PRELOAD_MARGIN + 'px 0px ' + PRELOAD_MARGIN + 'px 0px' });
    obs.observe(sentinel);
    appendNext();
  </script>
</body>
</html>
"""


def get_free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def load_custom_flags() -> list[str]:
    path = Path(__file__).resolve().parent / "chromium-flags.conf"
    flags: list[str] = []
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                flags.append(line)
    return flags


def _find_browser() -> str | None:
    for name in (
        "chromium",
        "chromium-browser",
        "google-chrome",
        "google-chrome-stable",
        "brave-browser",
        "microsoft-edge",
        "firefox",
    ):
        p = shutil.which(name)
        if p:
            return p
    mac = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if os.path.isfile(mac):
        return mac
    return None



PDF_HTML = r"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>__TITLE__</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    /* Match com/reader.py image waterfall */
    * { box-sizing: border-box; }
    html, body {
      margin: 0;
      background: #000000;
      color: #ffffff;
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", "Segoe UI", Roboto, sans-serif;
      display: flex;
      flex-direction: column;
      align-items: center;
      scroll-behavior: auto !important;
    }
    #container { width: 100%; max-width: 800px; min-height: 100vh; }

    .img-wrap {
      width: 100%;
      position: relative;
      line-height: 0;
      font-size: 0;
    }
    canvas.comic-img, img.comic-img {
      width: 100%;
      height: auto;
      display: block;
      margin: 0;
      border: none;
      padding: 0;
      background: #000000;
      vertical-align: top;
      opacity: 0;
      transition: opacity 0.2s ease-in-out;
    }
    canvas.comic-img.loaded, img.comic-img.loaded {
      opacity: 1;
    }
    .img-wrap:not(.ready) {
      min-height: 200px;
      background: #000;
    }
    .img-wrap.ready { min-height: 0; }

    #sentinel { height: 100px; width: 100%; }

    #status {
      position: fixed; inset: 0;
      display: flex; align-items: center; justify-content: center;
      color: #888; background: #000; z-index: 10;
    }
    #status.hidden { display: none; }
  </style>
</head>
<body>
  <div id="status">Loading…</div>
  <div id="container"></div>
  <div id="sentinel"></div>
  <script type="module">
    import * as pdfjsLib from "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.8.69/pdf.min.mjs";
    pdfjsLib.GlobalWorkerOptions.workerSrc =
      "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.8.69/pdf.worker.min.mjs";

    const status = document.getElementById("status");
    const container = document.getElementById("container");
    const sentinel = document.getElementById("sentinel");
    const startPage = Math.max(1, parseInt(
      new URLSearchParams(location.search).get("page") || "__START_PAGE__", 10) || 1);
    // Light DPR — enough sharpness, less GPU heat (com serves pre-made images)
    const dpr = Math.min(window.devicePixelRatio || 1, 1.25);
    const maxCssWidth = 800;

    let pdf = null;
    const wraps = [];
    const rendering = new Set();

    async function paint(wrap) {
      const num = wrap._pageNum;
      if (wrap._painted || rendering.has(num) || !pdf) return;
      rendering.add(num);
      try {
        const page = await pdf.getPage(num);
        const base = page.getViewport({ scale: 1 });
        const cssW = Math.min(window.innerWidth, maxCssWidth);
        const scale = (cssW * dpr) / base.width;
        const viewport = page.getViewport({ scale });
        const canvas = document.createElement("canvas");
        canvas.className = "comic-img";
        canvas.width = Math.floor(viewport.width);
        canvas.height = Math.floor(viewport.height);
        const ctx = canvas.getContext("2d", { alpha: false });
        await page.render({ canvasContext: ctx, viewport }).promise;
        wrap.innerHTML = "";
        wrap.appendChild(canvas);
        // force layout then fade in (same idea as com .loaded)
        requestAnimationFrame(() => {
          canvas.classList.add("loaded");
          wrap.classList.add("ready");
        });
        wrap._painted = true;
      } catch (e) {
        console.warn("page render failed", num, e);
      } finally {
        rendering.delete(num);
      }
    }

    try {
      pdf = await pdfjsLib.getDocument({ url: "/book.pdf", withCredentials: false }).promise;
      status.classList.add("hidden");

      // Build slots for all pages (layout only — paint on demand, like com imgObserver)
      for (let i = 1; i <= pdf.numPages; i++) {
        const wrap = document.createElement("div");
        wrap.className = "img-wrap";
        wrap.dataset.page = String(i);
        wrap._pageNum = i;
        wrap._painted = false;
        wraps.push(wrap);
        container.appendChild(wrap);
      }

      const imgObserver = new IntersectionObserver((entries) => {
        for (const e of entries) {
          if (e.isIntersecting) paint(e.target);
        }
      }, { root: null, rootMargin: "150% 0px", threshold: 0.01 });

      wraps.forEach((w) => imgObserver.observe(w));

      // Start page
      const target = wraps[startPage - 1];
      if (target) {
        target.scrollIntoView({ block: "start" });
        paint(target);
        // also paint neighbors so scroll isn't black
        if (wraps[startPage - 2]) paint(wraps[startPage - 2]);
        if (wraps[startPage]) paint(wraps[startPage]);
      }

      addEventListener("keydown", (e) => {
        const mid = document.elementFromPoint(innerWidth / 2, innerHeight / 2);
        const cur = parseInt(mid?.closest?.(".img-wrap")?.dataset?.page || startPage, 10);
        if (e.key === "ArrowRight" || e.key === "PageDown" || e.key === " ") {
          e.preventDefault();
          const n = Math.min(pdf.numPages, cur + 1);
          wraps[n - 1]?.scrollIntoView({ block: "start" });
          paint(wraps[n - 1]);
        } else if (e.key === "ArrowLeft" || e.key === "PageUp") {
          e.preventDefault();
          const n = Math.max(1, cur - 1);
          wraps[n - 1]?.scrollIntoView({ block: "start" });
          paint(wraps[n - 1]);
        }
      });
    } catch (err) {
      status.textContent = "Failed: " + (err && err.message ? err.message : err);
      status.classList.remove("hidden");
    }
  </script>
</body>
</html>
"""



def _detach_reader_process() -> bool:
    """Fork like nov/com: parent returns to shell; child becomes session leader.

    Returns True in the child, False in the parent (caller should exit).
    On fork failure, returns True so the caller continues in-process.
    """
    try:
        if os.fork() > 0:
            return False
    except OSError:
        return True
    try:
        os.setsid()
    except Exception:
        pass
    try:
        devnull = os.open(os.devnull, os.O_RDWR)
        os.dup2(devnull, 0)
        if not SHOW_BROWSER_LOGS:
            os.dup2(devnull, 1)
            os.dup2(devnull, 2)
        os.close(devnull)
    except Exception:
        pass
    return True



def launch_online(url: str, title: str = "") -> None:
    """Open an online reader URL in the system browser (fallback)."""
    browser = _find_browser()
    print(f"▶ {title or 'Online reader'}")
    print(f"  {url[:120]}{'…' if len(url) > 120 else ''}")
    if not browser:
        import webbrowser
        webbrowser.open(url)
        return
    if "firefox" in browser:
        subprocess.Popen([browser, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    udd = tempfile.mkdtemp(prefix="pub-online-")
    flags = load_custom_flags()
    cmd = [browser, f"--app={url}", f"--user-data-dir={udd}"] + flags
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)



def launch_pdf_reader(
    pdf_path: str | Path,
    title: str = "PDF",
    start_page: int = 1,
    source: str = "",
) -> None:
    """Serve a local PDF and render with PDF.js (same-origin)."""
    pdf_path = Path(pdf_path)
    if not pdf_path.is_file():
        raise FileNotFoundError(pdf_path)

    port = get_free_port()
    url = f"http://127.0.0.1:{port}/?page={max(1, int(start_page))}"
    src = f"[{source}] " if source else ""
    print(f"▶ {src}{title}")
    print(f"  {url}")
    if not _detach_reader_process():
        sys.exit(0)

    udd = tempfile.mkdtemp(prefix="pub-pdf-")
    pdf_bytes = pdf_path.read_bytes()
    safe_title = title.replace("<", "").replace(">", "")
    html = (
        PDF_HTML.replace("__TITLE__", safe_title)
        .replace("__START_PAGE__", str(max(1, int(start_page))))
        .replace("__PRELOAD_MARGIN__", str(PRELOAD_MARGIN_PX))
    )

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # noqa: A003
            pass

        def do_GET(self):  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path in ("/", "/index.html"):
                body = html.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
                return
            if parsed.path == "/book.pdf":
                self.send_response(200)
                self.send_header("Content-Type", "application/pdf")
                self.send_header("Content-Length", str(len(pdf_bytes)))
                self.send_header("Content-Disposition", "inline")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(pdf_bytes)
                return
            self.send_error(404)

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    browser = _find_browser()

    if not browser:
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            pass
        finally:
            server.shutdown()
            shutil.rmtree(udd, ignore_errors=True)
        os._exit(0)

    flags = load_custom_flags()
    if "firefox" in browser:
        cmd = [browser, url]
    else:
        cmd = [browser, f"--app={url}", f"--user-data-dir={udd}"] + flags

    kw = (
        {}
        if SHOW_BROWSER_LOGS
        else {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    )
    try:
        subprocess.run(cmd, **kw)
    finally:
        server.shutdown()
        shutil.rmtree(udd, ignore_errors=True)
    os._exit(0)



def launch_reader(
    provider,
    card: dict,
    sections: list[dict],
    start_index: int = 0,
) -> None:
    title = card.get("name") or sections[0].get("title") or "Book"
    labels = [s.get("name") or f"§ {i + 1}" for i, s in enumerate(sections)]
    epub_path = sections[0].get("path") if sections else None

    html = (
        READER_HTML.replace("__BOOK_TITLE__", json.dumps(title)[1:-1])
        .replace("__TOTAL_SECTIONS__", str(len(sections)))
        .replace("__START_INDEX__", str(max(0, min(start_index, len(sections) - 1))))
        .replace("__PRELOAD_MARGIN__", str(PRELOAD_MARGIN_PX))
        .replace("__SECTION_LABELS__", json.dumps(labels, ensure_ascii=False))
    )

    port = get_free_port()
    url = f"http://127.0.0.1:{port}/?start={start_index}"
    src = (
        card.get("_provider_module")
        or getattr(provider, "name", None)
        or card.get("source")
        or ""
    )
    src = f"[{src}] " if src else ""
    print(f"▶ {src}{title}  (from §{start_index + 1}/{len(sections)})")
    print(f"  {url}")
    if not _detach_reader_process():
        sys.exit(0)

    udd = tempfile.mkdtemp(prefix="pub-reader-")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # noqa: A003
            pass

        def do_GET(self):  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path in ("/", "/index.html"):
                body = html.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
                return

            if parsed.path == "/api/section":
                qs = parse_qs(parsed.query)
                try:
                    idx = int(qs.get("index", ["0"])[0])
                except ValueError:
                    idx = 0
                try:
                    if idx < 0 or idx >= len(sections):
                        raise IndexError("out of range")
                    data = provider.resolve_read(sections[idx])
                except Exception as e:
                    data = {"error": str(e)}
                body = json.dumps(data, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
                return

            if parsed.path == "/api/resource":
                qs = parse_qs(parsed.query)
                rel = unquote((qs.get("path") or [""])[0]).lstrip("/")
                if not rel or ".." in rel.split("/"):
                    self.send_error(400)
                    return
                if not epub_path or not Path(epub_path).is_file():
                    self.send_error(404)
                    return
                try:
                    with zipfile.ZipFile(epub_path) as z:
                        try:
                            data = z.read(rel)
                        except KeyError:
                            lower = {n.lower(): n for n in z.namelist()}
                            real = lower.get(rel.lower())
                            if not real:
                                self.send_error(404)
                                return
                            data = z.read(real)
                            rel = real
                    ctype, _ = mimetypes.guess_type(rel)
                    if not ctype:
                        ctype = (
                            "image/svg+xml"
                            if rel.lower().endswith(".svg")
                            else "application/octet-stream"
                        )
                    self.send_response(200)
                    self.send_header("Content-Type", ctype)
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Cache-Control", "public, max-age=86400")
                    self.end_headers()
                    self.wfile.write(data)
                except Exception:
                    self.send_error(404)
                return

            self.send_error(404)

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    browser = _find_browser()

    if not browser:
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            pass
        finally:
            server.shutdown()
            shutil.rmtree(udd, ignore_errors=True)
        os._exit(0)

    flags = load_custom_flags()
    if "firefox" in browser:
        cmd = [browser, url]
    else:
        cmd = [
            browser,
            f"--app={url}",
            f"--user-data-dir={udd}",
        ] + flags

    kw = (
        {}
        if SHOW_BROWSER_LOGS
        else {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    )
    try:
        subprocess.run(cmd, **kw)
    finally:
        server.shutdown()
        shutil.rmtree(udd, ignore_errors=True)
    os._exit(0)


def _cli() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from providers.zlib import Provider

    keyword = " ".join(sys.argv[1:]) or "安妮的日記"
    p = Provider()
    print("login…", p.login())
    cards = p.search(keyword, limit=8)
    if not cards:
        print("No results.")
        sys.exit(1)
    card = next(
        (c for c in cards if (c.get("extension") or "").lower() == "epub"), cards[0]
    )
    print("card", card["name"])
    sections = p.get_sections(card)
    print("sections", len(sections))
    launch_reader(p, card, sections, start_index=0)


if __name__ == "__main__":
    _cli()
