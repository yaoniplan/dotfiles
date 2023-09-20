#!/usr/bin/env bash

# Dependencies: xclip or xsel, curl

# Set variables
defaultTag="#todo"
yourHTTPRequest="http://192.168.10.100:5230/api/v1/memo"
yourAccessToken="eyJhbGciOiJIUzI1NiIsImtpZCI6InYxIiwidHlwIjoiSldUIn0.eyJuYW1lIjoieWFvbmlwbGFuIiwiaXNzIjoibWVtb3MiLCJzdWIiOiIxIiwiYXVkIjpbInVzZXIuYWNjZXNzLXRva2VuIl0sImlhdCI6MTY5NDg3NDI5MH0.FV_4Ml5mLBwrEfwwMoD-b-_noFAMtR0L157D87phPew"
yourContent="$@"

if command -v xclip; then
    yourClipboard="$(xclip -selection clipboard)"
else
    yourClipboard="$(xsel --output --clipboard)"
fi
yourClipboardWithNewlines=$(echo -e "$yourClipboard" | sed ':a;N;$!ba;s/\n/\\n/g')
yourContentWithTags="- $yourClipboardWithNewlines # $yourContent $defaultTag"

# Make the HTTP request with cURL
curl "$yourHTTPRequest" \
   -H "Accept: application/json" \
   -H "Authorization: Bearer $yourAccessToken" \
   -d "{\"content\":\"$yourContentWithTags\"}" -m 10
