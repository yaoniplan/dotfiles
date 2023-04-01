#!/usr/bin/env bash

# Set variables
read -p "Enter city name: " city
read -p "Open weather report in terminal? (y/n): " choice

if [ "$choice" == "y" ]
then
    curl wttr.in/$city | less -S
else
    wget -P /tmp/ https://wttr.in/"$city".png
    chromium /tmp/"$city".png &
    sleep 30s
    rm /tmp/"$city".png
fi
