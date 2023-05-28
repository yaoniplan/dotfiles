#!/usr/bin/env bash

if command -V tilda &>/dev/null && ! pgrep tilda &>/dev/null; then
    tilda --command tmux &>/dev/null &
fi

if command -v redshift &>/dev/null; then
    redshift -O 1500 &>/dev/null &
fi

clash &>/dev/null &
rclone mount yaoniplan:/ /mnt/yaoniplan/ &>/dev/null &
timerOfTomato.sh &>/dev/null &
