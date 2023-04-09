#! /bin/sh

# "How much time delay? '30s' for 30 seconds, '3m' for 30 minutes"
# Usage: `remindMe.sh 3m &`
# Dependencies: sleep, paplay, an audio file, notify-send

filePath="/usr/share/sounds/alsa/doorbell.mp3"
sleep $1
notify-send "Time is up" &
for times in {1..2}
do
    paplay $filePath
done
