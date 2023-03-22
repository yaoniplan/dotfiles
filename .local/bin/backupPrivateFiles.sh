#!/usr/bin/env bash

# Set the source and destination directories
remoteUser="yaoniplan"
remoteHost="192.168.10.105"
sourceDirectory="/mnt/Toshiba/growthRecord"
destinationDirectory="/mnt/backupPrivateFiles"

# Set the current date as the backup folder name
backupFolder="$(date +%F)"

# Create the destination directory if it does not exist
mkdir -p $destinationDirectory/$backupFolder

# Copy files from the source directory to the backup folder
rsync -av -e ssh $remoteUser@$remoteHost:"$sourceDirectory/" "$destinationDirectory/$backupFolder/"

# Print a success message
printf "Backup completed successfully!\n"
