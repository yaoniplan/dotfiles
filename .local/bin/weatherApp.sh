#!/usr/bin/env bash

# Set the location and API key
location="New York"
apiKey="867c346ad5ff494a4352bf8216221fde"

# Retrieve the weather data from the API
weatherData=$(curl -s "https://api.openwethermap.org/data/2.5/weather?q=${location}&units=metric&appid=${apiKey}")

# Parse the data into variables using the 'jq' command-line tool
temperature=$(echo $weatherData | jq '.main.temp')
description=$(echo $weatherData | jq '.weather[0].description')

# Display the results
echo "Current weather in ${location}: ${temperature}°C and ${description}"
