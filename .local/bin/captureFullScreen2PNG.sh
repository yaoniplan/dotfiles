#! /bin/sh

#Capture a window to PNG file

storageLocation=$HOME
fileName=$(date +%F_%T.png)
sendToTheClipboard() {
    echo -n "![$fileName](../assets/$fileName)" | xclip -selection clipboard
}

scrot -u "$HOME/$fileName"
sendToTheClipboard
