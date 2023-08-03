#!/usr/bin/env bash

# Generate random string
# At least one uppercase letter, one lowercase letter, one number, and one special symbol

generateRandomString=$(openssl rand -base64 11)

if command -v xclip; then
    echo $generateRandomString@gmail.com | xclip -selection clipboard
elif command -v xsel; then
    echo $generateRandomString@gmail.com | xsel --input --clipboard
else
    echo "xclip or xsel not found"
fi
