#!/usr/bin/env bash

# Set variables
repoDir="$HOME/note"
journalsDir="$repoDir/journals"
indexFile="$repoDir/assets/index.html"
temporaryFile="$HOME/yaoniplan.md"

# Set functions
notification () {
    export $(dbus-launch); notify-send "$notificationMessage" &

    for i in {1..2}
    do
        paplay "$audioFile"
    done
}
