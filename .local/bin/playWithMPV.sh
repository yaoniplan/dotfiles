#!/usr/bin/env bash

# Dependencies: mpv, yt-dlp, streamlink, xsel (or wl-clipboard)

# Grab URL from clipboard
if [[ "$XDG_SESSION_TYPE" = "wayland" ]]; then
    URL=$(wl-paste)
else
    URL=$(xsel --output --clipboard)
fi

# If nothing in clipboard, exit
if [[ -z "$URL" ]]; then
    echo "No URL in clipboard"
    exit 1
fi

# Check if URL ends with .m3u8 (case-insensitive)
if [[ "$URL" =~ \.m3u8($|\?) ]]; then
    # HLS stream — use streamlink with thread-based segment fetching
    streamlink --hls-start-offset 5s --stream-segment-threads 4 --player-no-close --player mpv --player-args '--speed=2 --hwdec=auto --hwdec-codecs=all' "$URL" best
elif [[ "$URL" =~ \.html($|\?) ]]; then
    # For my custom yt-dlp extractor yhdm.py
    realUrl=$(yt-dlp --print url "$URL")
    streamlink --hls-start-offset 5s --stream-segment-threads 4 --player-no-close --player mpv --player-args '--speed=2 --hwdec=auto --hwdec-codecs=all' "$realUrl" best
else
    # Normal URL — just play with mpv
    mpv --speed=2 --mute=yes --hwdec=auto --hwdec-codecs=all --ytdl-format='bv*[vcodec^=avc1][height<=720]+ba/b' "$URL"
fi
