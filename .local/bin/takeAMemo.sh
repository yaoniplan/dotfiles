#!/usr/bin/env bash

# Dependencies: xclip or xsel, curl

# Set variables
yourHTTPRequest="http://192.168.10.107:2004/diary"

if [[ "$1" == "--no-clipboard" ]]; then
    yourContent="${@:2}"
else
    if command -v xclip; then
        yourClipboard="$(xclip -selection clipboard)"
    else
        yourClipboard="$(xsel --output --clipboard)"
    fi
    yourContent="$yourClipboard # $@"
fi

# Make the HTTP request with cURL
curl --request POST --data "entry=$yourContent" "$yourHTTPRequest"
