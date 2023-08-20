#!/usr/bin/env bash

# Dependencies: notify-send, gtts-cli, mpg123

# Set variables
currentDate=$(date +%x) # 08/20/2023
currentTime=$(date +%H:%M) # 10:03
currentWeekday=$(date +%A) # Sunday

# Check if the first argument is coorsponding string
if [[ "$1"  == "date" ]]; then
    export $(dbus-launch); notify-send "$currentDate" && gtts-cli "$currentDate" | mpg123 -
elif [[ "$1" == "time" ]]; then
    export $(dbus-launch); notify-send "$currentTime" && gtts-cli "$currentTime" | mpg123 -
elif [[ "$1" == "weekday" ]]; then
    export $(dbus-launch); notify-send "$currentWeekday" && gtts-cli "$currentWeekday" | mpg123 -
else
    export $(dbus-launch); notify-send "$currentTime" && gtts-cli "$currentTime" | mpg123 -
fi
