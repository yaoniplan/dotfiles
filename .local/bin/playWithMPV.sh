#!/usr/bin/env bash

# Dependencies:
# mpv, xsel

mpv --speed=2 --fullscreen "$(xsel -ob)"
