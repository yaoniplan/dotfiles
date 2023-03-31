#!/usr/bin/env bash

# Check if the clipboard is empty or not
URLOfVideo=$(xclip -o)
if [ -z "$URLOfVideo" ]
then
    echo "Error: No text found in clipboard"
    exit 1
fi

# Play video with mpv
mpv --speed=2 --fs=yes $(xclip -o)
