#!/usr/bin/env bash

# Dependencies: command, cat xclip or xsel

if command -v xclip; then
    cat "$@" | xclip -selection clipboard
else
    cat "$@" | xsel --input --clipboard
fi
