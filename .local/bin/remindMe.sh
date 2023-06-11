#!/usr/bin/env bash

notificationMessage="Time is up!"
audioFile="/home/yaoniplan/note/assets/doorbell.mp3"

source $HOME/.local/bin/master.sh

sleep "$1"; notification
