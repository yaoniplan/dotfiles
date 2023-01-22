#! /bin/sh

# Capture fullscreen to GIF
# Dependencies: xwininfo, byzanz
# Refer to https://askubuntu.com/questions/107726/how-to-create-animated-gif-images-of-a-screencast/201018#201018

recordTime=10
widthOfFullScreen=$(xwininfo -root | gawk '/Width/ { print $2 }')
heightOfFullScreen=$(xwininfo -root | gawk '/Height/ { print $2 }')
fileName="${HOME}/test/assets/`date +%F_%T`.gif"

byzanz-record --verbose --duration=$recordTime \
    --x=0 --y=0 \
    --width=$widthOfFullScreen --height=$heightOfFullScreen \
    $fileName
