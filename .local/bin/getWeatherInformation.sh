#!/usr/bin/env bash

# Set variables
city="Dongxiang,Fuzhou,Jiangxi,China"
URL="https://www.google.com/search?q=$(echo $city | sed 's/,/+/g')+weather"

# Create a temporary directory to store the file
temporaryDir=$(mktemp --directory)

# Download the weather image and open it in a web browser
wget -P "$temporaryDir" "https://wttr.in/$city.png"
chromium "$temporaryDir/$city.png"

# Wait for 5 seconds and open the weather forecast in a web browser
sleep 5s
chromium "$URL"

# Remove the temporary directory and its contents
rm -rf "$temporaryDir"
