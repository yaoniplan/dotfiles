#!/usr/bin/env bash

notification () {
    notify-send "$notificationMessage" &

    for i in {1..2}
    do
        paplay "$audioFile"
    done
}
