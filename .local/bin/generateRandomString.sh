#!/usr/bin/env bash

# Generate a random string with at least one uppercase letter, one lowercase letter, one digit, and one special character

# Define character sets
uppercase=$(tr -dc 'A-Z' </dev/urandom | head -c1)
lowercase=$(tr -dc 'a-z' </dev/urandom | head -c1)
digit=$(tr -dc '0-9' </dev/urandom | head -c1)
special=$(tr -dc '!@#$%^&*()_+{}[]:;<>,.?~' </dev/urandom | head -c1)

# Generate additional random characters to reach desired length (e.g., 16 characters)
# Adjust the length as needed
additional=$(tr -dc 'A-Za-z0-9!@#$%^&*()_+{}[]:;<>,.?~' </dev/urandom | head -c14)

# Combine all characters and shuffle them
generateRandomString=$(echo "$uppercase$lowercase$digit$special$additional" | fold -w1 | shuf | tr -d '\n')

# Copy to clipboard based on session type
if [[ "$XDG_SESSION_TYPE" == "wayland" ]]; then
    echo -n "$generateRandomString" | wl-copy
elif command -v xclip &>/dev/null; then
    echo -n "$generateRandomString" | xclip -selection clipboard
elif command -v xsel &>/dev/null; then
    echo -n "$generateRandomString" | xsel --input --clipboard
else
    echo "Command xclip or xsel not found."
fi
