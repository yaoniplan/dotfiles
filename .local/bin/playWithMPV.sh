#!/usr/bin/env bash

# Dependencies: mpv, yt-dlp, xsel (Or wl-clipboard)

# Check if Wayland is the display server protocol
if [[ "$XDG_SESSION_TYPE" = "wayland" ]]; then
    mpv --speed=2  --fullscreen --mute=yes $(wl-paste)
else
    mpv --speed=2 --fullscreen --mute=yes $(xsel --output --clipboard)
fi
