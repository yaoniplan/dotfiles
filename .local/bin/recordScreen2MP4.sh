#!/usr/bin/env bash

# Dependencies: ffmpeg, date, xdpyinfo, grep, awk, pgrep, kill

# Set variables
setFileName=$(date +%F_%H-%M)
setFrameRate="60"
getScreenResolution=$(xdpyinfo | grep dimensions | awk '{print $2}')
getPIDOfFfmpegProcess=$(pgrep -f "ffmpeg -f x11grab")

# Check if the PID of ffmpeg process is not empty
if [[ -n "$getPIDOfFfmpegProcess" ]]; then
    # Stop recording
    kill "$getPIDOfFfmpegProcess"
else
    # Use ffmpeg to record screen
    ffmpeg -f x11grab -video_size "$getScreenResolution" -framerate "$setFrameRate" -i :0.0 -c:v libx264 "$setFileName".mp4
fi
