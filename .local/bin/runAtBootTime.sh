#!/usr/bin/env bash

if command -v feh &>/dev/null; then
    feh --bg-fill $HOME/note/assets/dark.jpg
fi

if command -v tilda &>/dev/null && ! pgrep tilda; then
    tilda --command tmux &>/dev/null &
fi

if command -v clash && ! pgrep clash; then
    clash &>/dev/null &
fi

if command -v rclone && ! pgrep rclone; then
    rclone mount yaoniplan:/ /mnt/yaoniplan --header "Referer:" &>/dev/null &
fi

if command -v sct ; then
    sct 1500
fi

if ! ps aux | grep -v grep | grep aolaStar; then
    mpv --shuffle --loop-playlist /mnt/grow/230601aolaStar/ &>/dev/null &
fi

if ! ps aux | grep -v grep | grep timerOfTomato.sh; then
    timerOfTomato.sh &>/dev/null &
fi
