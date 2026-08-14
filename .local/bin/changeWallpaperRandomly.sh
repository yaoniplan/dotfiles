#!/usr/bin/env bash

# Set variables
wallpaper_directory="/mnt/yaoniplan/chinaTelecom/wallpaper"

# Check if the display server protocol is Wayland
if [[ "$XDG_SESSION_TYPE" = "wayland" ]]; then
    # Generate a cached list of file names
    generate_wallpaper_list() {
        ls "$wallpaper_directory" > "$wallpaper_list"
    }

    wallpaper_list="$HOME/.cache/wallpaper-compgen"

    ## Generate wallpaper file name list if not exists
    #if [[ ! -f "$wallpaper_list" ]]; then
    #    generate_wallpaper_list
    #    echo "Generate list successfully!"
    #fi

    # Get random wallpaper
    random_wallpaper="$(shuf --head-count 1 "$wallpaper_list")"

    # Get current wallpaper (Even if file name contains spaces)
    current_wallpaper="$(basename "$(awww query | sed --silent 's/.*image: //p')")"

    # Get next wallpaper
    next_wallpaper="$(grep -x "$current_wallpaper" -A 1 "$wallpaper_list" | tail -1)"

    #if [[ "$next_wallpaper" == "$current_wallpaper" || -z "$next_wallpaper" || -z "$current_wallpaper" || $? -ne 0 ]];  then
    #    echo "This is the last wallpaper!"
    #    generate_wallpaper_list
    #    next_wallpaper="$(head -1 "$wallpaper_list")"
    #fi
    # Get previous wallpaper
    previous_wallpaper="$(grep -x "$current_wallpaper" -B 2 "$wallpaper_list" | tail -1)"

    # Interact with tofi
    selected_option=$(echo -e "api\nrandom\nnext\ndelete\nprevious\nregenerate" | tofi)

    case "$selected_option" in
        api)
            # List of API commands – each outputs an image URL
            api_commands=(
                'curl -Ls -o /dev/null -w "%{url_effective}" "https://www.aini.cn.eu.org/random"'
                'curl -s "https://wallhaven.cc/api/v1/search?q=fractal&purity=100&sorting=random" | jq -r ".data[0].path"'
                'curl -sL -o /dev/null -w "%{url_effective}\n" https://tool.teyonds.com/api'
            )

            # Shuffle the list, preserving each full command as one array entry
            shuffled=()
            while IFS= read -r line; do
                shuffled+=("$line")
            done < <(printf "%s\n" "${api_commands[@]}" | shuf)

            success=false
            for cmd in "${shuffled[@]}"; do
                # Evaluate the command to get the image URL
                image_url=$(eval "$cmd")
                [[ -z "$image_url" ]] && continue

                # Download & processing logic
                file_name=$(basename "$image_url")
                [[ -z "$file_name" ]] && continue
                file="/tmp/$file_name"
                [[ -f "$file" ]] || curl -L -o "$file" "$image_url" || continue
                [[ ! -e "$file" ]] && continue

                # Fix extension
                current_ext="${file_name##*.}"
                real_ext=$(file --extension --brief "$file" | cut -d/ -f1)
                if [[ "$current_ext" != "$real_ext" ]]; then
                    cp "$file" "/tmp/${file_name%.*}.$real_ext"
                    file="/tmp/${file_name%.*}.$real_ext"
                fi

                # Apply wallpaper
                matugen image "$file" --source-color-index 0
                notify-send "Set wallpaper" "$file_name"

                success=true
                break
            done

            if [[ "$success" != true ]]; then
                notify-send "All APIs failed" "Could not fetch a wallpaper from any source."
                exit 1
            fi
            ;;
        "random")
            file="$wallpaper_directory"/"$random_wallpaper"
            matugen image "$file" --source-color-index 0
            notify-send "Random wallpaper" "$random_wallpaper"
            ;;
        "next")
            # Set next wallpaper
            file="$wallpaper_directory"/"$next_wallpaper"
            matugen image "$file" --source-color-index 0
            notify-send "Set wallpaper" "$next_wallpaper"
            ;;
        "delete")
            # Delete current wallpaper
            rm "$wallpaper_directory"/"$current_wallpaper" &
            notify-send "Delete wallpaper" "$current_wallpaper"
            # Set next wallpaper
            file="$wallpaper_directory"/"$next_wallpaper"
            matugen image "$file" --source-color-index 0
            notify-send "Set wallpaper" "$next_wallpaper"
            ;;
        "previous")
            generate_wallpaper_list
            file="$wallpaper_directory"/"$previous_wallpaper"
            matugen image "$file" --source-color-index 0
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
