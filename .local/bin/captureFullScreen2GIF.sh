#! /bin/sh

# Capture full screen to GIF
# Dependencies: xwininfo, gawk, byzanz, paplay, an audio file
# Refer to https://askubuntu.com/questions/107726/how-to-create-animated-gif-images-of-a-screencast/201018#201018
# https://serverfault.com/questions/532559/bash-script-count-down-5-minutes-display-on-single-line
# $countdownSeconds refer to https://unix.stackexchange.com/questions/246259/write-a-script-that-reads-a-number-and-counts-down-to-0

recordSeconds=10
widthOfFullScreen=$(xwininfo -root | gawk '/Width/ { print $2 }')
heightOfFullScreen=$(xwininfo -root | gawk '/Height/ { print $2 }')
#fileName="${HOME}/test/assets/`date +%F_%T`.gif"
fileName="$HOME/`date +%F_%T`.gif"
# Write a countdown here
countdownSeconds=2
# Write a sound and display notification
soundNotification() {
    paplay /usr/share/sounds/alsa/Noise.wav
}
while [[ $countdownSeconds > 0 ]]
do
    echo $countdownSeconds
    (( countdownSeconds -= 1))
    sleep 1
done

soundNotification
byzanz-record --verbose --duration=$recordSeconds \
    --x=0 --y=0 \
    --width=$widthOfFullScreen --height=$heightOfFullScreen \
    $fileName
soundNotification
