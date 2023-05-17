#!/usr/bin/env bash

# Get the public IP address, city and country information
IPAddress=$(curl -s https://ipinfo.io/ip)
city=$(curl -s https://ipinfo.io/${IPAddress}/city)
country=$(curl -s https://ipinfo.io/${IPAddress}/country)
outputResult="Your IP address in ${city}, ${country} is ${IPAddress}."

# Output the result using notify-send if available, or echo otherwise
if command -v notify-send &>/dev/null; then
    export $(dbus-launch); notify-send "$outputResult"
else
    echo "$outputResult"
fi
