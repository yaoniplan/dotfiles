#!/usr/bin/env bash

# Set variables
city="Dongxiang,Fuzhou,Jiangxi,China"
URL="https://www.google.com/search?q=$(echo $city | sed 's/,/+/g')+weather"

# Output the result using Chromium if available, otherwise using curl
if command -v chromium &>/dev/null; then
    chromium "$URL" 2>/dev/null
    temporaryDir=$(mktemp --directory)
    wget -P "$temporaryDir" "https://wttr.in/$city.png"
    sleep 5s
    chromium "$temporaryDir/$city.png"
    sleep 5s
    rm -rf "$temporaryDir"
else
    curl "wttr.in/$city" | less -RS
fi
