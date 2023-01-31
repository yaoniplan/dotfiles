#! /bin/sh

# Capture full screen to GIF
# Dependencies: xwininfo, gawk, byzanz, paplay, an audio file, xclip
# Byzanz refer to https://askubuntu.com/questions/107726/how-to-create-animated-gif-images-of-a-screencast/201018#201018

recordSeconds=10
widthOfFullScreen=$(xwininfo -root | gawk '/Width/ { print $2 }')
heightOfFullScreen=$(xwininfo -root | gawk '/Height/ { print $2 }')
storageLocation=$HOME
fileName="`date +%F_%T`.gif"

# Write a function that sends a string to the clipboard
sendToTheClipboard() {
    echo -n "![$fileName](../assets/$fileName)" | xclip -selection clipboard
}

# Write a sound notification
soundNotification() {
    paplay /usr/share/sounds/alsa/Noise.wav
}

soundNotification
byzanz-record --duration=$recordSeconds \
    --x=0 --y=0 \
    --width=$widthOfFullScreen --height=$heightOfFullScreen \
    "$storageLocation/$fileName"
sendToTheClipboard
soundNotification
