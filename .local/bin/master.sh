#!/usr/bin/env bash

# Set variables
repoDir="$HOME/note"
readmeFile="$repoDir/README.md"
journalsDir="$repoDir/journals"
indexFile="$repoDir/assets/index.html"
temporaryFile="$HOME/yaoniplan.md"
fileName=$(date +%F_%H-%M)
readFromClipboard() {
    if command -v xclip; then
        yourClipboard="$(xclip -selection clipboard)"
    else
        yourClipboard="$(xsel --output --clipboard)"
    fi
}
sendToTheClipboard() {
    echo -n "!["$fileName"."$fileExtension"](../assets/"$fileName"."$fileExtension")" | xclip -selection clipboard
}

# Set functions
notification () {
    export $(dbus-launch); notify-send "$notificationMessage" &

    for i in {1..2}
    do
        paplay "$audioFile"
    done
}
