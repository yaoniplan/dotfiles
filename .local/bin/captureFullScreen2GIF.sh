#!/bin/bash


source $HOME/.local/bin/master.sh

# Delay before starting
fileExtension="gif"
DELAY=3

# Duration and output file
if [ $# -gt 0 ]; then
    D="--duration=$@"
else
    echo Default recording duration "$DELAY"s to "$fileName".gif
    D="--duration=10 "$fileName".gif"
fi
XWININFO=$(xwininfo)
read X <<< $(awk -F: '/Absolute upper-left X/{print $2}' <<< "$XWININFO")
read Y <<< $(awk -F: '/Absolute upper-left Y/{print $2}' <<< "$XWININFO")
read W <<< $(awk -F: '/Width/{print $2}' <<< "$XWININFO")
read H <<< $(awk -F: '/Height/{print $2}' <<< "$XWININFO")

echo Delaying $DELAY seconds. After that, byzanz will start
for (( i=$DELAY; i>0; --i )) ; do
    echo $i
    sleep 1
done

byzanz-record --verbose --delay=0 --x=$X --y=$Y --width=$W --height=$H $D
sendToTheClipboard
