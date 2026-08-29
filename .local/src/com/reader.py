import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Callable, Optional
from urllib.parse import parse_qs, urlparse

PRELOAD_MARGIN_PX = 3500
SHOW_BROWSER_LOGS = False

# 内置单页应用 HTML/JS/CSS
READER_HTML = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Com Reader</title>
    <style>
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

        img.comic-img {
            width: 100%;
            display: block;
            margin: 0;
            border: none;
            min-height: 300px;
            background: #000000;
            opacity: 0;
            transition: opacity 0.25s ease-in-out;
        }
        img.comic-img.loaded { opacity: 1; }

        .loading-box {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 2lh 0;
            cursor: pointer;
        }
        .spinner {
            width: 22px;
            height: 22px;
            border: 2.5px solid rgba(255, 255, 255, 0.15);
            border-top-color: #ffffff;
            border-radius: 50%;
            animation: spin 0.7s linear infinite;
        }
        .loading-text {
            margin-top: 12px;
            font-size: 0.85rem;
            color: #ffffff;
            font-weight: 500;
        }
        @keyframes spin { to { transform: rotate(360deg); } }

        .chapter-label-block {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            background: #000000;
            border: none;
            margin: 0;
            user-select: none;
            line-height: 1.5;
            padding-top: 1lh;
            padding-bottom: 1lh;
        }
        .divider-label {
            font-size: 1rem;
            color: #ffffff;
            font-weight: 700;
            line-height: 1.2;
        }
        .divider-title {
            font-size: 1rem;
            font-weight: 700;
            color: #ffffff;
            line-height: 1.2;
            margin-top: 0.25em;
        }

        #sentinel { height: 100px; width: 100%; }
    </style>
</head>
<body>
    <div id="container"></div>
    <div id="sentinel"></div>

    <script>
        let currentAppendIndex = INITIAL_INDEX;
        const targetStartPage = INITIAL_PAGE;
        const totalChapters = TOTAL_CHAPTERS;
        const preloadMargin = PRELOAD_MARGIN_PX;
        const chapterNames = CHAPTER_NAMES;

        const chapterCache = new Map();
        const loadedChapters = new Set();
        let isLoading = false;
        let hasScrolledToTargetPage = false;

        let lastHistoryChapter = -1;
        let lastHistoryPage = -1;

        const container = document.getElementById('container');
        const sentinel = document.getElementById('sentinel');

        const imgObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    if (img.dataset.src) {
                        img.onload = () => img.classList.add('loaded');
                        img.onerror = () => {
                            img.classList.add('loaded');
                            img.style.minHeight = '150px';
                            img.style.border = '2px dashed #ff4444';
                            img.style.display = 'flex';
                            img.style.alignItems = 'center';
                            img.style.justifyContent = 'center';
                            img.alt = '❌ 图片加载失败';
                        };
                        img.src = img.dataset.src;
                        delete img.dataset.src;
                    }
                    imgObserver.unobserve(img);
                }
            });
        }, { rootMargin: `${preloadMargin}px 0px ${preloadMargin}px 0px` });

        const historyObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const cIdx = parseInt(entry.target.dataset.chapterIndex);
                    const pIdx = parseInt(entry.target.dataset.pageIndex);
                    if (!isNaN(cIdx) && !isNaN(pIdx)) {
                        if (cIdx !== lastHistoryChapter || pIdx !== lastHistoryPage) {
                            lastHistoryChapter = cIdx;
                            lastHistoryPage = pIdx;
                            fetch('/api/history', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ index: cIdx, page: pIdx })
                            });
                        }
                    }
                }
            });
        }, { threshold: 0.5 });

        function fetchChapterImages(index) {
            if (chapterCache.has(index)) return chapterCache.get(index);
            const promise = fetch(`/api/chapter?index=${index}`)
                .then(res => res.json())
                .then(data => {
                    if (data.error || !data.images) {
                        chapterCache.delete(index);
                        throw new Error(data.error || 'Fetch failed');
                    }
                    return data;
                })
                .catch(err => {
                    chapterCache.delete(index);
                    throw err;
                });
            chapterCache.set(index, promise);
            return promise;
        }

        async function appendNextChapter() {
            if (isLoading || currentAppendIndex >= totalChapters || loadedChapters.has(currentAppendIndex)) return;
            isLoading = true;

            const indexToLoad = currentAppendIndex;
            const chapterName = chapterNames[indexToLoad] || `第 ${indexToLoad + 1} 章`;

            const headerBlock = document.createElement('div');
            headerBlock.className = 'chapter-label-block';
            headerBlock.innerHTML = `
                <div class="divider-label">Current:</div>
                <div class="divider-title">${chapterName}</div>
            `;
            container.appendChild(headerBlock);

            const loadingEl = document.createElement('div');
            loadingEl.className = 'loading-box';
            loadingEl.innerHTML = '<div class="spinner"></div>';
            container.appendChild(loadingEl);

            try {
                const data = await fetchChapterImages(indexToLoad);
                container.removeChild(loadingEl);
                loadedChapters.add(indexToLoad);

                let targetScrollImg = null;

                data.images.forEach((url, imgIdx) => {
                    const img = document.createElement('img');
                    img.className = 'comic-img';
                    img.dataset.src = `/api/img?url=${encodeURIComponent(url)}`;
                    img.dataset.chapterIndex = indexToLoad;
                    img.dataset.pageIndex = imgIdx;

                    imgObserver.observe(img);
                    historyObserver.observe(img);

                    container.appendChild(img);

                    if (!hasScrolledToTargetPage && indexToLoad === INITIAL_INDEX && imgIdx === targetStartPage) {
                        targetScrollImg = img;
                    }
                });

                const footerBlock = document.createElement('div');
                footerBlock.className = 'chapter-label-block';
                footerBlock.innerHTML = `
                    <div class="divider-label">Finished:</div>
                    <div class="divider-title">${data.chapter_name || chapterName}</div>
                `;
                container.appendChild(footerBlock);

                if (targetScrollImg) {
                    hasScrolledToTargetPage = true;
                    requestAnimationFrame(() => {
                        targetScrollImg.scrollIntoView({ block: 'start' });
                    });
                }

                currentAppendIndex++;

                if (currentAppendIndex < totalChapters) {
                    fetchChapterImages(currentAppendIndex).catch(() => {});
                }

            } catch (e) {
                loadingEl.innerHTML = '<div class="loading-text">❌ 加载章节失败，点击重新加载</div>';
                loadingEl.onclick = () => {
                    loadingEl.onclick = null;
                    container.removeChild(headerBlock);
                    container.removeChild(loadingEl);
                    isLoading = false;
                    appendNextChapter();
                };
            } finally {
                isLoading = false;
            }
        }

        const sentinelObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    appendNextChapter();
                }
            });
        }, { rootMargin: `${preloadMargin}px 0px ${preloadMargin}px 0px` });

        sentinelObserver.observe(sentinel);
        appendNextChapter();
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


def load_custom_flags() -> list:
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chromium-flags.conf")
    flags = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    flags.append(line)
    return flags


def launch_reader(
    provider,
    card: dict,
    chapters: list,
    start_index: int,
    start_page: int = 0,
    on_history_update: Optional[Callable] = None,
):
    title = card.get("name") or "未知"
    print(f"▶ {title} / {chapters[start_index]['name']} (P.{start_page + 1})")

    try:
        if os.fork() > 0:
            sys.exit(0)
    except OSError:
        sys.exit(1)

    os.setsid()
    devnull = os.open(os.devnull, os.O_RDWR)
    os.dup2(devnull, 0)
    if not SHOW_BROWSER_LOGS:
        os.dup2(devnull, 1)
        os.dup2(devnull, 2)
    os.close(devnull)

    port = get_free_port()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            if self.path == "/":
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                names = [c.get("name", f"第{i+1}话") for i, c in enumerate(chapters)]
                html = (
                    READER_HTML.replace("INITIAL_INDEX", str(start_index))
                    .replace("INITIAL_PAGE", str(start_page))
                    .replace("TOTAL_CHAPTERS", str(len(chapters)))
                    .replace("PRELOAD_MARGIN_PX", str(PRELOAD_MARGIN_PX))
                    .replace("CHAPTER_NAMES", json.dumps(names))
                )
                self.wfile.write(html.encode())
                return

            if self.path.startswith("/api/chapter"):
                qs = parse_qs(urlparse(self.path).query)
                idx = int(qs.get("index", [start_index])[0])
                data = {}
                if 0 <= idx < len(chapters):
                    chap = chapters[idx]
                    for _ in range(3):
                        try:
                            images = provider.resolve_read(chap, comic=card)
                            data = {"chapter_name": chap["name"], "images": images}
                            break
                        except Exception as e:
                            data = {"error": str(e)}
                            time.sleep(0.5)
                else:
                    data = {"error": "out of range"}
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(data).encode())
                return

            if self.path.startswith("/api/img"):
                qs = parse_qs(urlparse(self.path).query)
                url = qs.get("url", [""])[0]
                if not url:
                    self.send_response(400)
                    self.end_headers()
                    return
                if url.startswith("//"):
                    url = "https:" + url
                try:
                    if hasattr(provider, "fetch_image") and callable(provider.fetch_image):
                        img = provider.fetch_image(url)
                        ctype = "image/jpeg"
                    else:
                        headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                        }
                        if hasattr(provider, "headers"):
                            headers.update(provider.headers)
                        if hasattr(provider, "session"):
                            headers.update(dict(provider.session.headers))
                        headers = {k: v for k, v in headers.items() if k.lower() not in ("host", "accept-encoding")}
                        import requests
                        if hasattr(provider, "session") and isinstance(provider.session, requests.Session):
                            r = provider.session.get(url, headers=headers, timeout=15)
                        else:
                            r = requests.get(url, headers=headers, timeout=15)
                        r.raise_for_status()
                        img = r.content
                        ctype = r.headers.get("Content-Type", "image/jpeg")
                    self.send_response(200)
                    self.send_header("Content-Type", ctype)
                    self.send_header("Cache-Control", "public, max-age=31536000")
                    self.end_headers()
                    self.wfile.write(img)
                except Exception as e:
                    self.send_response(500)
                    self.end_headers()
                return

        def do_POST(self):
            if self.path == "/api/history" and on_history_update:
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                try:
                    on_history_update(body.get("index"), body.get("page", 0))
                except TypeError:
                    on_history_update(body.get("index"))
            self.send_response(200)
            self.end_headers()

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    Thread(target=server.serve_forever, daemon=True).start()

    browser = next(
        (b for b in ("chromium", "chromium-browser", "google-chrome", "brave-browser", "microsoft-edge")
         if subprocess.run(["which", b], capture_output=True).returncode == 0),
        None,
    )
    if not browser:
        sys.exit(1)

    udd = tempfile.mkdtemp(prefix="com_reader_")
    cmd = [browser, f"--app=http://127.0.0.1:{port}", f"--user-data-dir={udd}"] + load_custom_flags()
    kw = {} if SHOW_BROWSER_LOGS else {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    try:
        subprocess.run(cmd, **kw)
    finally:
        server.shutdown()
        shutil.rmtree(udd, ignore_errors=True)
