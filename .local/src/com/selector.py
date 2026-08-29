import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed


def fzf_select(options, prompt="选择: "):
    if not options:
        proc = subprocess.run(
            ["fzf", "--print-query", "--prompt", prompt, "--height", "~100%", "--reverse"],
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
            timeout=60,
        )
        return proc.stdout.strip() if proc.returncode == 0 else None
    except Exception as e:
        print(f"fzf 错误: {e}")
        return None


def fzf_select_comic_stream(provider_names, load_provider, keyword):
    proc = subprocess.Popen(
        ["fzf", "--prompt", "选择漫画: ", "--height", "100%", "--reverse", "--no-sort"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    line_map = {}

    def search_one(name):
        provider = load_provider(name)
        if not provider:
            return []
        try:
            results = provider.search(keyword)
            for item in results:
                item["_provider"] = provider
                item["_provider_module"] = name
            return results
        except Exception:
            return []

    def feed():
        with ThreadPoolExecutor(max_workers=len(provider_names)) as pool:
            futures = [pool.submit(search_one, n) for n in provider_names]
            for future in as_completed(futures):
                for card in future.result():
                    p = card["_provider"]
                    title = card.get("name") or "未知"
                    remark = (card.get("remark") or "").strip()
                    line = f"[{p.name}] {title}" + (f" | {remark}" if remark else "")
                    line_map[line] = card
                    if proc.poll() is not None:
                        return
                    try:
                        proc.stdin.write(line + "\n")
                        proc.stdin.flush()
                    except Exception:
                        return
        if proc.poll() is None:
            try:
                proc.stdin.close()
            except Exception:
                pass

    threading.Thread(target=feed, daemon=True).start()
    selected = proc.stdout.read().strip()
    proc.wait()
    return line_map.get(selected)
