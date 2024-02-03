#!/usr/bin/env bash

# Dependencies: notify-send, gtts-cli, mpg123

# Set variables
currentDate=$(date +%x) # e.g. 08/20/2023
currentTime=$(date +%H:%M) # e.g. 10:03
currentWeekday=$(date +%A) # e.g. Sunday

if [[ "$XDG_SESSION_TYPE" = "wayland" ]]; then
    if [[ "$1"  == "date" ]]; then
        notify-send "$currentDate" && gtts-cli "$currentDate" | mpg123 -
    elif [[ "$1" == "time" ]]; then
        notify-send "$currentTime" && gtts-cli "$currentTime" | mpg123 -
    elif [[ "$1" == "weekday" ]]; then
        notify-send "$currentWeekday" && gtts-cli "$currentWeekday" | mpg123 -
    else
        notify-send "$currentTime"; gtts-cli "$currentTime" | mpg123 -
    fi
else
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
fi
