"""Fast file download: aria2c when helpful, requests otherwise."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import requests

ARIA2_CONNECTIONS = int(os.environ.get("PUB_ARIA2_X", "16"))
ARIA2_SPLITS = int(os.environ.get("PUB_ARIA2_S", "16"))
ARIA2_TIMEOUT = int(os.environ.get("PUB_ARIA2_TIMEOUT", "120"))
FORCE_REQUESTS = os.environ.get("PUB_FORCE_REQUESTS", "").lower() in ("1", "true", "yes")


def has_aria2c() -> bool:
    return shutil.which("aria2c") is not None


def _same_host_referer(url: str) -> str:
    p = urlparse(url)
    if p.scheme and p.netloc:
        return f"{p.scheme}://{p.netloc}/"
    return ""


def _prefer_single_conn(url: str) -> bool:
    u = url.lower()
    return any(
        x in u
        for x in ("get.php", "ads.php", "file.php", "libgen.", "library.lol")
    )


def download_file(
    url: str,
    dest: Path,
    *,
    headers: dict[str, str] | None = None,
    session: requests.Session | None = None,
    min_bytes: int = 10_000,
) -> Path:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    if part.exists():
        part.unlink(missing_ok=True)

    headers = dict(headers or {})
    if "Referer" not in headers and "referer" not in headers:
        ref = _same_host_referer(url)
        if ref:
            headers["Referer"] = ref
    if "User-Agent" not in headers and "user-agent" not in headers:
        headers["User-Agent"] = (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        )

    last_err: Exception | None = None
    use_aria = has_aria2c() and not FORCE_REQUESTS
    single = _prefer_single_conn(url)
    order = ("requests", "aria2") if single else ("aria2", "requests")
    if not use_aria:
        order = ("requests",)

    for method in order:
        try:
            if method == "aria2":
                _aria2_download(url, part, headers=headers, single=single)
            else:
                _requests_download(url, part, headers=headers, session=session)
            if not part.is_file() or part.stat().st_size < min_bytes:
                raise RuntimeError(
                    f"{method} small/empty ({part.stat().st_size if part.is_file() else 0})"
                )
            head = part.read_bytes()[:16]
            if head.lstrip().startswith(b"<"):
                raise RuntimeError("got HTML instead of file")
            part.replace(dest)
            return dest
        except Exception as e:
            last_err = e
            part.unlink(missing_ok=True)

    raise RuntimeError(f"download failed: {last_err}")


def _aria2_download(
    url: str, part: Path, *, headers: dict[str, str], single: bool = False
) -> None:
    x = 1 if single else ARIA2_CONNECTIONS
    s = 1 if single else ARIA2_SPLITS
    cmd = [
        "aria2c",
        "--allow-overwrite=true",
        "--auto-file-renaming=false",
        "--console-log-level=warn",
        "--summary-interval=0",
        "--file-allocation=none",
        f"--max-connection-per-server={x}",
        f"--split={s}",
        "--min-split-size=1M",
        f"--timeout={ARIA2_TIMEOUT}",
        "--connect-timeout=15",
        "--max-tries=2",
        "--retry-wait=1",
        "-d", str(part.parent),
        "-o", part.name,
    ]
    ua = headers.get("User-Agent") or headers.get("user-agent")
    if ua:
        cmd += [f"--user-agent={ua}"]
    referer = headers.get("Referer") or headers.get("referer")
    if referer:
        cmd += [f"--referer={referer}"]
    for k, v in headers.items():
        if k.lower() in ("user-agent", "referer"):
            continue
        cmd += [f"--header={k}: {v}"]
    cmd.append(url)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=ARIA2_TIMEOUT + 30)
    if r.returncode != 0 or not part.is_file():
        err = (r.stderr or r.stdout or "").strip()[:400]
        raise RuntimeError(err or f"aria2c exit {r.returncode}")


def _requests_download(
    url: str,
    part: Path,
    *,
    headers: dict[str, str],
    session: requests.Session | None,
) -> None:
    sess = session or requests.Session()
    with sess.get(
        url, stream=True, timeout=(12, 120), allow_redirects=True, headers=headers or None
    ) as r:
        r.raise_for_status()
        with open(part, "wb") as f:
            for chunk in r.iter_content(256 * 1024):
                if chunk:
                    f.write(chunk)
