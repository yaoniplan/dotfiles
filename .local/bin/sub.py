#!/usr/bin/env python3

import os
import sys
import subprocess
import urllib.parse
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "sing-box"
SUB_API = "https://clash2sfa.xmdhs.com/sub"
EDITOR = os.environ.get("EDITOR", "vim")
CONFIGS_SUBDIR = CONFIG_DIR / "configs"

def url_to_filename(url: str) -> str:
    """Encode URL to a safe filename."""
    encoded = urllib.parse.quote(url, safe='')
    return f"config.{encoded}.json"

def filename_to_url(filename: str) -> str:
    """Decode URL from filename."""
    encoded = filename[len("config."):-len(".json")]
    return urllib.parse.unquote(encoded)

def switch_config(file_path: Path) -> bool:
    """Switch the active config; roll back the symlink if restart fails or the user interrupts"""
    symlink = CONFIG_DIR / "config.json"

    # Record the current symlink target (if it exists)
    previous_target = None
    if symlink.is_symlink():
        try:
            previous_target = os.readlink(symlink)
        except OSError:
            pass

    # Update the symlink
    try:
        if symlink.exists() or symlink.is_symlink():
            symlink.unlink()
        symlink.symlink_to(file_path)
    except OSError as e:
        print(f"Unable to update symlink: {e}", file=sys.stderr)
        return False

    # Try to restart sing-box
    try:
        subprocess.run(["doas", "systemctl", "restart", "sing-box"], check=True)
        print(f"Switched to {file_path.name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Restart failed (exit code {e.returncode}), rolling back config", file=sys.stderr)
    except KeyboardInterrupt:
        # User pressed Ctrl-C
        print("\nOperation interrupted, rolling back config", file=sys.stderr)
    except Exception as e:
        print(f"Unknown error during restart: {e}, rolling back config", file=sys.stderr)

    # Roll back the symlink
    try:
        if symlink.exists() or symlink.is_symlink():
            symlink.unlink()
        if previous_target:
            symlink.symlink_to(previous_target)
            print(f"Rolled back to previous config", file=sys.stderr)
        else:
            print(f"No previous config, symlink removed", file=sys.stderr)
    except OSError as e:
        print(f"Failed to roll back symlink: {e}", file=sys.stderr)
    return False

def create_config(url: str):
    """Download new subscription config and switch to it."""
    filename = url_to_filename(url)
    file_path = CONFIGS_SUBDIR / filename

    if file_path.exists():
        print(f"Already exists: {file_path}", file=sys.stderr)
        return

    result = subprocess.run(
        ["curl", "-LsG", "--data-urlencode", f"sub={url}", SUB_API],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print("Invalid configuration", file=sys.stderr)
        return

    with open(file_path, "w") as f:
        subprocess.run(
            ["jq", "-f", str(CONFIG_DIR / "patch.jq")],
            input=result.stdout, text=True, stdout=f, check=True
        )

    if switch_config(file_path):
        print(f"Downloaded and switched to {file_path.name}")
    else:
        print(f"File saved, but switch failed: {file_path.name}")

def update_config(file_path: Path):
    """Re‑download a config from its extracted URL."""
    url = filename_to_url(file_path.name)
    if not url.startswith(("http://", "https://")):
        print(f"Cannot extract subscription URL from {file_path.name}", file=sys.stderr)
        return

    tmp_path = file_path.with_suffix(".tmp")
    result = subprocess.run(
        ["curl", "-LsG", "--data-urlencode", f"sub={url}", SUB_API],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        if tmp_path.exists():
            tmp_path.unlink()
        print("Invalid configuration", file=sys.stderr)
        return

    with open(tmp_path, "w") as f:
        subprocess.run(
            ["jq", "-f", str(CONFIG_DIR / "patch.jq")],
            input=result.stdout, text=True, stdout=f, check=True
        )

    tmp_path.replace(file_path)
    if switch_config(file_path):
        print(f"Updated and switched to {file_path.name}")
    else:
        print(f"File updated, but switch failed: {file_path.name}")

def delete_config(file_path: Path, configs: list[str]):
    """Delete config. If it's the active one, fallback to neighbor or remove symlink."""
    basename = file_path.name
    symlink = CONFIG_DIR / "config.json"

    # Check if deleting the active config
    is_current = False
    if symlink.is_symlink():
        try:
            target = Path(os.readlink(symlink))
            if not target.is_absolute():
                target = (symlink.parent / target).resolve()
            else:
                target = target.resolve()
            if target == file_path.resolve():
                is_current = True
        except OSError:
            pass

    if is_current:
        idx = configs.index(basename) if basename in configs else -1
        fallback = None
        if idx > 0:
            fallback = CONFIGS_SUBDIR / configs[idx - 1]
        elif idx < len(configs) - 1:
            fallback = CONFIGS_SUBDIR / configs[idx + 1]

        if fallback:
            if not switch_config(fallback):
                print("Failed to switch to fallback config, cancelling deletion", file=sys.stderr)
                return
        else:
            try:
                symlink.unlink()
                print("No other config available, symlink removed")
            except OSError as e:
                print(f"Failed to remove symlink: {e}", file=sys.stderr)
                return

    file_path.unlink()
    print(f"Deleted {basename}")

def edit_config(file_path: Path):
    """Open config in editor."""
    subprocess.run([EDITOR, str(file_path)], check=False)

def run_fzf(configs: list[str], current_basename: str) -> tuple[str, str, str]:
    """Run fzf and return (query, key, selected)."""
    pos = 1
    if current_basename in configs:
        pos = configs.index(current_basename) + 1

    fzf_cmd = [
        "fzf",
        "--phony",
        "--print-query",
        "--expect=ctrl-u,ctrl-d,ctrl-e",
        "--pointer=➤",
        "--reverse",
        "--sync",
        "--height", "~100%",
        "--bind", f"start:pos({pos})",
        "--header", "Enter: switch | Ctrl-U: update | Ctrl-D: delete | Ctrl-E: edit | Type URL to add"
    ]

    proc = subprocess.Popen(
        fzf_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    out, err = proc.communicate("\n".join(configs) + ("\n" if configs else ""))
    if proc.returncode != 0:
        sys.exit(0)

    lines = out.splitlines()
    query = ""
    key = ""
    selected = ""

    if len(lines) >= 1:
        query = lines[0].strip()
    if len(lines) >= 3:
        key = lines[1].strip()
        selected = lines[2].strip()
    elif len(lines) == 2:
        second = lines[1].strip()
        if second in ("ctrl-u", "ctrl-d", "ctrl-e"):
            key = second
        else:
            selected = second

    return query, key, selected

def main():
    os.chdir(CONFIG_DIR)

    # Ensure the subdirectory exists
    CONFIGS_SUBDIR.mkdir(exist_ok=True)

    # List all config files (only new format)
    configs = sorted(p.name for p in CONFIGS_SUBDIR.glob("config.*.json"))

    symlink = CONFIG_DIR / "config.json"
    current_basename = ""
    if symlink.is_symlink():
        try:
            current_basename = Path(os.readlink(symlink)).name
        except OSError:
            pass

    query, key, selected = run_fzf(configs, current_basename)

    if key:
        if not selected:
            print("No selection", file=sys.stderr)
            sys.exit(1)

        file_path = CONFIGS_SUBDIR / selected
        if key == "ctrl-u":
            update_config(file_path)
        elif key == "ctrl-d":
            ans = input(f"Delete {selected}? [y/N] ")
            if ans.lower() in ("y", "yes"):
                delete_config(file_path, configs)
            else:
                print("Cancelled")
        elif key == "ctrl-e":
            edit_config(file_path)
        else:
            print(f"Unknown key: {key}", file=sys.stderr)
            sys.exit(1)

    elif query.startswith(("http://", "https://")):
        create_config(query)
    elif selected:
        switch_config(CONFIGS_SUBDIR / selected)
    else:
        print("Cancelled")

if __name__ == "__main__":
    main()
