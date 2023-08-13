#!/usr/bin/env bash

# Dependencies: notify-send, gtts-cli, mpg123

# Set variables
currentDate=$(date +%F)
currentTime=$(date +%H:%M)
currentWeekday=$(date +%A)

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
