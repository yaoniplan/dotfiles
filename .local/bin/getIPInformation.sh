#!/usr/bin/env bash

# Get the public IP address, city and country information
IPAddress=$(curl -s https://ipinfo.io/ip)
city=$(curl -s https://ipinfo.io/${IPAddress}/city)
country=$(curl -s https://ipinfo.io/${IPAddress}/country)

# Generage the output result
outputResult="Your IP address in ${city}, ${country} is ${IPAddress}."

# Output the result using notify-send if available, or echo otherwise
if ! notify-send "$outputResult" 2>/dev/null
then
    echo "$outputResult"
fi
