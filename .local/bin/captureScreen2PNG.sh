#!/usr/bin/env bash

# Dependencies: tofi, grim, hyprctl, jq, slurp, wl-copy, notify-send, scrot, xclip, xsel, niri

# === CONFIG ===
screenshot_dir="$HOME"
timestamp=$(date +%Y-%m-%d-%H%M%S)
filename="$screenshot_dir/$timestamp.png"

# === HELPERS ===

notify() {
    notify-send "Screenshot saved" "$1"
}

copy_to_clipboard() {
    if command -v wl-copy &>/dev/null; then
        wl-copy < "$1"
    elif command -v xclip &>/dev/null; then
        echo -n "![$1](../assets/$1)" | xclip -selection clipboard
    elif command -v xsel &>/dev/null; then
        echo -n "![$1](../assets/$1)" | xsel --input --clipboard
    fi
}

# === WAYLAND ===

wayland_capture() {
    local mode="$1"

    case "$mode" in
        full)
            grim - | wl-copy
            ;;
        active)
            if [[ "$XDG_CURRENT_DESKTOP" == "niri" ]]; then
                niri msg action screenshot-window
            elif [[ "$XDG_CURRENT_DESKTOP" == "Hyprland" ]]; then
                geometry=$(hyprctl -j activewindow | jq -r '"\(.at[0]),\(.at[1]) \(.size[0])x\(.size[1])"')
                grim -g "$geometry" - | wl-copy
            else
                echo "Error: Active window capture only supported in Niri or Hyprland."
                exit 1
            fi
            ;;
        select)
            grim -g "$(slurp)" - | wl-copy
            ;;
    esac

    sleep 1s
    wl-paste | swappy --file -
}

# === X11 ===

x11_capture() {
    local mode="$1"

    case "$mode" in
        full)     scrot "$filename" ;;
        focused)  scrot --focused "$filename" ;;
        select)   scrot --select "$filename" ;;
    esac

    copy_to_clipboard "$filename"
    notify "$filename"
}

# === MAIN ===

main() {
    mkdir -p "$screenshot_dir"
    mode=$(echo -e "full\nactive\nselect" | tofi)

    if [[ -z "$mode" ]]; then
        echo "No selection made. Exiting."
        exit 1
    fi

    if [[ "$XDG_SESSION_TYPE" == "wayland" ]]; then
        wayland_capture "$mode"
    else
        x11_capture "$mode"
    fi
}

main "$@"
