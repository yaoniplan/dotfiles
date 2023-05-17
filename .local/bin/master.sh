#!/usr/bin/env bash

notification () {
    export $(dbus-launch); notify-send "$notificationMessage" &

    for i in {1..2}
    do
        paplay "$audioFile"
    done
}
