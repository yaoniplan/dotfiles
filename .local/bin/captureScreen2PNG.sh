#!/usr/bin/env bash

# Dependencies: tofi, grim, hyprctl, jq, slurp, wl-copy, notify-send, scrot, xclip, xsel

# Check if the display server protocol is Wayland
if [[ "$XDG_SESSION_TYPE" = "wayland" ]]; then
    # Set the file name for yourself
    fileName="/mnt/grow/image/$(date +%Y-%m-%d-%H%M%S.png)"

    selected_option=$(echo -e "full\nactive\nselect" | tofi)

    case "$selected_option" in
        "full")
            grim "$fileName"
            ;;
        "active")
            # Check if the desktop is Hyprland
            if [[ "$XDG_CURRENT_DESKTOP" = "Hyprland" ]]; then
                geometry=$(hyprctl -j activewindow | jq -r '"\(.at[0]),\(.at[1]) \(.size[0])x\(.size[1])"')

                grim -g "$geometry" "$fileName"
            else
                echo "Error: Your \$XDG_CURRENT_DESKTOP is not Hyprland."
                exit 0
            fi
            ;;
        "select")
            grim -g "$(slurp)" "$fileName"
            ;;
        *)
            echo "Invalid selection. Aborting."
            exit 1
            ;;
    esac
    # Copy file name to clipboard
    echo "$fileName" | wl-copy
    notify-send "Screenshot" "$fileName"
else
    storageLocation=$HOME
    fileName=$(date +%F_%H-%M.png)
    sendToTheClipboard() {
        if command -v xclip &>/dev/null; then
            echo -n "![$fileName](../assets/$fileName)" | xclip -selection clipboard
        else
            echo -n "![$fileName](../assets/$fileName)" | xsel --input --clipboard
        fi
    }

    # Write a if condition judgement
    if [ $1 == "full" ]; then
        scrot "$storageLocation"/"$fileName"
    elif [ $1 == "focused" ]; then
        scrot --focused "$storageLocation"/"$fileName"
    else
        scrot --select "$storageLocation"/"$fileName"
    fi
    sendToTheClipboard
fi
