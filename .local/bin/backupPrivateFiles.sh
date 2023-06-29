#!/usr/bin/env bash

# Set variables
remoteUser="yaoniplan"
remoteHost="192.168.10.105"
sourceDir="/mnt/grow"
destinationDir="/mnt/grow"
backupFolder="$(date +%F)"
numberOfFiles=$(ls -1 "$sourceDir" | wc -l)
quantityToDelete=$(("$numberOfFiles" - 15))

# Create the destination directory if it does not exist
mkdir -p $destinationDir/$backupFolder

# Keep 15 directories only
if [[ "$numberOfFiles" -gt 15 ]]; then
    ls -1d "$destinationDir"/* | head -"$quantityToDelete" | xargs rm -rf
fi

# Copy files from the source directory to the backup folder
if command -v rsync &>/dev/null; then
    rsync -av --exclude="*.iso" $remoteUser@$remoteHost:"$sourceDir/" "$destinationDir/$backupFolder/"
else
    $HOME/.nix-profile/bin/rsync -av --exclude="*.iso" $remoteUser@$remoteHost:"$sourceDir/" "$destinationDir/$backupFolder/"
fi
