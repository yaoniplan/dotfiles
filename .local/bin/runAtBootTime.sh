#!/usr/bin/env bash

if command -v tilda &>/dev/null; then
    tilda --command tmux &>/dev/null &
fi
if command -v redshift &>/dev/null; then
    redshift -O 1500 &>/dev/null &
fi
if command -v yakuake &>/dev/null; then
    yakuake &>/dev/null &
fi

clash &>/dev/null &
rclone mount aliyundrive:/ /mnt/aliyundrive/ &>/dev/null &
timerOfTomato.sh &>/dev/null &
