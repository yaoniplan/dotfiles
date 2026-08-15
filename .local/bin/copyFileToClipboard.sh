#!/usr/bin/env bash

# Check if running on Wayland
[[ "$XDG_SESSION_TYPE" == "wayland" ]] && clipboard='wl-copy' || clipboard='xclip -selection clipboard'

# Check if the parameter is exists
if [[ "$#" -ne 0 ]]; then
    fileName="$@"
    cat "$fileName" | "$clipboard"
else
    # Interact with tofi
    if command -v tofi &>/dev/null; then
        # Define the directory to start with
        directory="/"

        while true; do
            # List all files and directories in the current directory and show them in dmenu
            selection=$(ls -a "$directory" | tofi)

            if [[ -z "$selection" ]]; then
                # If no file or directory is selected, exit the script
                exit 0
            elif [[ -d "$directory/$selection" ]]; then
                # If a directory is selected, enter the directory
                directory="$directory/$selection"
            else
                # If a file is selected, open it with Vim
                cat "$directory/$selection" | "$clipboard"
                exit 0
            fi
        done
    else
        echo "Usage: $(basename "$0") [file...]"
        exit 1
    fi
fi
