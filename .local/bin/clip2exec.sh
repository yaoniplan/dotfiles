#!/usr/bin/env bash

# Dependencies: tofi, wl-clipboard, notify-send

# Prompt the user to enter a script name using dmenu
SCRIPT_NAME=$(ls -1 "$HOME/.local/bin/" | tofi --prompt "Enter script name:")

# Check if a script name was entered
if [ -n "$SCRIPT_NAME" ]; then
    # Define the target directory
    TARGET_DIR="$HOME/.local/bin"

    # Create the target directory if it doesn't exist
    mkdir -p "$TARGET_DIR"

    # Define the full path to the new script
    SCRIPT_PATH="$TARGET_DIR/$SCRIPT_NAME"

    # Retrieve clipboard content using wl-paste
    CLIPBOARD_CONTENT=$(wl-paste)

    # Save the clipboard content to the specified file
    echo "$CLIPBOARD_CONTENT" > "$SCRIPT_PATH"

    # Make the file executable
    chmod +x "$SCRIPT_PATH"

    # Notify the user
    notify-send "Script saved and made executable" "$SCRIPT_PATH"
fi
