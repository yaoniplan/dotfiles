#!/usr/bin/env bash

notificationMessage="Time is up!"
audioFile="/home/yaoniplan/note/assets/doorbell.mp3"

source master.sh

sleep "$1"; notification
