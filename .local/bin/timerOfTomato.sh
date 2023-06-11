#!/usr/bin/env bash

notificationMessage="Pomodoro time is up!"
audioFile="/home/yaoniplan/note/assets/doorbell.mp3"

source $HOME/.local/bin/master.sh

while true; do
    notification
    sleep 20m
done
