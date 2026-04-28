#!/usr/bin/env bash

# Dependencies: wallpaper files, awww, tofi, curl, jq, rsync, notify-send, feh

# Set variables
wallpaper_directory="/mnt/yaoniplan/chinaTelecom/wallpaper"

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

    # Get random wallpaper
    random_wallpaper="$(shuf --head-count 1 "$wallpaper_list")"

    # Get current wallpaper (Even if file name contains spaces)
    current_wallpaper="$(basename "$(awww query | sed --silent 's/.*image: //p')")"

    # Get next wallpaper
    next_wallpaper="$(grep -x "$current_wallpaper" -A 1 "$wallpaper_list" | tail -1)"

    if [[ "$next_wallpaper" == "$current_wallpaper" || -z "$next_wallpaper" || -z "$current_wallpaper" || $? -ne 0 ]];  then
        echo "This is the last wallpaper!"
        generate_wallpaper_list
        next_wallpaper="$(head -1 "$wallpaper_list")"
    fi
    # Get previous wallpaper
    previous_wallpaper="$(grep -x "$current_wallpaper" -B 2 "$wallpaper_list" | tail -1)"

    # Interact with tofi
    selected_option=$(echo -e "wallhaven\nrandom\nnext\ndelete\nprevious\nregenerate" | tofi)

    case "$selected_option" in
        "wallhaven")
            image_url=$(curl -s "https://wallhaven.cc/api/v1/search?q=fractal&purity=100&sorting=random" | jq -r '.data[0].path')
            file_name=$(basename "$image_url")
            temp_file="/tmp/$file_name"
            curl -L -o "$temp_file" "$image_url"
            awww img --transition-type any "$temp_file"
            notify-send "Set wallpaper" "$file_name"
            # Move files but safer than `mv`
            rsync --archive --remove-source-files "$temp_file" "$wallpaper_directory"/
            generate_wallpaper_list
            ;;
        "random")
            awww img --transition-type any "$wallpaper_directory"/"$random_wallpaper"
            notify-send "Random wallpaper" "$random_wallpaper"
            ;;
        "next")
            # Set next wallpaper
            awww img --transition-type any "$wallpaper_directory"/"$next_wallpaper"
            notify-send "Set wallpaper" "$next_wallpaper"
            ;;
        "delete")
            # Delete current wallpaper
            rm "$wallpaper_directory"/"$current_wallpaper" &
            notify-send "Delete wallpaper" "$current_wallpaper"
            # Set next wallpaper
            awww img --transition-type any "$wallpaper_directory"/"$next_wallpaper"
            notify-send "Set wallpaper" "$next_wallpaper"
            ;;
        "previous")
            generate_wallpaper_list
            awww img --transition-type any "$wallpaper_directory"/"$previous_wallpaper"
            notify-send "Previous wallpaper" "$previous_wallpaper"
            ;;
        "regenerate")
            generate_wallpaper_list
            notify-send "Generate list successfully!"
            ;;
    esac
else
    feh --randomize --bg-fill "$wallpaper_directory"
fi
