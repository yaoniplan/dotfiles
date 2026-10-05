"""fzf helpers for pub — keyword input + concurrent provider search stream."""

from __future__ import annotations

import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed, Future


def fzf_select(options, prompt="选择: "):
    """Select one line from options, or free-text query when options is empty."""
    if not options:
        proc = subprocess.run(
            [
                "fzf",
                "--print-query",
                "--prompt",
                prompt,
                "--height",
                "~100%",
                "--reverse",
            ],
            input="",
            text=True,
            stdout=subprocess.PIPE,
        )
        return proc.stdout.split("\n", 1)[0].strip() or None
    try:
        proc = subprocess.run(
            ["fzf", "--prompt", prompt, "--height", "~100%", "--reverse"],
            input="\n".join(options),
            text=True,
            stdout=subprocess.PIPE,
            timeout=120,
        )
        return proc.stdout.strip() if proc.returncode == 0 else None
    except Exception as e:
        print(f"fzf 错误: {e}")
        return None


def fzf_select_book_stream(provider_names, load_provider, keyword):
    """Search all providers concurrently and stream results into fzf.

    As soon as the user accepts a row, remaining searches are cancelled and
    fzf stdin is closed so the TUI can leave immediately.
    """
    proc = subprocess.Popen(
        [
            "fzf",
            "--prompt",
            "选择出版物: ",
            "--height",
            "100%",
            "--reverse",
            "--no-sort",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    line_map: dict[str, dict] = {}
    stop = threading.Event()
    futures: list[Future] = []
    lock = threading.Lock()

    def search_one(name: str) -> list[dict]:
        if stop.is_set():
            return []
        provider = load_provider(name)
        if stop.is_set() or not provider:
            return []
        try:
            results = provider.search(keyword)
        except Exception:
            return []
        if stop.is_set():
            return []
        for item in results:
            item["_provider"] = provider
            item["_provider_module"] = name
        return results

    def feed():
        try:
            workers = max(1, len(provider_names))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                for n in provider_names:
                    futures.append(pool.submit(search_one, n))
                for future in as_completed(futures):
                    if stop.is_set():
                        break
                    try:
                        cards = future.result()
                    except Exception:
                        continue
                    for card in cards:
                        if stop.is_set():
                            return
                        p = card["_provider"]
                        title = card.get("name") or "未知"
                        author = (card.get("author") or "").strip()
                        remark = (card.get("remark") or "").strip()
                        extra = remark or author
                        line = f"[{p.name}] {title}" + (f" | {extra}" if extra else "")
                        with lock:
                            if line in line_map:
                                line = f"{line}  #{card.get('id', '')}"
                            line_map[line] = card
                        try:
                            if proc.stdin and not proc.stdin.closed:
                                proc.stdin.write(line + "\n")
                                proc.stdin.flush()
                        except Exception:
                            stop.set()
                            return
        finally:
            # If user already quit fzf, stdin may already be closed by main thread
            try:
                if proc.stdin and not proc.stdin.closed:
                    proc.stdin.close()
            except Exception:
                pass

    def watch_fzf_exit():
        """When fzf exits (user selected or ESC), stop searches immediately."""
        try:
            proc.wait()
        except Exception:
            pass
        stop.set()
        for f in futures:
            f.cancel()
        try:
            if proc.stdin and not proc.stdin.closed:
                proc.stdin.close()
        except Exception:
            pass

    threading.Thread(target=feed, daemon=True).start()
    threading.Thread(target=watch_fzf_exit, daemon=True).start()

    selected = ""
    try:
        if proc.stdout:
            selected = proc.stdout.read().strip()
    except Exception:
        selected = ""
    stop.set()
    for f in futures:
        f.cancel()
    try:
        if proc.stdin and not proc.stdin.closed:
            proc.stdin.close()
    except Exception:
        pass
    try:
        proc.wait(timeout=0.5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass

    return line_map.get(selected)


def fzf_select_sections_stream(provider, card):
    """fzf opens first; each section line is written as soon as it is known."""
    proc = subprocess.Popen(
        [
            "fzf",
            "--prompt",
            "选择起始章节: ",
            "--height",
            "100%",
            "--reverse",
            "--no-sort",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    line_map: dict[str, int] = {}
    sections: list[dict] = []
    err: Exception | None = None
    stop = threading.Event()

    def feed():
        nonlocal err
        try:
            it = getattr(provider, "iter_sections", None)
            stream = it(card) if callable(it) else iter(provider.get_sections(card))
            for s in stream:
                if stop.is_set() or proc.poll() is not None:
                    return
                sections.append(s)
                i = s.get("index", len(sections) - 1)
                name = s.get("name") or "§"
                line = f"{i + 1:3d}  {name}"
                if line in line_map:
                    line = f"{line}  #{i}"
                line_map[line] = int(i)
                try:
                    if proc.stdin and not proc.stdin.closed:
                        proc.stdin.write(line + "\n")
                        proc.stdin.flush()
                except Exception:
                    return
        except Exception as e:
            err = e
            try:
                if proc.poll() is None and proc.stdin and not proc.stdin.closed:
                    proc.stdin.write(f"！获取目录失败: {e}\n")
                    proc.stdin.flush()
            except Exception:
                pass
        finally:
            try:
                if proc.stdin and not proc.stdin.closed:
                    proc.stdin.close()
            except Exception:
                pass

    def watch_fzf_exit():
        try:
            proc.wait()
        except Exception:
            pass
        stop.set()
        try:
            if proc.stdin and not proc.stdin.closed:
                proc.stdin.close()
        except Exception:
            pass

    threading.Thread(target=feed, daemon=True).start()
    threading.Thread(target=watch_fzf_exit, daemon=True).start()

    selected = ""
    try:
        if proc.stdout:
            selected = proc.stdout.read().strip()
    except Exception:
        selected = ""
    stop.set()
    try:
        if proc.stdin and not proc.stdin.closed:
            proc.stdin.close()
    except Exception:
        pass
    try:
        proc.wait(timeout=0.5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass

    if err and not sections:
        print(f"get_sections 失败: {err}")
        return None, None
    if not selected or not sections:
        return None, None
    if selected.startswith("！"):
        return None, None
    if selected in line_map:
        return sections, line_map[selected]
    try:
        start_index = int(selected.strip().split(None, 1)[0]) - 1
    except (ValueError, IndexError):
        start_index = 0
    start_index = max(0, min(start_index, len(sections) - 1))
    return sections, start_index
