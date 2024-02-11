#!/usr/bin/env bash

# Generate random string
# At least one uppercase letter, one lowercase letter, one number, and one special symbol

generateRandomString=$(openssl rand -base64 11 | tr -d '\n')

if [[ "$XDG_SESSION_TYPE" = "wayland" ]]; then
    echo "$generateRandomString@gmail.com" | wl-copy
else
    if command -v xclip; then
        echo $generateRandomString@gmail.com | xclip -selection clipboard
    elif command -v xsel; then
        echo $generateRandomString@gmail.com | xsel --input --clipboard
    else
        echo "Command xclip or xsel not found."
    fi
fi
