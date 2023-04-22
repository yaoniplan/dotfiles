#!/usr/bin/env bash

# Set variables
remoteUser="yaoniplan"
remoteHost="192.168.10.173"
sourceDir="/mnt/Toshiba/growthRecord"
destinationDir="/mnt/backupPrivateFiles"
backupFolder="$(date +%F)"

# Create the destination directory if it does not exist
mkdir -p $destinationDir/$backupFolder

# Copy files from the source directory to the backup folder
rsync -av $remoteUser@$remoteHost:"$sourceDir/" "$destinationDir/$backupFolder/"
