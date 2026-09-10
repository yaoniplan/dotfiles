"""Local HTTP novel reader — minimal waterfall (faloo-inspired, plugin-ready)."""

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

PRELOAD_MARGIN_PX = 2800
SHOW_BROWSER_LOGS = False

# 极简：无顶栏 / 无进度 / 无章末装饰；标题即分隔；跟随系统日夜
READER_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <title>Nov</title>
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
            /* iPhone 系统无衬线 */
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display",
                         "PingFang SC", "Hiragino Sans GB", "Helvetica Neue",
                         "Microsoft YaHei", system-ui, sans-serif;
            -webkit-font-smoothing: antialiased;
            -webkit-text-size-adjust: 100%;
            scroll-behavior: auto !important;
            min-height: 100vh;
            font-size: 18px;
            line-height: 1.7;
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
            padding: 1.25rem 1.1rem 4rem;
        }

        /* 章节：标题 + 正文，标题本身充当分隔 */
        .chapter {
            padding: 1.75rem 0 0.5rem;
        }
        .chapter:first-child {
            padding-top: 0.5rem;
        }

        .chapter-title {
            font-size: 1.2rem;
            font-weight: 600;
            color: var(--fg);
            line-height: 1.4;
            text-align: center;
            margin: 0 0 1.5rem;
            letter-spacing: 0.02em;
        }

        .chapter-body p {
            text-indent: 2em;
            text-align: justify;
            word-break: break-word;
            /* 约 2 倍字号的段间距（舒适，接近飞卢「3倍」观感） */
            margin: 0 0 2em;
        }
        .chapter-body p:last-child {
            margin-bottom: 0;
        }

        .loading-box {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 2.5rem 0;
            cursor: pointer;
            color: var(--muted);
            font-size: 0.85rem;
        }
        .spinner {
            width: 18px;
            height: 18px;
            border: 2px solid color-mix(in srgb, var(--muted) 35%, transparent);
            border-top-color: var(--muted);
            border-radius: 50%;
            animation: spin 0.65s linear infinite;
            margin-bottom: 0.65rem;
        }
        @keyframes spin { to { transform: rotate(360deg); } }

        #sentinel {
            height: 120px;
            width: 100%;
        }

        .all-done {
            text-align: center;
            padding: 2.5rem 1rem 3rem;
            color: var(--muted);
            font-size: 0.85rem;
        }
    </style>
</head>
<body>
    <div id="container"></div>
    <div id="sentinel"></div>

    <script>
        const INITIAL_INDEX = __INITIAL_INDEX__;
        const TOTAL_CHAPTERS = __TOTAL_CHAPTERS__;
        const PRELOAD_MARGIN = __PRELOAD_MARGIN__;
        const CHAPTER_NAMES = __CHAPTER_NAMES__;
        const BOOK_TITLE = __BOOK_TITLE__;

        let currentAppendIndex = INITIAL_INDEX;
        const chapterCache = new Map();
        const loadedChapters = new Set();
        let isLoading = false;
        let hasScrolledToStart = false;
        let lastHistoryChapter = -1;

        const container = document.getElementById('container');
        const sentinel = document.getElementById('sentinel');

        document.title = (BOOK_TITLE || 'Nov') + ' — 阅读';

        function fetchChapter(index) {
            if (chapterCache.has(index)) return chapterCache.get(index);
            const promise = fetch('/api/chapter?index=' + index)
                .then(res => res.json())
                .then(data => {
                    if (data.error || !Array.isArray(data.paragraphs)) {
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

        const historyObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (!entry.isIntersecting) return;
                const cIdx = parseInt(entry.target.dataset.chapterIndex, 10);
                if (isNaN(cIdx) || cIdx === lastHistoryChapter) return;
                lastHistoryChapter = cIdx;
                fetch('/api/history', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ index: cIdx })
                }).catch(() => {});
            });
        }, { threshold: 0.12 });

        async function appendNextChapter() {
            if (isLoading) return;
            if (currentAppendIndex >= TOTAL_CHAPTERS) {
                if (!document.querySelector('.all-done')) {
                    const done = document.createElement('div');
                    done.className = 'all-done';
                    done.textContent = '— 全部章节已读完 —';
                    container.appendChild(done);
                }
                return;
            }
            if (loadedChapters.has(currentAppendIndex)) return;
            isLoading = true;

            const indexToLoad = currentAppendIndex;
            const chapterName = CHAPTER_NAMES[indexToLoad] || ('第 ' + (indexToLoad + 1) + ' 章');

            const block = document.createElement('div');
            block.className = 'chapter';
            block.dataset.chapterIndex = String(indexToLoad);

            const titleEl = document.createElement('h2');
            titleEl.className = 'chapter-title';
            titleEl.dataset.chapterIndex = String(indexToLoad);
            titleEl.textContent = chapterName;
            block.appendChild(titleEl);
            historyObserver.observe(titleEl);

            const loadingEl = document.createElement('div');
            loadingEl.className = 'loading-box';
            loadingEl.innerHTML = '<div class="spinner"></div><span>加载中…</span>';
            block.appendChild(loadingEl);
            container.appendChild(block);

            try {
                const data = await fetchChapter(indexToLoad);
                block.removeChild(loadingEl);
                loadedChapters.add(indexToLoad);

                const body = document.createElement('div');
                body.className = 'chapter-body';
                body.dataset.chapterIndex = String(indexToLoad);
                const paras = data.paragraphs || [];
                for (let i = 0; i < paras.length; i++) {
                    const p = document.createElement('p');
                    p.textContent = paras[i];
                    body.appendChild(p);
                }
                block.appendChild(body);

                if (!hasScrolledToStart && indexToLoad === INITIAL_INDEX) {
                    hasScrolledToStart = true;
                    requestAnimationFrame(() => {
                        titleEl.scrollIntoView({ block: 'start' });
                    });
                }

                currentAppendIndex++;

                // 瀑布预加载下一章
                if (currentAppendIndex < TOTAL_CHAPTERS) {
                    fetchChapter(currentAppendIndex).catch(() => {});
                }
            } catch (e) {
                loadingEl.innerHTML = '<span>加载失败，点击重试</span>';
                loadingEl.onclick = () => {
                    loadingEl.onclick = null;
                    container.removeChild(block);
                    isLoading = false;
                    appendNextChapter();
                };
            } finally {
                isLoading = false;
            }
        }

        const sentinelObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) appendNextChapter();
            });
        }, { rootMargin: PRELOAD_MARGIN + 'px 0px ' + PRELOAD_MARGIN + 'px 0px' });

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


def _build_html(start_index: int, chapters: list, title: str) -> str:
    names = [c.get("name", f"第{i+1}章") for i, c in enumerate(chapters)]
    return (
        READER_HTML.replace("__INITIAL_INDEX__", str(start_index))
        .replace("__TOTAL_CHAPTERS__", str(len(chapters)))
        .replace("__PRELOAD_MARGIN__", str(PRELOAD_MARGIN_PX))
        .replace("__CHAPTER_NAMES__", json.dumps(names, ensure_ascii=False))
        .replace("__BOOK_TITLE__", json.dumps(title or "未知", ensure_ascii=False))
    )


def launch_reader(
    provider,
    card: dict,
    chapters: list,
    start_index: int,
    on_history_update: Optional[Callable] = None,
):
    title = card.get("name") or "未知"
    print(f"▶ {title} / {chapters[start_index]['name']}")

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
    html_page = _build_html(start_index, chapters, title)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            if self.path == "/" or self.path.startswith("/?"):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(html_page.encode("utf-8"))
                return

            if self.path.startswith("/api/chapter"):
                qs = parse_qs(urlparse(self.path).query)
                try:
                    idx = int(qs.get("index", [start_index])[0])
                except (TypeError, ValueError):
                    idx = start_index
                data: dict = {}
                if 0 <= idx < len(chapters):
                    chap = chapters[idx]
                    for _ in range(3):
                        try:
                            paragraphs = provider.resolve_read(chap, comic=card)
                            data = {
                                "chapter_name": chap.get("name", ""),
                                "paragraphs": paragraphs or [],
                            }
                            break
                        except Exception as e:
                            data = {"error": str(e)}
                            time.sleep(0.4)
                else:
                    data = {"error": "out of range"}
                body = json.dumps(data, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
                return

            self.send_response(404)
            self.end_headers()

        def do_POST(self):
            if self.path == "/api/history" and on_history_update:
                try:
                    length = int(self.headers.get("Content-Length", 0))
                    body = json.loads(self.rfile.read(length) or b"{}")
                    on_history_update(body.get("index"))
                except Exception:
                    pass
            self.send_response(200)
            self.end_headers()

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    Thread(target=server.serve_forever, daemon=True).start()

    browser = next(
        (
            b
            for b in (
                "chromium",
                "chromium-browser",
                "google-chrome",
                "brave-browser",
                "microsoft-edge",
            )
            if subprocess.run(["which", b], capture_output=True).returncode == 0
        ),
        None,
    )
    if not browser:
        sys.exit(1)

    udd = tempfile.mkdtemp(prefix="nov_reader_")
    cmd = [
        browser,
        f"--app=http://127.0.0.1:{port}/",
        f"--user-data-dir={udd}",
    ] + load_custom_flags()
    kw = {} if SHOW_BROWSER_LOGS else {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    try:
        subprocess.run(cmd, **kw)
    finally:
        server.shutdown()
        shutil.rmtree(udd, ignore_errors=True)
