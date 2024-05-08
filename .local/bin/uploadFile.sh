#!/usr/bin/env bash

# Check if the parameter is exists
if [[ "$#" -ne 0 ]]; then
    fileName="$@"
else
    # Interact with tofi
    if command -v tofi &>/dev/null; then
        fileName=$(echo "" | tofi)
    else
        echo "Usage: $0 [file name]"
        exit 1
    fi

    # Check if file name is empty
    if [[ -z "$fileName" ]]; then
        echo "File name is empty. Aborting."
        exit 1
    fi
fi

# Adjust based on needs
authorization="admin:jj"
filePath="chinaTelecom/$(date +%Y/%m/%d)"
endpoint="http://100.65.173.16:5244/dav/"$filePath"/"

curl --user "$authorization" --upload-file "$fileName" "$endpoint"

# Notify with notify-send or terminal
if command -v notify-send; then
    notify-send "Upload" "$fileName"
else
    echo "Upload" "$fileName"
fi
