#!/usr/bin/env python3
"""
交互式 Provider 测试器（支持选择搜索结果）
使用 fzf 快速选择，无 fzf 时自动回退到数字输入。
"""

import importlib
import json
import sys
import traceback
import subprocess
import shutil
from pathlib import Path

# ------------------------------------------------------------
# 辅助：使用 fzf 进行选择（如果可用），否则回退到原始输入
# ------------------------------------------------------------
def fzf_available():
    return shutil.which("fzf") is not None

def fzf_select(options, prompt="请选择", multi=False):
    """使用 fzf 从 options 中选择一项或多项。返回选中项（或列表），取消时返回 None。"""
    if not options:
        return None

    if not fzf_available():
        # 回退到编号输入
        print("\n可选项：")
        for i, opt in enumerate(options):
            print(f"  {i:>2}. {opt}")
        while True:
            if multi:
                sel = input(f"\n请选择编号（多个用逗号分隔，例如 0,2）: ").strip()
                if not sel:
                    continue
                try:
                    indices = [int(x.strip()) for x in sel.split(",") if x.strip()]
                    if all(0 <= i < len(options) for i in indices):
                        return [options[i] for i in indices]
                except ValueError:
                    pass
                print("输入无效，请重试")
            else:
                sel = input(f"\n请选择编号 (0-{len(options)-1}): ").strip()
                if sel.isdigit():
                    idx = int(sel)
                    if 0 <= idx < len(options):
                        return options[idx]
                print("输入无效，请重试")
        return None

    # 使用 fzf
    cmd = ["fzf", "--prompt", f"{prompt}: ", "--height", "40%", "--border"]
    if multi:
        cmd.append("--multi")
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        out, _ = proc.communicate("\n".join(options))
        if proc.returncode != 0:
            return None
        selected = [line.strip() for line in out.splitlines() if line.strip()]
        if not selected:
            return None
        if multi:
            return selected
        return selected[0]
    except Exception:
        # fzf 执行失败，回退到编号输入
        return fzf_select(options, prompt, multi)  # 递归但不会再进 fzf 分支

# ------------------------------------------------------------
def log_request(method, url, headers=None, params=None, data=None):
    print(f"\n{'='*60}")
    print(f"📤 请求: {method} {url}")
    if params:
        print(f"   Params: {params}")
    if headers:
        print(f"   Headers: {json.dumps(dict(headers), indent=2, ensure_ascii=False)}")
    if data:
        print(f"   Data: {data}")

def log_response(resp):
    print(f"📥 响应: {resp.status_code} {resp.reason}")
    print(f"   URL: {resp.url}")
    content_type = resp.headers.get("Content-Type", "")
    print(f"   Content-Type: {content_type}")
    body = resp.text
    if len(body) > 2000:
        body = body[:2000] + f"\n... [截断，总长度 {len(body)}]"
    print(f"   Body:\n{body}\n")

def test_search(prov, keyword, verbose):
    print("\n▶️ 步骤1: search()")
    try:
        cards = prov.search(keyword)
        print(f"✅ search 返回 {len(cards)} 个结果")
        if cards:
            for idx, c in enumerate(cards):
                print(f"   [{idx}] {c.get('vod_name','?')} (vod_id: {c.get('vod_id','?')})")
        else:
            print("❌ 没有结果")
        return cards
    except Exception:
        print(f"❌ search 异常:\n{traceback.format_exc()}")
        return []

def test_tracks(prov, card):
    print(f"\n▶️ 步骤2: get_tracks()  - 专辑: {card.get('vod_name')}")
    try:
        tracks = prov.get_tracks(card)
        print(f"✅ get_tracks 返回 {len(tracks)} 个音轨")
        if tracks:
            for idx, t in enumerate(tracks[:3]):
                print(f"   [{idx}] {t.get('name','?')} (url: {t.get('url','?')})")
            if len(tracks) > 3:
                print(f"   ... 共 {len(tracks)} 个")
        else:
            print("❌ 没有获取到音轨")
        return tracks
    except Exception:
        print(f"❌ get_tracks 异常:\n{traceback.format_exc()}")
        return []

def test_resolve(prov, track):
    print(f"\n▶️ 步骤3: resolve_play()  - 音轨: {track.get('name')}")
    try:
        url = prov.resolve_play(track)
        if url:
            print(f"✅ 播放地址: {url}")
        else:
            print("⚠️  未获取到播放地址")
        return url
    except Exception:
        print(f"❌ resolve_play 异常:\n{traceback.format_exc()}")
        return ""

# ------------------------------------------------------------
def main():
    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root))  # 使 import 能找到根目录

    provider_dir = root / "providers"
    if not provider_dir.is_dir():
        print("❌ 找不到 providers/ 目录（请确认脚本位于项目根目录）")
        return
    print(f"📁 使用 providers 目录: {provider_dir}")

    # 列出所有 Provider 模块文件名（不含扩展名）
    modules = []
    for f in provider_dir.glob("*.py"):
        if f.name.startswith("_") or f.name == "__init__.py":
            continue
        modules.append(f.stem)  # 只有文件名，如 "cyc"
    if not modules:
        print("❌ 未找到任何 Provider 模块")
        return

    print(f"\n可用的 Provider ({len(modules)} 个):")
    for mod in modules:
        print(f"  - {mod}")

    # 使用 fzf 选择 provider（模块名）
    selected_mod = fzf_select(modules, prompt="选择 Provider")
    if selected_mod is None:
        print("未选择，退出")
        return

    print(f"\n已选择: {selected_mod}")

    # 导入选中的 Provider
    try:
        # 因为 providers 不在 sys.path 中，需要从 providers.xxx 导入？
        # 但模块名只是 "cyc"，而实际模块是 providers.cyc，所以需要加上前缀
        module = importlib.import_module(f"providers.{selected_mod}")
        provider = module.Provider()
    except Exception as e:
        print(f"❌ 导入失败:\n{traceback.format_exc()}")
        return

    keyword = input("请输入搜索关键字: ").strip()
    if not keyword:
        keyword = "修仙"
        print(f"未输入关键字，使用默认: '{keyword}'")

    verbose = input("\n启用详细请求/响应日志？(y/n, 默认 y): ").strip().lower() != "n"

    if verbose and hasattr(provider, "session"):
        def print_response(resp, *args, **kwargs):
            log_request(resp.request.method, resp.request.url,
                        headers=resp.request.headers,
                        params=resp.request.params if hasattr(resp.request, "params") else None,
                        data=resp.request.body)
            log_response(resp)
        provider.session.hooks["response"].append(print_response)
    elif verbose:
        print("⚠️  Provider 没有 session 对象，无法拦截详细日志。")

    # 搜索
    cards = test_search(provider, keyword, verbose)
    if not cards:
        print("\n🏁 测试结束（无搜索结果）")
        return

    # 选择专辑
    card_options = [f"{idx}: {c.get('vod_name','?')} (vod_id: {c.get('vod_id','?')})" for idx, c in enumerate(cards)]
    selected_card_str = fzf_select(card_options, prompt="选择专辑")
    if selected_card_str is None:
        print("未选择专辑，退出")
        return
    try:
        sel_idx = int(selected_card_str.split(":")[0])
    except (ValueError, IndexError):
        print("无法解析选择，退出")
        return
    selected_card = cards[sel_idx]
    print(f"\n✅ 选择专辑: {selected_card['vod_name']} (vod_id: {selected_card['vod_id']})")

    # 获取音轨
    tracks = test_tracks(provider, selected_card)
    if not tracks:
        print("\n🏁 测试结束（无音轨）")
        return

    # 选择音轨
    track_options = [f"{idx}: {t.get('name','?')} (url: {t.get('url','?')})" for idx, t in enumerate(tracks)]
    selected_track_str = fzf_select(track_options, prompt="选择音轨")
    if selected_track_str is None:
        print("未选择音轨，退出")
        return
    try:
        track_idx = int(selected_track_str.split(":")[0])
    except (ValueError, IndexError):
        print("无法解析选择，退出")
        return
    selected_track = tracks[track_idx]
    print(f"\n✅ 选择音轨: {selected_track['name']} (url: {selected_track['url']})")

    # 解析播放地址
    test_resolve(provider, selected_track)
    print("\n🏁 测试完成")

if __name__ == "__main__":
    main()
