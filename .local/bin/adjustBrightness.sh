#!/usr/bin/env bash

#Dependencies: brightnessctl, tofi, notify-send

# Get the current brightness
current_brightness=$(brightnessctl --machine-readable | cut --delimiter=',' --fields='4' | tr --delete '%')

# Prompt the user to enter the desired brightness level
new_brightness=$(echo "" | tofi --prompt-text "Set Brightness Level $current_brightness to (0-100): ")

# Validate the input (Check if it is a number)
if [[ ! $new_brightness =~ ^[0-9]+$ ]]; then
    echo "Invalid Input" "Please enter a valid number between 0 and 100."
    exit 1
fi

# Ensure the brightness level is within the valid range (0-100)
if (( $new_brightness < 0 || $new_brightness > 100 )); then
    notify-send "Invalid Brightness" "Please enter a brightness level between 0 and 100."
    exit 1
fi

# Set new brightness
brightnessctl set "$new_brightness"%

# Show a notification with the new brightness level
notify-send "Brightness" "Set to $new_brightness%"
