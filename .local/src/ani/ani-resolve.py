#!/usr/bin/env python3
import sys, json, os, importlib

STATE_FILE = "/tmp/ani_playlist.json"

def find_provider_module(source_name):
    """在 providers/ 下找到 name 匹配 source_name 的模块"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    prov_dir = os.path.join(script_dir, "providers")
    for fname in os.listdir(prov_dir):
        if not fname.endswith(".py") or fname.startswith("__"):
            continue
        mod_name = fname[:-3]
        try:
            mod = importlib.import_module(f"providers.{mod_name}")
            provider = mod.Provider()
            if provider.name == source_name:
                return mod_name, provider
        except Exception:
            continue
    return None, None

def main():
    if len(sys.argv) < 2:
        print("Usage: ani-resolve.py <next|prev|goto:index>", file=sys.stderr)
        sys.exit(1)
    command = sys.argv[1]

    if not os.path.exists(STATE_FILE):
        print("no state file", file=sys.stderr)
        sys.exit(1)

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)

    source = state["source"]
    tracks = state["tracks"]
    current = state["start_index"]
    script_dir = state.get("script_dir", os.path.dirname(os.path.abspath(__file__)))

    if command == "next":
        new_idx = current + 1
    elif command == "prev":
        new_idx = current - 1
    elif command.startswith("goto:"):
        try:
            # 索引为 0-based，直接使用
            new_idx = int(command.split(":")[1])
        except ValueError:
            print("invalid goto", file=sys.stderr)
            sys.exit(1)
    else:
        print("unknown command", file=sys.stderr)
        sys.exit(1)

    if new_idx < 0 or new_idx >= len(tracks):
        print("index out of range", file=sys.stderr)
        sys.exit(1)

    os.chdir(script_dir)
    sys.path.insert(0, script_dir)

    _, provider = find_provider_module(source)
    if provider is None:
        print(f"cannot find provider for source: {source}", file=sys.stderr)
        sys.exit(1)

    track = tracks[new_idx]
    try:
        play_url = provider.resolve_play(track)
    except Exception as e:
        print(f"resolve error: {e}", file=sys.stderr)
        sys.exit(1)

    # 更新状态文件
    state["start_index"] = new_idx
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    # 输出两行：播放地址 + 标题
    title = f"[{source}] {state['title']} / {track['name']}"
    print(play_url)
    print(title)

if __name__ == "__main__":
    main()
