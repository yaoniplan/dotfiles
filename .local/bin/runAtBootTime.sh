#!/usr/bin/env bash

if commmand -v feh &>/dev/null; then
    feh $HOME/note/assets/dark.jpg &>/dev/null &
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

if command -v redshift && ! pgrep redshift; then
    redshift -x; redshift -O 1500 &>/dev/null &
fi

if ! ps aux | grep -v grep | grep aolaStar; then
    mpv --shuffle --loop-playlist /mnt/grow/230601aolaStar/ &>/dev/null &
fi

if ! ps aux | grep -v grep | grep timerOfTomato.sh; then
    timerOfTomato.sh &>/dev/null &
fi
