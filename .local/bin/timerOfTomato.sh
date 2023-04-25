#!/usr/bin/env bash

notificationMessage="Pomodoro time is up!"
audioFile="/home/yaoniplan/note/assets/doorbell.mp3"

source master.sh

while true
do
    notification
    sleep 15m
    notification
    sleep 20m
done
