#!/usr/bin/env sh

# Set variables
trashDir="$HOME/.trash"

# Check if the directory exists
[[ -d "$trashDir" ]] || mkdir --parents "$trashDir"

# Delete files and directories older than 30 days
find "$trashDir" -mindepth 1 -ctime +30 -delete
