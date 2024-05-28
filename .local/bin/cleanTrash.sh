#!/usr/bin/env sh

# Set variables
trashDir="/home/yaoniplan/.trash"

# Delete files and directories older than 30 days
find "$trashDir" -mindepth 1 -mtime +30 -delete
