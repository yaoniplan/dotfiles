#!/usr/bin/env bash

# Set the source and destination directories
sourceDirectory="/mnt/Toshiba/testGrowthRecord"
destinationDirectory="/mnt/test/backup"

# Create the destination directory if it does not exist
if [ ! -d $destinationDirectory ]; then
    mkdir $destinationDirectory
fi

# Set the current date as the backup folder name
backupFolder="$(date +%F_%T)"

# Create the backup folder within the destination directory
mkdir "$destinationDirectory/$backupFolder"

# Copy files from the source directory to the backup folder
cp -r $sourceDirectory/* "$destinationDirectory/$backupFolder"

# Print a success message
echo "Backup completed successfully!"
