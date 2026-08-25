import json
import os
import shlex
import subprocess
import tempfile


def play_single(
    source_name: str,
    anime_title: str,
    tracks: list,
    start_index: int,
    play_url: str,
    preferred_player: str | None = None,
):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_mpv_conf = os.path.join(script_dir, "mpv.conf")

    # 生成播放列表
    playlist_path = os.path.join(tempfile.gettempdir(), "ani_playlist.m3u")
    with open(playlist_path, "w", encoding="utf-8") as f:
        for i, track in enumerate(tracks):
            if i == start_index:
                f.write(play_url + "\n")                     # 当前集真实链接
            else:
                f.write(f"ani-playlist://{source_name}/{i}\n")  # 占位协议

    # 写入状态 JSON（供 ani-resolve.py 使用）
    state = {
        "source": source_name,
        "title": anime_title,
        "start_index": start_index,
        "tracks": tracks,
    }
    state["script_dir"] = script_dir
    state_file = os.path.join(tempfile.gettempdir(), "ani_playlist.json")
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    # 构建播放器命令
    if preferred_player:
        player_cmd = preferred_player.split()
    else:
        player_cmd = os.environ.get("ANI_PLAYER", "mpv").split()

    if os.path.isfile(local_mpv_conf):
        player_cmd.append(f"--include={local_mpv_conf}")

    # 修正：--playlist 必须用等号
    player_cmd.append(f"--playlist={playlist_path}")
    player_cmd.append(f"--playlist-start={start_index}")
    current_ep = tracks[start_index]["name"]
    media_title = f"[{source_name}] {anime_title} - {current_ep}"
    player_cmd.append(f"--force-media-title={media_title}")

    print(f"▶ 正在播放: {media_title}")
    subprocess.Popen(
        player_cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    print("播放器已啟動。")
