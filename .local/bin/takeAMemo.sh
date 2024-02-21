#!/usr/bin/env bash

# Dependencies: tofi, curl, jq, notify-send

# Set your access token
ACCESS_TOKEN="eyJhbGciOiJIUzI1NiIsImtpZCI6InYxIiwidHlwIjoiSldUIn0.eyJuYW1lIjoiYWRtaW4iLCJpc3MiOiJtZW1vcyIsInN1YiI6IjEiLCJhdWQiOlsidXNlci5hY2Nlc3MtdG9rZW4iXSwiZXhwIjoxNzA4NTE0NzMyLCJpYXQiOjE3MDg0ODU5MzJ9.IXWuKllhzuQxaHivDuTSVVS3y9VRJ2gF21nzCcqKv7o"

# Set the server URL
SERVER_URL="https://memos.yaoniplan.eu.org/api/v1/memo"

# Set the default tag
tag="#TODO\n"

# Prompt user to input the content interactively using dmenu
memo=$(tofi --prompt-text "Enter memo content: ")

# Check if memo is empty
if [[ -z "$memo" ]]; then
    echo "Memo is empty. Aborting."
    exit 1
fi

# Read the content of the Markdown file and escape special characters
content=$(echo "$tag$memo" | sed ':a;N;$!ba;s/\n/\\n/g' | sed 's/"/\\"/g')

# Prepare the JSON payload
json_payload="{\"content\":\"$content\"}"

# Send the content to the remote server using curl
response=$(curl --request POST "$SERVER_URL" \
     --header "Content-Type: application/json" \
     --header "Authorization: Bearer $ACCESS_TOKEN" \
     --data "$json_payload")

# Check exit status of curl command
if [[ $? -eq 0 ]]; then
    # If curl succeeds, parse the content from the response and send notification
    notification_content=$(echo "$response" | jq -r '.content')
    notify-send "Curl Success" "$notification_content"
else
    # If curl fails, send notification of failure with error message
    notify-send "Curl Failed" "$response"
fi
