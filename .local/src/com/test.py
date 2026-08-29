#!/usr/bin/env python3
"""
交互式 Provider 测试器 — 对齐统一契约 + 可复制诊断报告

  search / get_chapters / resolve_read  (+ optional fetch_image)

结束时打印 ===== DIAG REPORT ===== … ===== END REPORT =====
整段复制发给 AI 即可，无需 zip。
"""
from __future__ import annotations

import importlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any


# ── fzf / 编号 ────────────────────────────────────────────────────────
def fzf_available() -> bool:
    return shutil.which("fzf") is not None


def fzf_select(options: list[str], prompt: str = "请选择", multi: bool = False):
    if not options:
        return None
    if not fzf_available():
        return _number_select(options, multi)
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
        selected = [l.strip() for l in out.splitlines() if l.strip()]
        if not selected:
            return None
        return selected if multi else selected[0]
    except Exception:
        return _number_select(options, multi)


def _number_select(options: list[str], multi: bool = False):
    print("\n可选项：")
    for i, opt in enumerate(options):
        print(f"  {i:>2}. {opt}")
    while True:
        if multi:
            sel = input("\n编号（逗号分隔）: ").strip()
            if not sel:
                continue
            try:
                idxs = [int(x.strip()) for x in sel.split(",") if x.strip()]
                if all(0 <= i < len(options) for i in idxs):
                    return [options[i] for i in idxs]
            except ValueError:
                pass
            print("无效")
        else:
            sel = input(f"\n编号 (0-{len(options)-1}): ").strip()
            if sel.isdigit() and 0 <= int(sel) < len(options):
                return options[int(sel)]
            print("无效")


def ask_yes(msg: str, default: bool = True) -> bool:
    hint = "Y/n" if default else "y/N"
    try:
        ans = input(f"{msg} ({hint}): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return default
    if not ans:
        return default
    return ans in ("y", "yes", "1", "是")


# ── 临时文件 / JSON ───────────────────────────────────────────────────
def open_text_in_viewer(text: str, title: str, suffix: str = ".html") -> str | None:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in title)[:40]
    fd, path = tempfile.mkstemp(prefix=f"com_test_{safe}_", suffix=suffix)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text if text.endswith("\n") else text + "\n")
    print(f"\n📄 {path}  ({len(text)} 字符)")
    editors: list[str] = []
    for env in ("VISUAL", "EDITOR"):
        if os.environ.get(env):
            editors.append(os.environ[env])
    for cmd in ("nvim", "vim", "nano", "less", "bat", "code"):
        if shutil.which(cmd.split()[0]) and cmd not in editors:
            editors.append(cmd)
    if not editors:
        print(text[:2000] + ("…" if len(text) > 2000 else ""))
        return path
    labels = [f"{i}: {e}" for i, e in enumerate(editors)] + [f"{len(editors)}: 跳过"]
    sel = fzf_select(labels, prompt="用什么打开")
    if sel is None or sel.startswith(f"{len(editors)}:"):
        return path
    try:
        editor = editors[int(sel.split(":")[0])]
    except (ValueError, IndexError):
        return path
    cmd = [editor, "-R", path] if editor == "less" else editor.split() + [path]
    try:
        subprocess.call(cmd)
    except Exception as e:
        print(f"打开失败: {e}")
    return path


def to_jsonable(obj: Any) -> Any:
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(x) for x in obj]
    return repr(obj)


def dump_json(data: Any, limit: int | None = None) -> str:
    s = json.dumps(to_jsonable(data), ensure_ascii=False, indent=2, default=str)
    if limit and len(s) > limit:
        return s[:limit] + f"\n… [truncated, total {len(s)} chars]"
    return s


def print_structure(label: str, data: Any, preview_limit: int = 2) -> None:
    print(f"\n── {label} 结构 ──")
    if data is None:
        print("  (None)")
        return
    if isinstance(data, list):
        print(f"  type: list  len={len(data)}")
        if not data:
            return
        if isinstance(data[0], dict):
            print(f"  item_keys: {sorted(data[0].keys())}")
        print(f"  前 {min(preview_limit, len(data))} 项:")
        print(dump_json(data[:preview_limit]))
        if len(data) > preview_limit:
            print(f"  ... 另有 {len(data) - preview_limit} 项")
    elif isinstance(data, dict):
        print(f"  type: dict  keys={sorted(data.keys())}")
        print(dump_json(data))
    else:
        print(f"  type: {type(data).__name__}  value={data!r}")


# ── HTTP 日志 ─────────────────────────────────────────────────────────
_ask_open_html = True
_saved_responses: list[dict] = []


def log_request(method, url, headers=None, data=None):
    print(f"\n{'=' * 60}")
    print(f"📤 请求: {method} {url}")
    if headers:
        interesting = {
            k: v
            for k, v in dict(headers).items()
            if k.lower()
            in (
                "user-agent",
                "referer",
                "accept",
                "content-type",
                "cookie",
                "authorization",
                "origin",
            )
        }
        if interesting:
            print(f"   Headers: {json.dumps(interesting, indent=2, ensure_ascii=False)}")
    if data:
        text = data if isinstance(data, str) else repr(data)
        print(f"   Data: {text[:500]}{'…' if len(str(text)) > 500 else ''}")


def log_response(resp, body_preview: int = 1500):
    global _ask_open_html
    status, reason, url = resp.status_code, resp.reason, str(resp.url)
    ctype = resp.headers.get("Content-Type", "")
    body = resp.text or ""
    total = len(body)
    print(f"📥 响应: {status} {reason}")
    print(f"   URL: {url}")
    print(f"   Content-Type: {ctype}")
    print(f"   Body 长度: {total} 字符")
    if total > body_preview:
        print(f"   Body 预览 (前 {body_preview} 字符):\n{body[:body_preview]}")
        print(f"   ... [截断，总长度 {total}]")
    else:
        print(f"   Body:\n{body}")

    _saved_responses.append(
        {
            "method": resp.request.method,
            "url": url,
            "status": status,
            "content_type": ctype,
            "body": body,
            "length": total,
        }
    )

    if total == 0:
        print()
        return
    suffix = ".json" if "json" in ctype.lower() else ".html"
    path_part = url.rstrip("/").split("/")[-1].split("?")[0][:30] or "response"
    if _ask_open_html:
        if ask_yes(f"用编辑器打开本页完整响应 ({total} 字符)？", default=False):
            open_text_in_viewer(body, f"{status}_{path_part}", suffix=suffix)
        if len(_saved_responses) >= 2:
            if not ask_yes("之后的响应还要逐个询问打开吗？", default=True):
                _ask_open_html = False
                print("   (已关闭逐个询问；结束时可再选打开)")
    print()


def attach_session_logger(provider) -> bool:
    session = getattr(provider, "session", None)
    if session is None:
        return False

    def _hook(resp, *args, **kwargs):
        req = resp.request
        log_request(req.method, req.url, headers=req.headers, data=req.body)
        log_response(resp)

    session.hooks.setdefault("response", []).append(_hook)
    return True


def review_saved_responses() -> None:
    if not _saved_responses:
        return
    print(f"\n── 本轮共捕获 {len(_saved_responses)} 次 HTTP 响应 ──")
    if not ask_yes("是否再次打开某次完整响应？", default=False):
        return
    labels = [
        f"{i}: [{e['status']}] {e['url'][:70]}  ({e['length']} chars)"
        for i, e in enumerate(_saved_responses)
    ]
    sel = fzf_select(labels, prompt="选择要打开的响应")
    if sel is None:
        return
    try:
        e = _saved_responses[int(sel.split(":")[0])]
    except (ValueError, IndexError):
        return
    suffix = ".json" if "json" in (e["content_type"] or "").lower() else ".html"
    open_text_in_viewer(e["body"], f"resp_{e['status']}", suffix=suffix)


# ── 诊断报告（结束时整段可复制） ──────────────────────────────────────
class Report:
    def __init__(self, provider: str, keyword: str):
        self.meta = {
            "provider": provider,
            "keyword": keyword,
            "time": datetime.now().isoformat(timespec="seconds"),
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        }
        self.selected: dict = {}
        self.sections: list[str] = []
        self.trace: str | None = None

    def add(self, text: str):
        self.sections.append(text)

    def add_json(self, label: str, data: Any, limit: int = 2000):
        self.sections.append(f"{label}:\n{dump_json(data, limit=limit)}")

    def set_trace(self, tb: str):
        self.trace = tb

    def render(self) -> str:
        out = [
            "===== DIAG REPORT =====",
            f"provider : {self.meta['provider']}",
            f"keyword  : {self.meta['keyword']}",
            f"time     : {self.meta['time']}",
            f"python   : {self.meta['python']}",
            f"platform : {self.meta['platform']}",
            "",
            "selected:",
            dump_json(self.selected),
        ]
        if self.trace:
            out += ["", "TRACEBACK:", self.trace]
        if self.sections:
            out.append("")
            out.extend(self.sections)

        if _saved_responses:
            out.append("\n── HTTP (sample) ──")
            entries = _saved_responses
            if len(entries) <= 5:
                indices = list(range(len(entries)))
            else:
                indices = [0, 1, 2, len(entries) - 2, len(entries) - 1]
            shown = set()
            for idx in indices:
                if idx in shown or idx < 0 or idx >= len(entries):
                    continue
                shown.add(idx)
                h = entries[idx]
                body = h.get("body") or ""
                ctype = h.get("content_type") or ""
                url = h.get("url") or ""
                if "image/" in ctype or "chapterfun.ashx" in url:
                    preview = f"[{h.get('length', 0)} chars omitted]"
                else:
                    preview = body[:800]
                out.append(
                    f"[{idx + 1}] {h.get('method')} {h.get('status')}  {url}\n"
                    f"    Content-Type: {ctype}  len={h.get('length')}\n"
                    f"    preview:\n{preview}"
                )
            omitted = len(entries) - len(shown)
            if omitted > 0:
                out.append(f"  … {omitted} more HTTP calls omitted")

        out.append("\n===== END REPORT =====")
        return "\n".join(out)


# ── 测试步骤（对齐契约） ──────────────────────────────────────────────
def test_search(prov, keyword: str, report: Report):
    print("\n▶️ 步骤1: search()")
    try:
        cards = prov.search(keyword)
        print(f"✅ search 返回 {len(cards)} 个结果")
        if not cards:
            print("❌ 没有结果")
            report.add("search: empty")
            return []
        for idx, c in enumerate(cards):
            print(f"   [{idx}] {c.get('name', '?')} (id: {c.get('id', '?')})")
        print_structure("search 返回列表", cards, preview_limit=2)
        report.add(f"search count: {len(cards)}")
        if cards:
            report.add(f"search item_keys: {sorted(cards[0].keys())}")
        report.add_json("search first 2", cards[:2])
        if ask_yes("用编辑器打开【search JSON】？", default=False):
            open_text_in_viewer(dump_json(cards), f"search_{keyword}", ".json")
        return cards
    except Exception:
        tb = traceback.format_exc()
        report.set_trace(tb)
        print(f"❌ search 异常:\n{tb}")
        return []


def test_chapters(prov, card, report: Report):
    name = card.get("name") or "?"
    print(f"\n▶️ 步骤2: get_chapters()  - 漫画: {name}")
    print_structure("传入的 card", card)
    try:
        chapters = prov.get_chapters(card)
        print(f"✅ get_chapters 返回 {len(chapters)} 个章节")
        if not chapters:
            print("❌ 没有获取到章节")
            report.add("chapters: empty")
            return []
        for idx, ch in enumerate(chapters[:10]):
            print(f"   [{idx}] {ch.get('name', '?')} (id: {ch.get('id', '?')})")
        if len(chapters) > 10:
            print(f"   ... 共 {len(chapters)} 个")
        print_structure("get_chapters 返回列表", chapters, preview_limit=2)
        report.add(f"chapters count: {len(chapters)}")
        if chapters:
            report.add(f"chapters item_keys: {sorted(chapters[0].keys())}")
        report.add_json("chapters first 2", chapters[:2])
        if ask_yes("用编辑器打开【chapters JSON】？", default=False):
            open_text_in_viewer(dump_json(chapters), f"chapters_{name}", ".json")
        return chapters
    except Exception:
        tb = traceback.format_exc()
        report.set_trace(tb)
        print(f"❌ get_chapters 异常:\n{tb}")
        return []


def test_resolve(prov, chap, card, report: Report):
    name = chap.get("name") or "?"
    print(f"\n▶️ 步骤3: resolve_read()  - 章节: {name}")
    print_structure("传入的 chapter", chap)
    try:
        images = prov.resolve_read(chap, comic=card)
        if images:
            print(f"✅ 解析成功，共 {len(images)} 张图片")
            for i, url in enumerate(images[:5]):
                print(f"   [{i}] {url}")
            if len(images) > 5:
                print(f"   ... 共 {len(images)} 张")
        else:
            print("⚠️  未获取到图片列表（空列表）")
        print_structure("resolve_read 返回", images, preview_limit=5)
        report.add(f"images count: {len(images) if images else 0}")
        report.add_json("images first 5", (images or [])[:5])

        if images and hasattr(prov, "fetch_image") and callable(prov.fetch_image):
            if ask_yes("测试 fetch_image（第一张）？", default=False):
                try:
                    data = prov.fetch_image(images[0])
                    info = {
                        "url": images[0],
                        "bytes": len(data),
                        "magic": data[:8].hex(),
                    }
                    report.add_json("fetch_image", info)
                    print(f"✅ fetch_image → {len(data)} bytes  magic={data[:4]!r}")
                except Exception:
                    tb = traceback.format_exc()
                    report.add("fetch_image ERROR:\n" + tb)
                    print(f"❌ fetch_image\n{tb}")

        if ask_yes("用编辑器打开【images JSON】？", default=False):
            open_text_in_viewer(dump_json(images), f"images_{name}", ".json")
        return images
    except Exception:
        tb = traceback.format_exc()
        report.set_trace(tb)
        print(f"❌ resolve_read 异常:\n{tb}")
        return []


# ── main ──────────────────────────────────────────────────────────────
def main():
    global _ask_open_html, _saved_responses
    _ask_open_html = True
    _saved_responses = []

    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root))
    provider_dir = root / "providers"
    if not provider_dir.is_dir():
        print("❌ 找不到 providers/")
        return

    print(f"📁 使用 providers 目录: {provider_dir}")
    modules = sorted(
        f.stem
        for f in provider_dir.glob("*.py")
        if not f.name.startswith("_")
        and f.name != "__init__.py"
        and not f.name.lower().startswith("deprecated")
    )
    if not modules:
        print("❌ 未找到任何 Provider")
        return

    print(f"\n可用的 Provider ({len(modules)} 个):")
    for m in modules:
        print(f"  - {m}")

    selected_mod = fzf_select(modules, prompt="选择 Provider")
    if selected_mod is None:
        print("未选择，退出")
        return
    print(f"\n已选择: {selected_mod}")

    try:
        provider = importlib.import_module(f"providers.{selected_mod}").Provider()
    except Exception:
        print(f"❌ 导入失败:\n{traceback.format_exc()}")
        return

    keyword = input("请输入搜索关键字: ").strip() or "天才"
    if keyword == "天才":
        print(f"使用默认关键字: '{keyword}'")

    report = Report(selected_mod, keyword)

    if ask_yes("启用详细请求/响应日志（可打开完整 HTML）？", default=True):
        if attach_session_logger(provider):
            print("✅ 已挂载 session 日志")
        else:
            print("⚠️  Provider 没有 session，无法拦截 HTTP")

    cards = test_search(provider, keyword, report)
    if not cards:
        print("\n🏁 测试结束（无搜索结果）")
        review_saved_responses()
        print("\n" + report.render())
        return

    card_options = [
        f"{i}: {c.get('name', '?')} (id: {c.get('id', '?')})"
        for i, c in enumerate(cards)
    ]
    sel = fzf_select(card_options, prompt="选择漫画")
    if sel is None:
        review_saved_responses()
        print("\n" + report.render())
        return
    card = cards[int(sel.split(":")[0])]
    print(f"\n✅ 选择漫画: {card.get('name')} (id: {card.get('id')})")
    print_structure("当前选中的 card", card)
    report.selected["comic"] = {"id": card.get("id"), "name": card.get("name")}

    chapters = test_chapters(provider, card, report)
    if not chapters:
        print("\n🏁 测试结束（无章节）")
        review_saved_responses()
        print("\n" + report.render())
        return

    chap_options = [
        f"{i}: {ch.get('name', '?')} (id: {ch.get('id', '?')})"
        for i, ch in enumerate(chapters)
    ]
    sel = fzf_select(chap_options, prompt="选择章节")
    if sel is None:
        review_saved_responses()
        print("\n" + report.render())
        return
    chap = chapters[int(sel.split(":")[0])]
    print(f"\n✅ 选择章节: {chap.get('name')} (id: {chap.get('id')})")
    print_structure("当前选中的 chapter", chap)
    report.selected["chapter"] = {"id": chap.get("id"), "name": chap.get("name")}

    test_resolve(provider, chap, card, report)

    print("\n🏁 测试完成")
    review_saved_responses()
    print("\n" + report.render())


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n(cancelled)")
