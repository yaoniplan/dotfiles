#!/usr/bin/env bash

# Set variables
city="Dongxiang,Fuzhou,Jiangxi,China"

# Use the curl command to fetch the weather information
curl wttr.in/$city | less
