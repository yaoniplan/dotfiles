#!/usr/bin/env bash

# Set variables
remoteUser="yaoniplan"
remoteHost="192.168.10.105"
sourceDir="/mnt/grow"
destinationDir="/mnt/grow"
backupFolder="$(date +%F)"

# Create the destination directory if it does not exist
mkdir -p $destinationDir/$backupFolder

# Copy files from the source directory to the backup folder
rsync -av --exclude="*.iso" $remoteUser@$remoteHost:"$sourceDir/" "$destinationDir/$backupFolder/"
