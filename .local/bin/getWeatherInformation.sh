#!/usr/bin/env bash

# Set variables
city="Dongxiang,Fuzhou,Jiangxi,China"
URL="https://www.google.com/search?q="$(echo "$city" | sed 's/,/+/g')"+weather"

# Use default web browser or curl
if command -v xdg-open &>/dev/null; then
    xdg-open "$URL"
else
    curl "wttr.in/"$city"" | less -RS
fi
