#!/bin/bash

# Dependencies: tofi, wayst, vim

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
        wayst -e vim "$directory/$selection"
        exit 0
    fi
done
