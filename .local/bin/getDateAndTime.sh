#!/usr/bin/env bash

# Dependencies: tofi, notify-send, gtts-cli, mpg123

# Set variables
currentData="It's $(date +%A), $(date +%B)$(date +%e), $(date +%Y)." # e.g. It's Friday, March 1, 2024.
currentTime="It's $(date +%H:%M)." # e.g. It's 10:03.

if [[ "$XDG_SESSION_TYPE" = "wayland" ]]; then
    selected_option=$(echo -e "date\ntime" | tofi)

    case "$selected_option" in
        "date")
            notify-send "Date" "$currentData" && gtts-cli "$currentData" | mpg123 -
            ;;
        "time")
            notify-send "Time" "$currentTime" && gtts-cli "$currentTime" | mpg123 -
            ;;
        *)
            notify-send "Time" "$currentTime" && gtts-cli "$currentTime" | mpg123 -
            ;;
    esac
else
    # Check if the first argument is coorsponding string
    if [[ "$1"  == "date" ]]; then
        export $(dbus-launch); notify-send "$currentDate" && gtts-cli "$currentDate" | mpg123 -
    elif [[ "$1" == "time" ]]; then
        export $(dbus-launch); notify-send "$currentTime" && gtts-cli "$currentTime" | mpg123 -
    else
        export $(dbus-launch); notify-send "$currentTime" && gtts-cli "$currentTime" | mpg123 -
    fi
fi
