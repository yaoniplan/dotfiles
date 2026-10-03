#!/bin/bash

# Dependencies: tofi, notify-send, gtts-cli

# Prompt the user to enter a reminder message
# e.g. Fill bottle with water
reminder_message=$(echo "" | tofi --prompt-text "Enter Reminder: ")
# Check if input is empty
if [[ -z "$reminder_message" ]]; then
    echo "Input is empty. Aborting."
    exit 1
fi

# Prompt the user to enter a duration for the reminder
# e.g. 6
reminder_duration=$(echo "" | tofi --prompt-text "Enter Duration (minutes): ")
deadline=$(date --date="now + $reminder_duration minutes" '+%H:%M')
# Check if input is empty
if [[ -z "$reminder_duration" ]]; then
    echo "Input is empty. Aborting."
    exit 1
fi

# Convert the duration to seconds
reminder_duration_seconds=$((reminder_duration * 60 * 1000))

# Random icon
random_icon=$(shuf -n1 ~/.cache/.icons-list)

# Set a timer for the reminder (icon: appointment-reminder)
notify-send --icon="$random_icon" --expire-time="$reminder_duration_seconds" "$deadline" "$reminder_message" && gtts-cli "$reminder_message" | mpg123 -

##!/usr/bin/env bash
#
#notificationMessage="Time is up!"
#audioFile="/home/yaoniplan/note/assets/doorbell.mp3"
#
#source $HOME/.local/bin/master.sh
#
#sleep "$1"; notification
