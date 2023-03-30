#!/usr/bin/env bash

# Get the city name from the user
echo "Enter the city name: "
read city

# Use the curl command to fetch the weather information
curl wttr.in/$city | less
