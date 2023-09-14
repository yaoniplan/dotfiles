#!/usr/bin/env bash

# Dependencies: xclip or xsel, curl

# Set the variables
defaultTag="#todo"
yourHTTPRequest="http://192.168.10.100:5230/api/v1/memo?openId=aabc309c-c5bd-4882-971e-33ac106267f0"
yourContent="$@ $defaultTag"

# Check if arguments are provided
if [[ "$#" = 0 ]]; then
    if command -v xclip; then
        yourContent="$(xclip -selection clipboard) $defaultTag"
    else
        yourContent="$(xsel --output --clipboard) $defaultTag"
    fi
fi

# Make the HTTP request with cURL
curl "$yourHTTPRequest" -H 'Content-Type: application/json' -d "{\"content\":\"$yourContent\"}" -m 10
