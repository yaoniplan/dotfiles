#!/usr/bin/env bash

# Dependencies: mpv, yt-dlp, xsel

if [[ "$#" = 2 ]]; then
    mpv --speed=2 --fullscreen --mute=yes --sub-file="$1" "$2"
else
    mpv --speed=2 --fullscreen --mute=yes $(xsel --output --clipboard)
fi
