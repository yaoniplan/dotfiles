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

if command -v sct; then
    currentTime=$(date +%H:%M)

    if [[ $currentTime > "22:00" ]] || [[ $currentTime < "07:00" ]]; then
        sct 1500
        echo "Set color temperature to 1500K between 22:00 and 07:00"
    else
        sct
        echo "Reset to the default color temperature"
    fi
fi

if ! ps aux | grep -v grep | grep timerOfTomato.sh; then
    timerOfTomato.sh &>/dev/null &
fi
