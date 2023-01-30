#! /bin/sh

# Capture full screen to GIF
# Dependencies: xwininfo, gawk, byzanz, paplay, an audio file
# Byzanz refer to https://askubuntu.com/questions/107726/how-to-create-animated-gif-images-of-a-screencast/201018#201018

recordSeconds=10
widthOfFullScreen=$(xwininfo -root | gawk '/Width/ { print $2 }')
heightOfFullScreen=$(xwininfo -root | gawk '/Height/ { print $2 }')
#fileName="${HOME}/test/assets/`date +%F_%T`.gif"
fileName="$HOME/`date +%F_%T`.gif"
# Write a sound and display notification
soundNotification() {
    paplay /usr/share/sounds/alsa/Noise.wav
}

soundNotification
byzanz-record --verbose --duration=$recordSeconds \
    --x=0 --y=0 \
    --width=$widthOfFullScreen --height=$heightOfFullScreen \
    $fileName
soundNotification
