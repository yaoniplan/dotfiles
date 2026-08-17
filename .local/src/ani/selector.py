#!/usr/bin/env python3

import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed


def fzf_input(prompt="輸入: "):
    """利用 fzf 作為單行文字輸入框，回傳使用者輸入的字串"""
    try:
        proc = subprocess.run(
            ["fzf", "--print-query", "--prompt", prompt, "--height", "~100%", "--reverse"],
            input="",                # 沒有候選清單，只當輸入框
            text=True,
            stdout=subprocess.PIPE,
            timeout=60,
        )

        # fzf 在沒有項目時，按 Enter 會回傳 1，但仍會透過 --print-query 印出 query
        if proc.returncode in (0, 1):
            # 取出第一行（query），可能為空
            query = proc.stdout.split('\n', 1)[0].strip()
            return query if query else None

        # 其他回傳碼（例如 130 表示使用者按 Esc 或 Ctrl-C）視為取消
        return None

    except subprocess.TimeoutExpired:
        print("❌ 輸入超時")
        return None
    except FileNotFoundError:
        print("找不到 fzf 工具")
        sys.exit(1)
    except Exception as e:
        print(f"fzf 錯誤: {e}")
        return None


def fzf_select(options, prompt="選擇: "):
    if not options:
        return None

    try:
        proc = subprocess.run(
            ["fzf", "--prompt", prompt, "--height", "100%", "--reverse"],
            input="\n".join(options),
            text=True,
            stdout=subprocess.PIPE,
            timeout=60,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
        return None

    except subprocess.TimeoutExpired:
        print("❌ 選擇器超時")
        return None
    except FileNotFoundError:
        print("找不到 fzf 工具")
        sys.exit(1)
    except Exception as e:
        print(f"fzf 錯誤: {e}")
        return None


def fzf_multi_select(options, prompt="選擇: "):
    if not options:
        return []

    try:
        proc = subprocess.run(
            ["fzf", "--multi", "--prompt", prompt, "--height", "100%", "--reverse"],
            input="\n".join(options),
            text=True,
            stdout=subprocess.PIPE,
            timeout=60,
        )
        if proc.returncode == 0:
            return [line.strip() for line in proc.stdout.splitlines() if line.strip()]
        return []

    except subprocess.TimeoutExpired:
        print("❌ 選擇器超時")
        return []
    except FileNotFoundError:
        print("找不到 fzf 工具")
        sys.exit(1)
    except Exception as e:
        print(f"fzf 錯誤: {e}")
        return []


def fzf_select_movie_stream(provider_names, load_provider, keyword):
    """背景載入 provider 並搜尋，同時將結果串流給 fzf"""

    try:
        proc = subprocess.Popen(
            ["fzf", "--prompt", "選擇影片: ", "--height", "100%", "--reverse"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
    except FileNotFoundError:
        print("找不到 fzf 工具")
        sys.exit(1)

    line_map = {}
    got_result = False

    def search_one(name):
        provider = load_provider(name)
        if provider is None:
            return []

        try:
            results = provider.search(keyword)
            for item in results:
                item["_provider"] = provider
            return results
        except Exception as e:
            print(f"[{provider.name}] 搜尋錯誤: {e}")
            return []

    def feed_results():
        nonlocal got_result
        with ThreadPoolExecutor(max_workers=len(provider_names)) as pool:
            futures = [pool.submit(search_one, name) for name in provider_names]

            for future in as_completed(futures):
                cards = future.result()

                for card in cards:
                    got_result = True
                    provider = card["_provider"]
                    title = card.get("vod_name", "未知")
                    remark = card.get("vod_remarks", "")

                    line = f"[{provider.name}] {title}"
                    if remark:
                        line += f" | {remark}"

                    line_map[line] = card

                    # 如果 fzf 已經結束，就停止寫入
                    if proc.poll() is not None:
                        return
                    try:
                        proc.stdin.write(line + "\n")
                        proc.stdin.flush()
                    except Exception:
                        return

        if proc and proc.poll() is None:
            try:
                proc.stdin.close()
            except Exception:
                pass

    # 啟動背景執行緒負責搜尋與寫入
    feeder = threading.Thread(target=feed_results)
    feeder.start()

    # 主執行緒直接讀取 fzf 的選擇，使用者一按 Enter 就會返回
    selected = proc.stdout.read().strip()
    proc.wait()

    # 可選：給背景執行緒一點時間清理，但不阻塞
    # feeder.join(timeout=1)

    if not selected:
        return None

    return line_map.get(selected)
