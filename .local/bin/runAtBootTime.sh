#!/usr/bin/env bash

# Check if the display server protocol is Wayland
if [[ "$XDG_SESSION_TYPE" = "wayland" ]]; then
    execute_command() {
        if command -v "$1" &>/dev/null && ! pgrep "$1" &>/dev/null; then
            "$@" &>/dev/null &
        fi
    }

    execute_command foot --server
    execute_command udiskie
    execute_command mako
    execute_command wlsunset -l 28.2 -L 116.6
    execute_command swww-daemon
    execute_command rclone mount yaoniplan:/ /mnt/yaoniplan/ --header "Referer:"
else
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
fi
