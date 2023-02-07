#! /bin/sh

# "How much time delay? '30s' for 30 seconds, '3m' for 30 minutes"
# Usage: `remindMe.sh 3m &`
# Dependencies: sleep, paplay, an audio file, notify-send

sleep $1; paplay /usr/share/sounds/alsa/Noise.wav & notify-send "Time is up" &
