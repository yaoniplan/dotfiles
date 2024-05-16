#!/usr/bin/env bash

# Dependencies: wallpaper files, swww, tofi, notify-send, feh

# Set variables
wallpaper_directory="/mnt/yaoniplan/interestAndHobby/wallpaper"

# Check if the display server protocol is Wayland
if [[ "$XDG_SESSION_TYPE" = "wayland" ]]; then
    # Generate a cached list of file names
    generate_wallpaper_list() {
        ls "$wallpaper_directory" > "$wallpaper_list"
    }

    wallpaper_list="$HOME/.cache/wallpaper-compgen"

    # Generate wallpaper file name list if not exists
    if [[ ! -f "$wallpaper_list" ]]; then
        generate_wallpaper_list
        echo "Generate list successfully!"
    fi

    # Get current wallpaper (Even if file name contains spaces)
    current_wallpaper="$(basename "$(swww query | sed --silent 's/.*image: //p')")"

    # Get next wallpaper
    next_wallpaper="$(grep -x "$current_wallpaper" -A 1 "$wallpaper_list" | tail -1)"

    if [[ "$next_wallpaper" == "$current_wallpaper" || -z "$next_wallpaper" || -z "$current_wallpaper" || $? -ne 0 ]];  then
        echo "This is the last wallpaper!"
        generate_wallpaper_list
        next_wallpaper="$(head -1 "$wallpaper_list")"
    fi

    # Interact with tofi
    selected_option=$(echo -e "next\ndelete" | tofi)

    case "$selected_option" in
        "next")
            # Set next wallpaper
            swww img --transition-type any "$wallpaper_directory"/"$next_wallpaper"
            notify-send "Set wallpaper" "$next_wallpaper"
            ;;
        "delete")
            # Delete current wallpaper
            rm "$wallpaper_directory"/"$current_wallpaper" &
            notify-send "Delete wallpaper" "$current_wallpaper"
            # Set next wallpaper
            swww img --transition-type any "$wallpaper_directory"/"$next_wallpaper"
            notify-send "Set wallpaper" "$next_wallpaper"
            ;;
    esac

    # Check if there was an error
    if [[ $? -ne 0 ]]; then
        generate_wallpaper_list
        notify-send "Generate list successfully!"
    fi
else
    feh --randomize --bg-fill "$wallpaper_directory"
fi
