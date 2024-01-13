#!/usr/bin/env bash

# Dependencies: mpv, yt-dlp, xsel

mpv --speed=2 --fullscreen --mute=yes $(xsel --output --clipboard)
