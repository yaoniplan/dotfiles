#!/usr/bin/env bash

# Set variables
remoteUser="yaoniplan"
remoteHost="192.168.10.105"
sourceDir="/mnt/grow"
destinationDir="/mnt/grow"
backupFolder="$(date +%F)"
numberOfFiles=$(ls -1 "$sourceDir" | wc -l)
quantityToDelete=$(("$numberOfFiles" - 30))

# Create the destination directory if it does not exist
mkdir -p $destinationDir/$backupFolder

# Keep 30 directories only
if [[ "$numberOfFiles" -gt 30 ]]; then
    ls -1d "$destinationDir"/* | head -"$quantityToDelete" | xargs rm -rf
fi

# Copy files from the source directory to the backup folder
rsync -av --exclude="*.iso" $remoteUser@$remoteHost:"$sourceDir/" "$destinationDir/$backupFolder/"
