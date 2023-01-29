#! /bin/sh

# Timer of tomato
# Dependencies: paplay, an audio file, notify-send

# Write a function about notification (e.g. sound, display)
soundNotification() {
    paplay /usr/share/sounds/alsa/Noise.wav && export $(dbus-launch) && notify-send "timerOfTomato"
}

# Write an infinite loop
# Add water at 8:00, drink water at 8:15, add water at 8:35, drink water at 8:50, ...
while true
do
    soundNotification
    sleep 900
    soundNotification
    sleep 1200
done
