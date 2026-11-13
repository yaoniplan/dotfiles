#!/usr/bin/env bash

# Dependencies: swayimg, curl, wl-clipboard

# Use the first argument if provided
if [ -n "$1" ]; then
    image_url="$1"
    swayimg "exec://curl -sL '$image_url'"
    exit 0
fi

# Clipboard already contains an image MIME type
if wl-paste --list-types | grep -q '^image/'; then
    wl-paste --type image/png | swayimg -
    exit 0
fi

clipboard=$(wl-paste)

# Base64 data URL
if [[ $clipboard == data:image/*';base64,'* ]]; then
    printf '%s' "${clipboard#*,}" | base64 --decode | swayimg -
    exit 0
fi

# HTTP(S) URL
image_url=$(printf '%s' "$clipboard" | grep -Eo 'https?://[^[:space:]]+' | head -n1)

if [ -n "$image_url" ]; then
    swayimg "exec://curl -fsSL '$image_url'"
    exit 0
fi

echo "No image, Base64 image, or valid URL found in the clipboard."
exit 1
