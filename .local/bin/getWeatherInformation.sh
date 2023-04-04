#!/usr/bin/env bash

# Set variables
city="Dongxiang,Fuzhou,Jiangxi,China"
URL="https://www.google.com/search?q=$(echo $city | sed 's/,/+/g')+weather"

# Create a temporary directory to store the file
temporaryDir=$(mktemp --directory)
wget -P "$temporaryDir" "https://wttr.in/$city.png"

# Output the result using Chromium if available, otherwise using curl
if ! chromium "$temporaryDir/$city.png" "$URL" 2>/dev/null
then
    curl "wttr.in/$city" | less -RS
    sleep 5s && rm -rf "$temporaryDir"
fi
