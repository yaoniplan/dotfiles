#!/usr/bin/env bash

# Dependencies: tofi, curl, notify-send

# Set the server URL
SERVER_URL="http://100.65.173.16:2004/diary"

# Set the default tag
tag=""

# Prompt user to input the content interactively using dmenu
memo=$(echo "" | tofi)

# Check if memo is empty
if [[ -z "$memo" ]]; then
    echo "Memo is empty. Aborting."
    exit 1
fi

# Read the content of the Markdown file and escape special characters
content=$(echo "$tag$memo" | sed ':a;N;$!ba;s/\n/\\n/g' | sed 's/"/\\"/g')

# Prepare the JSON payload
json_payload="entry=$content"

# Send the content to the remote server using curl
response=$(curl --request POST "$SERVER_URL" --data "$json_payload")

# Check exit status of curl command
if [[ $? -eq 0 ]]; then
    # If curl succeeds, parse the content from the response and send notification
    notify-send "Curl Success" "$content"
else
    # If curl fails, send notification of failure with error message
    notify-send "Curl Failed" "$response"
fi
