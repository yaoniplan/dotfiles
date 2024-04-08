#!/usr/bin/env bash

# Dependencies: pactl, tofi, notify-send

# Get the current volume
current_volume=$(pactl list sinks | grep 'Volume' | head -1 | awk '{print $5}' | sed 's/%//')

# Prompt the user to enter the desired volume level
new_volume=$(echo "" | tofi --prompt-text "Set Volume Level $current_volume to (0-100): ")

# Validate the input (check if it's a number)
if [[ ! $new_volume =~ ^[0-9]+$ ]]; then
    notify-send "Invalid Input" "Please enter a valid number between 0 and 100."
    exit 1
fi

# Ensure the volume level is within the valid range (0-100)
if (( $new_volume < 0 || $new_volume > 100 )); then
    notify-send "Invalid Volume" "Please enter a volume level between 0 and 100."
    exit 1
fi

# Set the new volume level
pactl set-sink-volume @DEFAULT_SINK@ "$new_volume%"

# Show a notification with the new volume level
notify-send "Volume" "Set to $new_volume%"
