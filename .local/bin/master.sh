#!/usr/bin/env bash

# Set variables
repoDir="$HOME/.config/note"
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
    if [[ "$XDG_SESSION_TYPE" = "wayland" ]]; then
        notify-send "$notificationMessage" &

        for i in {1..2}
        do
            paplay "$audioFile"
        done
    else
        export $(dbus-launch); notify-send "$notificationMessage" &

        for i in {1..2}
        do
            paplay "$audioFile"
        done
    fi
}
