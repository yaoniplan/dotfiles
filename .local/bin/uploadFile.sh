#!/usr/bin/env bash

# Check if the parameter is exists
if [[ "$#" -ne 0 ]]; then
    fileName="$@"
else
    # Interact with tofi
    if command -v tofi &>/dev/null; then
        fileName=$(selectFile.sh)
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
selected_option=$(echo -e "Public\nPrivate" | tofi)

case "$selected_option" in
    "Public")
        filePath="chinaTelecom/$(date +%Y/%m/%d)"
        endpoint="http://100.65.173.16:5244/dav/"$filePath"/"
        ;;
    "Private")
        filePath="grow/temporary/$(date +%Y/%m/%d)"
        endpoint="http://100.65.173.16:5244/dav/"$filePath"/"
        ;;
    *)
        echo "Invalid selection. Aborting."
        exit 1
        ;;
esac

curl --user "$authorization" --upload-file "$fileName" "$endpoint"

# Notify with notify-send or terminal
if command -v notify-send; then
    notify-send "Upload" "$fileName"
    echo $(echo "$endpoint"$(basename "$fileName") | sed 's/\/dav//g')
else
    echo "Upload" "$fileName"
    echo $(echo "$endpoint"$(basename "$fileName") | sed 's/\/dav//g')
fi
